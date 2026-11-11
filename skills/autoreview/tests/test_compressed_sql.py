from __future__ import annotations

import gzip
import hashlib
import os
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from skills.autoreview.tests.test_autoreview_hardening import SCRIPT, git, init_repo


class CompressedSqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = runpy.run_path(str(SCRIPT))

    def fixture(self, root, old=b'SELECT 1;\n', new=b'SELECT 2;\n', path='baseline.sql.gz'):
        repo = init_repo(root)
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if old is not None:
            target.write_bytes(gzip.compress(old, mtime=1))
        (repo / 'source').write_text('source\n')
        git(repo, 'add', '.')
        git(repo, 'commit', '-qm', 'base')
        base = git(repo, 'rev-parse', 'HEAD').strip()
        target.write_bytes(gzip.compress(new, mtime=2))
        git(repo, 'add', '.')
        git(repo, 'commit', '-qm', 'candidate')
        return repo, base

    def test_branch_modification_uses_both_frozen_blobs_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = self.fixture(Path(tmp))
            old_oid = git(repo, 'rev-parse', f'{base}:baseline.sql.gz').strip()
            new_oid = git(repo, 'rev-parse', 'HEAD:baseline.sql.gz').strip()
            (repo / 'baseline.sql.gz').write_bytes(b'WORKTREE_SENTINEL')
            bundle = self.helper['branch_bundle'](repo, base)
            self.assertIn('-SELECT 1;', bundle.text)
            self.assertIn('+SELECT 2;', bundle.text)
            self.assertIn(old_oid, bundle.text)
            self.assertIn(new_oid, bundle.text)
            self.assertIn(hashlib.sha256(b'SELECT 2;\n').hexdigest(), bundle.text)
            self.assertNotIn('WORKTREE_SENTINEL', bundle.text)
            self.assertIn('Binary files', bundle.branch_patch)
            chunks = self.helper['split_review_bundle'](bundle.text, 1200)
            for chunk in chunks:
                if 'SELECT' in chunk.content:
                    self.assertIn('compressed-sql ', chunk.content + chunk.context)

    def test_added_and_recompressed_files_are_reviewed(self):
        for old in (None, b'SELECT 2;\n'):
            with self.subTest(old=old), tempfile.TemporaryDirectory() as tmp:
                repo, base = self.fixture(Path(tmp), old=old)
                bundle = self.helper['branch_bundle'](repo, base)
                self.assertIn('compressed-sql ', bundle.text)
                self.assertIn('baseline.sql.gz', bundle.paths)
                if old is None:
                    self.assertIn('+SELECT 2;', bundle.text)
                else:
                    self.assertIn('Decoded SQL unchanged', bundle.text)

    def test_malformed_and_nontext_payloads_fail_closed(self):
        valid = gzip.compress(b'SELECT 2;\n')
        bad_crc = bytearray(valid)
        bad_crc[-8] ^= 1
        for payload in (b'not gzip', valid[:-1], bytes(bad_crc), valid + b'junk',
                        valid + valid, gzip.compress(b'\xff'), gzip.compress(b'SELECT\0')):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as tmp:
                repo, base = self.fixture(Path(tmp))
                (repo / 'baseline.sql.gz').write_bytes(payload)
                git(repo, 'add', '.')
                git(repo, 'commit', '-qm', 'invalid')
                with self.assertRaises(SystemExit):
                    self.helper['branch_bundle'](repo, base)

    def test_invalid_old_side_also_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = self.fixture(Path(tmp), old=b'\xff')
            with self.assertRaises(SystemExit):
                self.helper['branch_bundle'](repo, base)

    def test_limits_apply_before_read_and_during_expansion_and_in_total(self):
        for limit, value in (('MAX_REVIEW_SQL_COMPRESSED_BYTES', 8),
                             ('MAX_REVIEW_SQL_BYTES', 8),
                             ('MAX_REVIEW_SQL_TOTAL_BYTES', 12),
                             ('MAX_REVIEW_SQL_TOTAL_COMPRESSED_BYTES', 40)):
            with self.subTest(limit=limit), tempfile.TemporaryDirectory() as tmp:
                repo, base = self.fixture(Path(tmp))
                namespace = self.helper['capture_compressed_sql'].__globals__
                with mock.patch.dict(namespace, {limit: value}):
                    with self.assertRaises(SystemExit):
                        self.helper['branch_bundle'](repo, base)

    def test_compression_bomb_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = self.fixture(Path(tmp), new=b'x' * 100000)
            namespace = self.helper['capture_compressed_sql'].__globals__
            with mock.patch.dict(namespace, {'MAX_REVIEW_SQL_BYTES': 1024}):
                with self.assertRaises(SystemExit):
                    self.helper['branch_bundle'](repo, base)

    def test_forced_text_attributes_do_not_hide_compressed_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = self.fixture(Path(tmp))
            (repo / '.gitattributes').write_text('*.gz diff\n')
            git(repo, 'add', '.')
            git(repo, 'commit', '-qm', 'force text')
            with self.assertRaises(SystemExit):
                self.helper['branch_bundle'](repo, base)

    def test_other_modes_and_unsupported_binaries_still_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = self.fixture(Path(tmp))
            with self.assertRaises(SystemExit):
                self.helper['commit_bundle'](repo, 'HEAD')
            (repo / 'baseline.sql.gz').write_bytes(gzip.compress(b'SELECT 3;\n'))
            with self.assertRaises(SystemExit):
                self.helper['local_bundle'](repo)
            (repo / 'other.bin').write_bytes(b'\x00\xff')
            git(repo, 'add', '.')
            git(repo, 'commit', '-qm', 'unsupported')
            with self.assertRaises(SystemExit):
                self.helper['branch_bundle'](repo, base)

    def test_sensitive_compressed_path_is_never_decoded(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = self.fixture(Path(tmp), path='.ssh/baseline.sql.gz')
            namespace = self.helper['branch_bundle'].__globals__
            with mock.patch.dict(namespace, {'decode_compressed_sql': mock.Mock(side_effect=AssertionError('decoded sensitive blob'))}):
                with self.assertRaises(SystemExit):
                    self.helper['branch_bundle'](repo, base)

    def test_partitioned_sql_keeps_both_blob_bindings(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = self.fixture(Path(tmp), old=b'', new=b'SELECT 2;\n' * 500)
            bundle = self.helper['branch_bundle'](repo, base)
            chunks = self.helper['split_review_bundle'](bundle.text, 1200)
            self.assertGreater(len(chunks), 2)
            for chunk in chunks:
                if 'SELECT' in chunk.content:
                    evidence = chunk.content + chunk.context
                    self.assertIn('compressed-sql before:', evidence)
                    self.assertIn('compressed-sql after:', evidence)
                    self.assertIn(hashlib.sha256(b'SELECT 2;\n' * 500).hexdigest(), evidence)

    def test_review_batches_refuses_decoded_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = self.fixture(Path(tmp))
            bundle = self.helper['branch_bundle'](repo, base)
            with self.assertRaises(SystemExit):
                self.helper['branch_batch_units'](bundle)

    def test_encoded_limit_refuses_before_blob_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = self.fixture(Path(tmp))
            oid = git(repo, 'rev-parse', 'HEAD:baseline.sql.gz').strip()
            namespace = self.helper['decode_compressed_sql'].__globals__
            with mock.patch.dict(namespace, {
                'MAX_REVIEW_SQL_COMPRESSED_BYTES': 1,
                'git': mock.Mock(return_value='100\n'),
                'git_bytes': mock.Mock(side_effect=AssertionError('read oversized blob')),
            }):
                with self.assertRaises(SystemExit):
                    self.helper['decode_compressed_sql'](repo, oid, 100, 100)

    def test_symlink_type_change_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = self.fixture(Path(tmp))
            target = repo / 'baseline.sql.gz'
            target.write_text('source')
            oid = git(repo, 'hash-object', '-w', str(target)).strip()
            git(repo, 'update-index', '--cacheinfo', f'120000,{oid},baseline.sql.gz')
            git(repo, 'commit', '-qm', 'type change')
            with self.assertRaises(SystemExit):
                self.helper['branch_bundle'](repo, base)

    def test_plain_text_sql_gz_remains_ordinary_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = init_repo(Path(tmp))
            (repo / 'source').write_text('source\n')
            git(repo, 'add', '.')
            git(repo, 'commit', '-qm', 'base')
            base = git(repo, 'rev-parse', 'HEAD').strip()
            (repo / 'plain.sql.gz').write_text('SELECT 1;\n')
            git(repo, 'add', '.')
            git(repo, 'commit', '-qm', 'plain text')
            bundle = self.helper['branch_bundle'](repo, base)
            self.assertIn('+SELECT 1;', bundle.text)
            self.assertNotIn('compressed-sql ', bundle.text)
            (repo / 'plain.sql.gz').write_text('SELECT 2;\n')
            git(repo, 'add', '.')
            git(repo, 'commit', '-qm', 'modify plain text')
            bundle = self.helper['branch_bundle'](repo, base)
            self.assertIn('+SELECT 2;', bundle.text)
            self.assertNotIn('compressed-sql ', bundle.text)

    def test_symlink_addition_remains_ordinary_symlink_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = init_repo(Path(tmp))
            (repo / 'source').write_text('source\n')
            git(repo, 'add', '.')
            git(repo, 'commit', '-qm', 'base')
            base = git(repo, 'rev-parse', 'HEAD').strip()
            target = repo / 'link.sql.gz'
            target.write_text('source')
            oid = git(repo, 'hash-object', '-w', str(target)).strip()
            git(repo, 'update-index', '--add', '--cacheinfo', f'120000,{oid},link.sql.gz')
            git(repo, 'commit', '-qm', 'link')
            bundle = self.helper['branch_bundle'](repo, base)
            self.assertIn('new file mode 120000', bundle.text)
            self.assertNotIn('compressed-sql ', bundle.text)

    def test_empty_gzip_addition_is_not_labeled_recompression(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = self.fixture(Path(tmp), old=None, new=b'')
            bundle = self.helper['branch_bundle'](repo, base)
            self.assertIn('Added empty decoded SQL', bundle.text)
            self.assertNotIn('Decoded SQL unchanged', bundle.text)

    def test_projection_preserves_unrelated_type_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = self.fixture(Path(tmp))
            source = repo / 'source'
            source.write_text('baseline.sql.gz')
            oid = git(repo, 'hash-object', '-w', str(source)).strip()
            git(repo, 'update-index', '--cacheinfo', f'120000,{oid},source')
            git(repo, 'commit', '-qm', 'type change')
            bundle = self.helper['branch_bundle'](repo, base)
            self.assertIn('+SELECT 2;', bundle.text)
            self.assertIn('new file mode 120000', bundle.text)
            self.assertIn('deleted file mode 100644', bundle.text)

    def test_decoded_temp_files_cannot_be_written_inside_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = self.fixture(Path(tmp))
            namespace = self.helper['compressed_sql_diff'].__globals__
            with mock.patch.object(namespace['tempfile'], 'gettempdir', return_value=str(repo)):
                with self.assertRaisesRegex(SystemExit, 'outside the reviewed repository'):
                    self.helper['branch_bundle'](repo, base)
            self.assertFalse(list(repo.glob('autoreview-sql-*')))

    def test_user_attributes_cannot_normalize_decoded_line_endings(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = self.fixture(Path(tmp))
            home = Path(tmp) / 'home'
            attributes = home / '.config' / 'git' / 'attributes'
            attributes.parent.mkdir(parents=True)
            attributes.write_text('* text=auto\n')
            with mock.patch.dict(os.environ, {'HOME': str(home)}):
                patch = self.helper['compressed_sql_diff'](repo, b'SELECT 1;\n', b'SELECT 1;\r\n')
            self.assertIn('+SELECT 1;\r\n', patch)

    def test_enclosing_worktree_attributes_cannot_hide_decoded_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = self.fixture(Path(tmp))
            outer = Path(tmp) / 'outer'
            outer.mkdir()
            git(outer, 'init', '-q')
            (outer / '.gitattributes').write_text('* text ident\n')
            scratch = outer / 'scratch'
            scratch.mkdir()
            namespace = self.helper['compressed_sql_diff'].__globals__
            with mock.patch.object(namespace['tempfile'], 'gettempdir', return_value=str(scratch)):
                patch = self.helper['compressed_sql_diff'](
                    repo, b"SELECT '$Id: before $';\n", b"SELECT '$Id: after $';\r\n",
                )
            self.assertIn("+SELECT '$Id: after $';\r\n", patch)

    def test_enclosing_worktree_filter_cannot_execute_or_rewrite_sql(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = self.fixture(Path(tmp))
            outer = Path(tmp) / 'outer'
            outer.mkdir()
            git(outer, 'init', '-q')
            (outer / '.gitattributes').write_text('* filter=rewrite\n')
            marker = Path(tmp) / 'filter-ran'
            script = Path(tmp) / 'filter.py'
            script.write_text(
                'import sys\nfrom pathlib import Path\n'
                f'Path({str(marker)!r}).write_text("executed")\n'
                'sys.stdout.write(sys.stdin.read().replace("TRUNCATE", "SELECT_1_FROM"))\n'
            )
            git(outer, 'config', 'filter.rewrite.clean', f'"{sys.executable}" "{script}"')
            scratch = outer / 'scratch'
            scratch.mkdir()
            namespace = self.helper['compressed_sql_diff'].__globals__
            with mock.patch.object(namespace['tempfile'], 'gettempdir', return_value=str(scratch)):
                patch = self.helper['compressed_sql_diff'](repo, b'SELECT 1;\n', b'TRUNCATE TABLE ledger;\n')
            self.assertIn('+TRUNCATE TABLE ledger;\n', patch)
            self.assertFalse(marker.exists())

    def test_separator_in_temp_path_cannot_restore_enclosing_attributes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = self.fixture(Path(tmp))
            outer = Path(tmp) / ('outer' + os.pathsep + 'path')
            outer.mkdir()
            git(outer, 'init', '-q')
            (outer / '.gitattributes').write_text('* text ident\n')
            scratch = outer / 'scratch'
            scratch.mkdir()
            namespace = self.helper['compressed_sql_diff'].__globals__
            with mock.patch.object(namespace['tempfile'], 'gettempdir', return_value=str(scratch)):
                patch = self.helper['compressed_sql_diff'](
                    repo, b"SELECT '$Id: before $';\n", b"SELECT '$Id: after $';\r\n",
                )
            self.assertIn("+SELECT '$Id: after $';\r\n", patch)

    def test_separator_in_temp_path_cannot_restore_enclosing_filters(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = self.fixture(Path(tmp))
            outer = Path(tmp) / ('outer' + os.pathsep + 'path')
            outer.mkdir()
            git(outer, 'init', '-q')
            (outer / '.gitattributes').write_text('* filter=rewrite\n')
            marker = Path(tmp) / 'filter-ran'
            script = Path(tmp) / 'filter.py'
            script.write_text(
                'import sys\nfrom pathlib import Path\n'
                f'Path({str(marker)!r}).write_text("executed")\n'
                'sys.stdout.write(sys.stdin.read().replace("TRUNCATE", "SELECT_1_FROM"))\n'
            )
            git(outer, 'config', 'filter.rewrite.clean', f'"{sys.executable}" "{script}"')
            scratch = outer / 'scratch'
            scratch.mkdir()
            namespace = self.helper['compressed_sql_diff'].__globals__
            with mock.patch.object(namespace['tempfile'], 'gettempdir', return_value=str(scratch)):
                patch = self.helper['compressed_sql_diff'](repo, b'SELECT 1;\n', b'TRUNCATE TABLE ledger;\n')
            self.assertIn('+TRUNCATE TABLE ledger;\n', patch)
            self.assertFalse(marker.exists())

    def test_projected_sql_prompt_requires_null_attribution_for_all_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, base = self.fixture(Path(tmp))
            bundle = self.helper['branch_bundle'](repo, base)
            prompt = self.helper['render_review_prompt'](
                'candidate', 'branch', base, self.helper['ReviewChunk'](bundle.text), '', '',
            )
            self.assertIn('For every finding on projected SQL use null source_attribution.', prompt)
            self.assertIn('Blob IDs are provenance, not mixed-source record IDs.', prompt)

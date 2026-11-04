"""Exercise output custody with real parent and Git metadata replacement."""
import argparse
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock


SUBJECT = Path(__file__).resolve().parents[1] / 'scripts' / 'autoreview'


def load_subject():
    module = types.ModuleType('output_custody_subject')
    module.__file__ = str(SUBJECT)
    sys.modules[module.__name__] = module
    exec(compile(SUBJECT.read_bytes(), str(SUBJECT), 'exec'), module.__dict__)
    return module


@unittest.skipUnless(os.name == 'posix', 'POSIX directory-descriptor custody')
class OutputCustodyTests(unittest.TestCase):
    def setUp(self):
        self.helper = load_subject()
        temporary = tempfile.TemporaryDirectory(prefix='autoreview-output-custody-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.repo = self.root / 'source'
        self.repo.mkdir()
        subprocess.run(['/usr/bin/git', 'init', '-q', str(self.repo)], check=True,
                       env={'PATH': '/usr/bin:/bin', 'GIT_CONFIG_NOSYSTEM': '1',
                            'GIT_CONFIG_GLOBAL': os.devnull})
        self.outside = self.root / 'outside'
        self.outside.mkdir(mode=0o700)
        self.alias = self.root / 'alias'
        self.alias.symlink_to(self.outside, target_is_directory=True)
        token = self.helper.UNTRUSTED_SOURCE_ROOTS.set((self.repo,))
        self.addCleanup(self.helper.UNTRUSTED_SOURCE_ROOTS.reset, token)
        binding = self.helper.repository_metadata(self.repo)
        token = self.helper.SOURCE_METADATA_BINDINGS.set((binding,))
        self.addCleanup(self.helper.SOURCE_METADATA_BINDINGS.reset, token)

    def redirect(self):
        self.alias.unlink()
        self.alias.symlink_to(self.repo, target_is_directory=True)

    def change_metadata(self):
        (self.repo / '.git').rename(self.repo / 'original-git')
        (self.repo / '.git').mkdir()

    def arguments(self, **values):
        args = argparse.Namespace(json_output=None, output=None, status_output=None,
                                  preflight_output=None, engine_stage_dir=None,
                                  native_handoff=None, dry_run=False,
                                  external_source_manifests=[], mode="uncommitted", base=None)
        for key, value in values.items():
            setattr(args, key, value)
        return args

    def test_stale_deletion_does_not_follow_redirected_parent(self):
        # Metadata remains unchanged: only the previously admitted parent alias moves.
        for role in ('status_output', 'preflight_output'):
            with self.subTest(role=role):
                if self.alias.resolve() != self.outside:
                    self.alias.unlink()
                    self.alias.symlink_to(self.outside, target_is_directory=True)
                source = self.repo / (role + '.json')
                source.write_text('source sentinel')
                destination = self.outside / source.name
                destination.write_text('stale outside report')
                args = self.arguments(**{role: str(self.alias / source.name)})
                prepare = self.helper.prepare_output_paths

                def prepare_then_redirect(*args):
                    prepare(*args)
                    self.redirect()

                with mock.patch.object(self.helper, 'repo_root', return_value=self.repo), \
                        mock.patch.object(self.helper, 'prepare_output_paths', side_effect=prepare_then_redirect), \
                        mock.patch.object(self.helper, 'choose_target', side_effect=RuntimeError('target reached')), \
                        contextlib.redirect_stderr(io.StringIO()):
                    try:
                        self.helper.main_with_output_boundary(args, self.repo, [])
                    except (SystemExit, RuntimeError):
                        pass
                self.helper.verify_repository_metadata()
                self.assertTrue(source.exists(), 'source entry was deleted')
                self.assertEqual(source.read_text(), 'source sentinel')
                self.assertEqual(destination.read_text(), 'stale outside report')

    def test_stale_unlink_is_bound_at_the_filesystem_operation(self):
        source = self.repo / 'status.json'
        source.write_text('source sentinel')
        outside = self.outside / source.name
        outside.write_text('stale report')
        args = self.arguments(status_output=str(self.alias / source.name))
        unlink = os.unlink
        redirected = []

        def redirect_at_unlink(path, *args, **kwargs):
            if Path(path).name == source.name and not redirected:
                redirected.append(True)
                self.redirect()
            return unlink(path, *args, **kwargs)

        # The callback only schedules the real symlink replacement; the actual
        # unlink still runs, including the helper's own directory descriptor.
        with mock.patch.object(self.helper, 'repo_root', return_value=self.repo), \
                mock.patch.object(self.helper, 'choose_target', side_effect=RuntimeError('target reached')), \
                mock.patch.object(os, 'unlink', side_effect=redirect_at_unlink), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'target reached'):
                self.helper.main_with_output_boundary(args, self.repo, [])
        self.assertTrue(redirected)
        self.assertTrue(source.exists(), 'late parent redirection deleted a source entry')
        self.assertEqual(source.read_text(), 'source sentinel')
        self.assertFalse(outside.exists())

    def test_probe_cleanup_uses_original_parent_after_alias_redirect(self):
        verify = self.helper.verify_repository_metadata
        sentinels = []

        def redirect_after_probe(*args):
            probes = list(self.outside.glob('.autoreview-output-probe.*'))
            if probes and not sentinels:
                for probe in probes:
                    sentinel = self.repo / probe.name
                    sentinel.write_text('source probe sentinel')
                    sentinels.append(sentinel)
                self.redirect()
            return verify(*args)

        with mock.patch.object(self.helper, 'verify_repository_metadata', side_effect=redirect_after_probe):
            try:
                self.helper.require_output_ready(self.alias / 'report.json', '--json-output')
            except SystemExit:
                pass
        self.assertTrue(sentinels, 'fixture must redirect after a real probe was created')
        for sentinel in sentinels:
            self.assertTrue(sentinel.exists(), 'source entry was deleted during probe cleanup')
            self.assertEqual(sentinel.read_text(), 'source probe sentinel')
        self.assertEqual(list(self.outside.iterdir()), [])

    def test_metadata_refusal_removes_complete_report_scratch(self):
        verify = self.helper.verify_repository_metadata
        destination = self.outside / 'report.json'
        destination.write_text('previous report')
        observed = []

        def change_after_write(*args):
            for temporary in self.outside.glob('.report.json.*'):
                if temporary.read_text() == 'complete synthetic report' and not observed:
                    observed.append(temporary)
                    self.change_metadata()
            return verify(*args)

        with mock.patch.object(self.helper, 'verify_repository_metadata', side_effect=change_after_write):
            with self.assertRaisesRegex(SystemExit, 'metadata'):
                self.helper.atomic_write_text(destination, 'complete synthetic report')
        self.assertTrue(observed, 'fixture must change metadata after the real content write')
        self.assertEqual(destination.read_text(), 'previous report')
        self.assertEqual(list(self.outside.glob('.report.json.*')), [])

    def handoff(self):
        args = self.arguments(native_handoff=str(self.alias / 'exchange'))
        args.engine_timeout_seconds = 1
        reviewer = argparse.Namespace(model='fixture/model', thinking='high', openclaw_models=[])
        return self.helper.NativeHandoff(args, reviewer, ['synthetic prompt'])

    def test_native_cleanup_ignores_metadata_refusal_and_parent_alias(self):
        handoff = self.handoff()
        (self.outside / 'exchange' / '1.request.json').write_text('complete synthetic prompt')
        nested = self.outside / 'exchange' / 'nested'
        nested.mkdir()
        (nested / 'request').write_text('nested synthetic prompt')
        (nested / 'source-link').symlink_to(self.repo, target_is_directory=True)
        protected = self.repo / 'exchange'
        protected.mkdir()
        (protected / '1.request.json').write_text('source sentinel')
        self.change_metadata()
        self.redirect()
        handoff.close()
        self.assertFalse((self.outside / 'exchange').exists())
        self.assertEqual((protected / '1.request.json').read_text(), 'source sentinel')
        self.assertIsNone(handoff.lock_fd)

    def test_final_status_keeps_the_admitted_parent(self):
        args = self.arguments(status_output=str(self.alias / 'status.json'))
        args.engine = 'codex'
        self.helper.prepare_output_paths(args, self.repo)
        different = self.root / 'different-outside'
        different.mkdir()
        self.alias.unlink()
        self.alias.symlink_to(different, target_is_directory=True)
        with self.assertRaisesRegex(SystemExit, 'output parent changed'):
            self.helper.write_review_status(args, 'done', 0)
        self.assertEqual(list(different.iterdir()), [])
        self.assertEqual(list(self.outside.iterdir()), [])

    def test_native_initial_nonempty_directory_is_preserved(self):
        mkdir = os.mkdir
        exchange = self.outside / 'exchange'
        retained = self.outside / 'retained-empty-exchange'

        def replace_after_mkdir(path, *args, **kwargs):
            mkdir(path, *args, **kwargs)
            if Path(path).name == 'exchange':
                exchange.rename(retained)
                mkdir(exchange, mode=0o700)
                (exchange / 'sentinel').write_text('unknown initial contents')

        errors = io.StringIO()
        with mock.patch.object(os, 'mkdir', side_effect=replace_after_mkdir), \
                contextlib.redirect_stderr(errors):
            with self.assertRaisesRegex(SystemExit, 'fresh empty directory'):
                self.handoff()
        self.assertEqual((exchange / 'sentinel').read_text(), 'unknown initial contents')
        self.assertIn('could not safely remove native handoff scratch', errors.getvalue())

    def test_native_creation_replacement_is_never_admitted_for_cleanup(self):
        open_file = os.open
        exchange = self.outside / 'exchange'
        retained = self.outside / 'retained-created-exchange'

        def replace_at_root_open(path, flags, *args, **kwargs):
            if Path(path).name == 'exchange' and flags & os.O_DIRECTORY:
                exchange.rename(retained)
                exchange.mkdir()
                (exchange / 'sentinel').write_text('unadmitted replacement')
            return open_file(path, flags, *args, **kwargs)

        errors = io.StringIO()
        with mock.patch.object(os, 'open', side_effect=replace_at_root_open), \
                contextlib.redirect_stderr(errors):
            with self.assertRaisesRegex(SystemExit, 'directory changed during creation'):
                self.handoff()
        self.assertEqual((exchange / 'sentinel').read_text(), 'unadmitted replacement')
        self.assertTrue(retained.is_dir())
        self.assertIn('could not safely remove native handoff scratch', errors.getvalue())

    def test_native_creation_custody_failure_reports_residue(self):
        open_file = os.open

        def refuse_root_open(path, flags, *args, **kwargs):
            if Path(path).name == 'exchange' and flags & os.O_DIRECTORY:
                raise PermissionError('synthetic root-open refusal')
            return open_file(path, flags, *args, **kwargs)

        errors = io.StringIO()
        with mock.patch.object(os, 'open', side_effect=refuse_root_open), \
                contextlib.redirect_stderr(errors):
            with self.assertRaises(PermissionError):
                self.handoff()
        self.assertTrue((self.outside / 'exchange').is_dir())
        self.assertIn('could not safely remove native handoff scratch', errors.getvalue())

    def test_native_replacement_is_preserved_and_residue_is_reported(self):
        handoff = self.handoff()
        exchange = self.outside / 'exchange'
        retained = self.outside / 'retained-exchange'
        exchange.rename(retained)
        exchange.mkdir()
        (exchange / 'sentinel').write_text('replacement')
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            handoff.close()
        self.assertEqual((exchange / 'sentinel').read_text(), 'replacement')
        self.assertTrue(retained.is_dir())
        self.assertIn('could not safely remove native handoff scratch', errors.getvalue())
        self.assertIsNone(handoff.lock_fd)


if __name__ == '__main__':
    unittest.main()

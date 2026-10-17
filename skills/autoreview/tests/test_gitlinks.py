from __future__ import annotations

import json
import runpy
import tempfile
import unittest
from pathlib import Path

from skills.autoreview.tests.test_autoreview_hardening import SCRIPT, git, init_repo


class GitlinkBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = runpy.run_path(str(SCRIPT))

    def fixture(self, root):
        repo = init_repo(root)
        (repo / 'source').write_text('base\n')
        git(repo, 'add', '.')
        git(repo, 'commit', '-qm', 'source')
        old = git(repo, 'rev-parse', 'HEAD').strip()
        (repo / '.gitmodules').write_text(
            '[submodule "different-name"]\n path = vendor/dependency\n'
            ' url = https://example.invalid/old.git\n')
        git(repo, 'add', '.gitmodules')
        git(repo, 'update-index', '--add', '--cacheinfo', f'160000,{old},vendor/dependency')
        (repo / 'vendor' / 'dependency').mkdir(parents=True)
        git(repo, 'commit', '-qm', 'base pin')
        base = git(repo, 'rev-parse', 'HEAD').strip()
        return repo, old, base

    def test_bump_uses_full_ids_and_selected_urls_without_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, old, base = self.fixture(Path(tmp))
            (repo / '.gitmodules').write_text(
                '[submodule "different-name"]\n path = vendor/dependency\n'
                ' url = https://example.invalid/new.git\n')
            git(repo, 'add', '.gitmodules')
            git(repo, 'update-index', '--cacheinfo', f'160000,{base},vendor/dependency')
            local = self.helper['local_bundle'](repo).text
            git(repo, 'commit', '-qm', 'bump pin and URL')
            # Repository display settings cannot expand or suppress the link patch.
            git(repo, 'config', 'diff.submodule', 'log')
            git(repo, 'config', 'diff.ignoreSubmodules', 'all')
            # Neither the working copy nor local config may replace frozen URLs.
            (repo / '.gitmodules').write_text('[invalid working tree\n')
            git(repo, 'config', 'submodule.different-name.url', 'https://wrong.invalid')
            for bundle in (local, self.helper['branch_bundle'](repo, base).text,
                           self.helper['commit_bundle'](repo, 'HEAD').text):
                self.assertIn(old, bundle)
                self.assertIn(base, bundle)
                self.assertIn('https://example.invalid/old.git', bundle)
                self.assertIn('https://example.invalid/new.git', bundle)
                self.assertIn('NOT bundled or reviewed', bundle)
                self.assertNotIn('wrong.invalid', bundle)
            self.assertFalse((repo / 'vendor/dependency/.git').exists())

    def test_gitmodules_include_is_never_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, old, base = self.fixture(Path(tmp))
            external = Path(tmp) / 'outside'
            external.write_text('[submodule "leak"]\npath = vendor/dependency\nurl = PRIVATE_SENTINEL\n')
            (repo / '.gitmodules').write_text(f'[include]\npath = {external}\n')
            git(repo, 'add', '.gitmodules')
            git(repo, 'update-index', '--cacheinfo', f'160000,{base},vendor/dependency')
            git(repo, 'commit', '-qm', 'bump')
            text = self.helper['branch_bundle'](repo, base).text
            self.assertNotIn('PRIVATE_SENTINEL', text)
            self.assertIn('"url": null', text)

    def test_sensitive_gitlink_path_is_omitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, old, base = self.fixture(Path(tmp))
            git(repo, 'update-index', '--add', '--cacheinfo', f'160000,{base},.ssh/dependency')
            git(repo, 'commit', '-qm', 'sensitive link')
            bundle = self.helper['branch_bundle'](repo, base)
            self.assertNotIn('.ssh/dependency', bundle.text)
            self.assertNotIn('.ssh/dependency', bundle.paths)

    def test_working_url_and_unstaged_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, old, base = self.fixture(Path(tmp))
            dependency = repo / 'vendor' / 'dependency'
            dependency.rmdir()
            git(repo, 'clone', '--no-hardlinks', str(repo), str(dependency))
            git(dependency, 'checkout', '-q', base)
            (repo / '.gitmodules').write_text(
                '[submodule "different-name"]\npath = vendor/dependency\nurl = ../new.git\n')
            text = self.helper['local_bundle'](repo).text
            metadata = next(json.loads(line) for line in text.splitlines()
                            if line.startswith('{"path": "vendor/dependency"'))
            self.assertEqual(metadata['new']['sha'], base)
            self.assertIn('index -> working_tree', text)
            self.assertIn('../new.git', text)
            self.assertIn(base, text)
            (dependency / 'source').write_text('dirty\n')
            with self.assertRaisesRegex(SystemExit, 'uncommitted submodule contents'):
                self.helper['local_bundle'](repo)

    def test_subproject_looking_regular_text_is_not_a_dirty_submodule(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, old, base = self.fixture(Path(tmp))
            (repo / 'source').write_text('Subproject commit ' + old + '-dirty\n')
            self.assertIn('-dirty', self.helper['local_bundle'](repo).text)

    def test_ambiguous_mapping_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, old, base = self.fixture(Path(tmp))
            with (repo / '.gitmodules').open('a') as f:
                f.write('[submodule "duplicate"]\npath = vendor/dependency\nurl = other\n')
            git(repo, 'add', '.gitmodules')
            git(repo, 'update-index', '--cacheinfo', f'160000,{base},vendor/dependency')
            with self.assertRaisesRegex(SystemExit, 'ambiguous .gitmodules'):
                self.helper['local_bundle'](repo)


if __name__ == '__main__':
    unittest.main()

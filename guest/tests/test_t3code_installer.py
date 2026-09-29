from __future__ import annotations
import copy
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

GUEST = Path(__file__).resolve().parents[1]
ASSETS = GUEST / 'native-overlay/usr/local/share/try-omarchy/t3code'
INSTALLER = GUEST / 'native-overlay/usr/local/lib/try-omarchy/install-t3code-arm64'
SPEC = json.loads((GUEST / 'spec.json').read_text())


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


release = load('release', ASSETS / 'resolve-release.py')
installer = load('installer', INSTALLER)
integration = load('integration', GUEST / 'scripts/install-t3code-integration.py')
PAYLOAD = b'fake ARM64 AppImage bytes'


def metadata(version='0.0.42'):
    name = f'T3-Code-{version}-arm64.AppImage'
    return dict(tag_name=f'v{version}', draft=False, prerelease=False, assets=[dict(
        name=name, browser_download_url=f'https://github.com/pingdotgg/t3code/releases/download/v{version}/{name}',
        digest='sha256:' + hashlib.sha256(PAYLOAD).hexdigest())])


class T3CodeTests(unittest.TestCase):
    def test_latest_stable_version_is_not_pinned(self):
        for version in ('0.0.42', '0.1.0', '2.0.0'):
            self.assertEqual(release.resolve(metadata(version))[0], version)

    def test_untrusted_release_metadata_is_rejected(self):
        invalid = []
        for field, value in [('draft', True), ('prerelease', True), ('tag_name', 'v1.0.0; touch /tmp/bad'), ('assets', [])]:
            item = metadata(); item[field] = value; invalid.append(item)
        for field, value in [('browser_download_url', 'https://example.com/app'), ('digest', None), ('name', 'T3-Code-0.0.42-x86_64.AppImage')]:
            item = metadata(); item['assets'][0][field] = value; invalid.append(item)
        item = metadata(); item['assets'] *= 2; invalid.append(item)
        for item in invalid:
            with self.subTest(item=item), self.assertRaises(ValueError):
                release.resolve(item)

    def test_local_inputs_match_reviewed_spec(self):
        for name, key in {**installer.ASSET_PINS,
                          'legacy-omarchy-install-ai-t3-code': 'legacyInstallSha256',
                          'legacy-omarchy-update': 'legacyUpdateSha256'}.items():
            self.assertEqual(installer.sha256(ASSETS / name), SPEC['supplyChain']['t3code'][key])
        self.assertEqual(installer.sha256(INSTALLER), SPEC['supplyChain']['t3code']['installerSha256'])

    def install(self, root, payload=PAYLOAD, fetch_error=None, migrate_error=None, remove=False):
        calls = []
        def fetch(url, destination):
            calls.append(('download', url))
            if fetch_error:
                raise fetch_error
            destination.write_bytes(json.dumps(metadata()).encode() if url.endswith('/latest') else payload)
        def run(*args, **kwargs):
            calls.append(args)
            if '--appimage-extract' in args:
                icon = kwargs['cwd'] / 'squashfs-root/usr/share/icons/hicolor/256x256/apps/t3code.png'
                icon.parent.mkdir(parents=True)
                icon.write_bytes(b'icon')
        with patch.dict(os.environ, {'XDG_DATA_HOME': str(root)}), \
             patch.object(installer, 'fetch', side_effect=fetch), \
             patch.object(installer, 'run', side_effect=run), \
             patch.object(installer, 'migrate_package', side_effect=migrate_error) as migrate:
            installer.install(ASSETS, GUEST / 'spec.json', remove)
            return calls, migrate.call_count

    def test_download_installs_intact_writable_appimage_and_launcher(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'space and % field'
            calls, migrated = self.install(root)
            app = root / 'try-omarchy/t3code'
            self.assertEqual((app / 'T3-Code.AppImage').read_bytes(), PAYLOAD)
            self.assertEqual((app / 'T3-Code.AppImage').stat().st_mode & 0o777, 0o755)
            self.assertIn('fuse2', next(c for c in calls if c[0] == 'omarchy-pkg-add'))
            entry = (root / 'applications/t3code.desktop').read_text()
            self.assertIn('%% field', entry)
            self.assertIn('t3code-wrapper" %U', entry)
            self.assertEqual(migrated, 1)
            self.assertTrue((app / 't3').stat().st_mode & 0o111)

    def test_network_and_checksum_failure_leave_existing_package_untouched(self):
        for kwargs, error in [({'fetch_error': OSError('offline')}, OSError),
                              ({'payload': b'corrupted'}, ValueError)]:
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                with self.assertRaises(error):
                    self.install(root, migrate_error=AssertionError('must not remove package'), **kwargs)
                self.assertFalse((root / 'try-omarchy/t3code/T3-Code.AppImage').exists())
                self.assertFalse((root / 'applications/t3code.desktop').exists())

    def test_reinstall_preserves_nightly_and_repairs_launcher_without_download(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.install(root)
            image = root / 'try-omarchy/t3code/T3-Code.AppImage'
            image.write_bytes(b'new nightly installed by T3 Code')
            (root / 'applications/t3code.desktop').unlink()
            calls, _ = self.install(root, fetch_error=AssertionError('must not download stable'))
            self.assertEqual(image.read_bytes(), b'new nightly installed by T3 Code')
            self.assertTrue((root / 'applications/t3code.desktop').exists())
            self.assertFalse(any(c[0] == 'download' for c in calls))

    def test_cancelled_package_removal_is_retryable_without_redownload(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(subprocess.CalledProcessError):
                self.install(root, migrate_error=subprocess.CalledProcessError(1, 'pacman'))
            self.assertFalse((root / 'applications/t3code.desktop').exists())
            self.install(root, fetch_error=AssertionError('already staged'))
            self.assertTrue((root / 'applications/t3code.desktop').exists())

    def test_remove_only_deletes_app_and_launcher(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.install(root)
            saved = root / '.t3'; saved.mkdir(); (saved / 'chat').write_text('keep')
            calls, migrated = self.install(root, remove=True)
            self.assertFalse((root / 'try-omarchy/t3code').exists())
            self.assertFalse((root / 'applications/t3code.desktop').exists())
            self.assertEqual((saved / 'chat').read_text(), 'keep')
            self.assertEqual(migrated, 0)
            self.assertFalse(any(c[0] == 'download' for c in calls))

    def test_removing_an_absent_app_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.install(root, remove=True)
            self.install(root, remove=True)
            self.assertFalse((root / 'try-omarchy/t3code').exists())

    def test_symlink_destinations_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); outside = root / 'outside'; outside.mkdir()
            (root / 'try-omarchy').symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                self.install(root)
            self.assertEqual(list(outside.iterdir()), [])

    def test_package_migration_unregisters_old_local_repo_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp); (repo / 'try-omarchy.db.tar.gz').touch()
            def execute(args, **kwargs):
                return subprocess.CompletedProcess(args, 1 if args[0] == 'pgrep' else 0,
                                                   stdout='t3code-bin-0.0.42-1/desc\n')
            with patch.object(installer, 'REPO', repo), patch.object(installer.subprocess, 'run', side_effect=execute) as run:
                installer.migrate_package()
                calls = [c.args[0] for c in run.call_args_list]
                self.assertIn(('sudo', 'pacman', '-R', 't3code-bin'), calls)
                self.assertIn(('sudo', 'repo-remove', str(repo / 'try-omarchy.db.tar.gz'), 't3code-bin'), calls)

    def test_migration_refuses_to_remove_running_package(self):
        with patch.object(installer.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
            with self.assertRaisesRegex(ValueError, 'Close the packaged'):
                installer.migrate_package()
            self.assertFalse(any(c.args[0][0] == 'sudo' for c in run.call_args_list))

    def test_wrapper_launches_appimage_with_flags_and_arguments(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'config').mkdir()
            (root / 'config/t3code-flags.conf').write_text('# comment\n--ozone-platform=wayland\n')
            shutil.copyfile(ASSETS / 't3code-wrapper', root / 'wrapper')
            app = root / 'T3-Code.AppImage'
            app.write_text('#!/bin/bash\nprintf "%s\\n" "$@"\n'); app.chmod(0o755)
            result = subprocess.run(['bash', str(root / 'wrapper'), 't3code://some/path'],
                                    env={**os.environ, 'XDG_CONFIG_HOME': str(root / 'config')}, capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.splitlines(), ['--ozone-platform=wayland', 't3code://some/path'])

    def test_menu_stops_before_theme_and_launch_when_install_fails(self):
        backport = next(p for p in SPEC['authenticity']['backports'] if p['id'] == 't3code-arm64-desktop')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'bin').mkdir()
            for target in backport['targets']:
                shutil.copyfile(GUEST / 'tests/fixtures' / Path(target['path']).name, root / target['path'])
            subprocess.run(['patch', '-p1', '-i', str(GUEST / backport['patch'])], cwd=root, check=True, capture_output=True)
            target = root / 'bin/omarchy-install-ai-t3-code'
            target.write_text(target.read_text().replace('/usr/local/lib/try-omarchy/install-t3code-arm64', 'fake-installer'))
            for name, body in {'uname':'echo aarch64', 'fake-installer':'exit 42',
                              'omarchy-theme-set-t3code':'touch "$HOME/theme"', 'omarchy-theme-refresh':'touch "$HOME/theme"'}.items():
                file=root/'bin'/name;file.write_text('#!/bin/bash\n'+body+'\n');file.chmod(0o755)
            result=subprocess.run(['bash',str(target)],env={**os.environ,'HOME':str(root),'PATH':str(root/'bin')+':'+os.environ['PATH']},capture_output=True)
            self.assertEqual(result.returncode,42)
            self.assertFalse((root/'theme').exists())

    def test_existing_guest_migration_accepts_original_and_previous_pr(self):
        for legacy in (False, True):
            with self.subTest(legacy=legacy), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); (root / 'usr/bin').mkdir(parents=True)
                (root / 'usr/share/try-omarchy').mkdir(parents=True)
                for name in ('omarchy-update', 'omarchy-install-ai-t3-code', 'omarchy-remove-ai-t3-code'):
                    source = ASSETS / ('legacy-' + name) if legacy and name != 'omarchy-remove-ai-t3-code' else GUEST / 'tests/fixtures' / name
                    shutil.copyfile(source, root / 'usr/bin' / name)
                old = copy.deepcopy(SPEC); del old['supplyChain']['t3code']
                specpath = root / 'usr/share/try-omarchy/build-spec.json'
                specpath.write_text(json.dumps(old))
                integration.install(GUEST, root)
                first = (root / 'usr/bin/omarchy-update').read_bytes()
                self.assertEqual(first, (GUEST / 'tests/fixtures/omarchy-update').read_bytes())
                integration.install(GUEST, root)
                self.assertEqual(first, (root / 'usr/bin/omarchy-update').read_bytes())
                self.assertEqual(json.loads(specpath.read_text())['upstream'], old['upstream'])
                (root / 'usr/bin/omarchy-update').write_text('# user change')
                with self.assertRaisesRegex(ValueError, 'differs from the reviewed version'):
                    integration.install(GUEST, root)
                self.assertEqual((root / 'usr/bin/omarchy-update').read_text(), '# user change')


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Apply the reviewed T3 Code AppImage installation integration to an existing guest."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install(guest, root):
    spec = json.loads((guest / 'spec.json').read_text())
    backport = next(p for p in spec['authenticity']['backports'] if p['id'] == 't3code-arm64-desktop')
    patch = guest / backport['patch']
    if digest(patch) != backport['patchSha256']:
        raise ValueError('T3 Code integration patch digest mismatch')
    pins = spec['supplyChain']['t3code']
    state = root / 'var/lib/try-omarchy'
    state.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='t3code-stage.', dir=state) as temporary:
        stage = Path(temporary)
        payload = {}
        for target in backport['targets']:
            dest = root / 'usr' / target['path']
            if dest.is_symlink() or not dest.is_file():
                raise ValueError(f'unsafe or missing command: {dest}')
            current = digest(dest)
            legacy = pins['legacyInstallSha256'] if target['path'] == 'bin/omarchy-install-ai-t3-code' else None
            if current not in (target['beforeSha256'], target['afterSha256'], legacy):
                raise ValueError(f'{dest} differs from the reviewed version; no files changed')
            # Each command can already have been migrated independently.
            if current == target['afterSha256']:
                continue
            staged = stage / target['path']
            staged.parent.mkdir(parents=True, exist_ok=True)
            source = dest
            if current == legacy:
                source = guest / 'tests/fixtures/omarchy-install-ai-t3-code'
                if digest(source) != target['beforeSha256']:
                    raise ValueError('installer preimage digest mismatch')
            shutil.copyfile(source, staged)
            section = next(part for part in patch.read_text().split('--- a/') if part.startswith(target['path'] + '\n'))
            subprocess.run(['patch', '--batch', str(staged)], input=('--- a/' + section).encode(), check=True, capture_output=True)
            if digest(staged) != target['afterSha256']:
                raise ValueError(f'patched command digest mismatch: {dest}')
            payload[dest] = (staged.read_bytes(), 0o755)
        # Retire the previous PR's stable-only update hook, including on old VMs.
        updater = root / 'usr/bin/omarchy-update'
        original = guest / 'tests/fixtures/omarchy-update'
        original_digest = 'cd1b703031a7456b2bd1302166a2cd29a1db8007f15bed954f64e742502aa552'
        if digest(original) != original_digest:
            raise ValueError('updater preimage digest mismatch')
        if updater.is_symlink() or not updater.is_file() or digest(updater) not in (original_digest, pins['legacyUpdateSha256']):
            raise ValueError(f'{updater} differs from the reviewed version; no files changed')
        if digest(updater) != original_digest:
            payload[updater] = (original.read_bytes(), 0o755)
        assets = guest / 'native-overlay/usr/local/share/try-omarchy/t3code'
        pins = spec['supplyChain']['t3code']
        for name, key in [('t3code-wrapper', 'wrapperSha256'), ('t3', 'cliSha256'),
                          ('resolve-release.py', 'resolverSha256'),
                          ('legacy-omarchy-install-ai-t3-code', 'legacyInstallSha256'),
                          ('legacy-omarchy-update', 'legacyUpdateSha256')]:
            source = assets / name
            if source.is_symlink() or digest(source) != pins[key]:
                raise ValueError(f'installer asset digest mismatch: {name}')
            payload[root / 'usr/local/share/try-omarchy/t3code' / name] = (source.read_bytes(), 0o644)
        helper = Path('usr/local/lib/try-omarchy/install-t3code-arm64')
        if digest(guest / 'native-overlay' / helper) != pins['installerSha256']:
            raise ValueError('installer digest mismatch')
        payload[root / helper] = ((guest / 'native-overlay' / helper).read_bytes(), 0o755)
        spec_path = root / 'usr/share/try-omarchy/build-spec.json'
        existing = json.loads(spec_path.read_text())
        existing['supplyChain']['t3code'] = pins
        payload[spec_path] = ((json.dumps(existing, indent=2) + '\n').encode(), 0o644)
        for dest in payload:
            if dest.is_symlink() or (dest.exists() and not dest.is_file()):
                raise ValueError(f'unsafe destination: {dest}')
        backup = Path(tempfile.mkdtemp(prefix='t3code-integration-backup.', dir=state))
        for dest in payload:
            if dest.exists():
                saved = backup / dest.relative_to(root)
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, saved)
        for dest, (data, mode) in payload.items():
            dest.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix='.t3code-', dir=dest.parent)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(data)
                    os.fchmod(stream.fileno(), mode)
                os.replace(temporary, dest)
            finally:
                Path(temporary).unlink(missing_ok=True)
    print(f'T3 Code menu and update integration installed. Backup: {backup}')


if __name__ == '__main__':
    if os.geteuid() != 0:
        raise SystemExit('Run with sudo to update the existing guest integration.')
    install(Path(__file__).resolve().parents[1], Path('/'))

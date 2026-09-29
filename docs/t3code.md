# T3 Code desktop on ARM64

Choose **Install → AI → T3 Code** in the Omarchy menu. The installer downloads
and verifies the latest stable official ARM64 AppImage, installs its runtime
dependencies (including FUSE 2), applies the Omarchy palette, and opens the app.
The factory contains only installer assets; the application downloads on demand.

## Updates and nightly builds

The intact AppImage lives at
`~/.local/share/try-omarchy/t3code/T3-Code.AppImage` (under `XDG_DATA_HOME`
when configured).
The file and directory belong to the guest user, so T3 Code can replace itself
without administrator access. The launcher uses a filename without a version
number, which Electron's AppImage updater preserves when installing updates.

Use T3 Code's settings to choose **Nightly** or check for updates. T3 Code owns
subsequent update downloads, installation, and restarts. `omarchy update` and
`yay` do not update this application. Running the installer again keeps the
existing AppImage, including its version and selected channel, and repairs the
launcher. Selecting stable again follows T3 Code's own version/downgrade policy.

The desktop entry is installed in the user's applications directory. Its wrapper
reads `~/.config/t3code-flags.conf` (or the configured `XDG_CONFIG_HOME`); each
nonempty, noncomment line is one Electron argument. A private `t3` wrapper beside
the AppImage runs its bundled CLI for initial theme selection. It follows the
updated AppImage and does not replace an independently installed `t3` command.
Omarchy continues to publish palette changes to T3 Code's existing theme file.

**Remove → AI → T3 Code** removes the AppImage and launcher, then applies
Omarchy's existing removal policy, which also deletes T3 Code configuration and
workspaces. The installer’s `--remove` option alone removes only application
files and the desktop entry.

## Existing VMs

Updating the Mac app does not change the integration on an existing guest disk.
From this Try Omarchy checkout inside the guest, run:

```sh
sudo python3 guest/scripts/install-t3code-integration.py
```

Close T3 Code, then select **Install → AI → T3 Code**. The installer stages the
verified AppImage before asking pacman to remove the old `t3code-bin` package.
It removes the old local repository entry too. Chats, settings, and projects are
preserved; this migration does not invoke Omarchy's app removal command.
If removal is cancelled, rerun Install to finish using the staged download.

The integration migration accepts both the pinned upstream commands and the
previous version of this PR. It retires the old stable-only `omarchy update`
hook, updates installation/removal commands, and backs up modified files under
`/var/lib/try-omarchy/t3code-integration-backup.*`. It refuses unrecognized command
edits before writing. New factory builds own the integration in
`try-omarchy-runtime`; reinstalling an older runtime can restore its old commands,
so rerun the migration if that happens.

## Verification and trust boundary

Installer inputs and Omarchy patches are checksum-pinned factory inputs. On the
first installation the helper resolves GitHub's stable release metadata, requires
the exact official ARM64 asset URL, and verifies the downloaded AppImage against
GitHub's SHA-256 digest before executing it or removing an old package. This
trusts the upstream GitHub account and HTTPS; it is not an independent signature
or a factory pin of the application version. Future updates use T3 Code's own
updater and verification policy.

The installer extracts only a desktop icon; the launcher always executes the
intact AppImage through its runtime. Download or checksum failures stop before
changing an installed package. The app's complete install → switch to nightly →
update → restart → menu launch flow should be verified in a disposable guest
before shipping a factory image.

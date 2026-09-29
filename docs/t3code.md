# T3 Code

Choose **Install → AI → T3 Code** to download the official ARM64 AppImage.
The installer sets up FUSE 2, the launcher, and the Omarchy theme.

Use **T3 Code’s settings** to update or switch to nightly. Reinstalling through
Omarchy keeps your current version and channel.

**Remove → AI → T3 Code** deletes the app, configuration, and workspaces.

## Existing VMs

Updating the Mac app does not migrate an existing VM. From this checkout
inside the guest, run:

```sh
sudo python3 guest/scripts/install-t3code-integration.py
```

Close T3 Code, then choose **Install → AI → T3 Code**. This replaces the old
pacman installation and preserves chats, settings, and projects. If you cancel
the package removal prompt, run Install again to finish.

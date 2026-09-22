# Working on Try Omarchy

[CONTRIBUTING.md](CONTRIBUTING.md) is authoritative for contributor requirements,
including issues, testing, build inputs, and PR evidence. Read it before making
changes.

## Project orientation

- The product is a native Apple Silicon macOS app running pinned upstream
  Omarchy in a project-built ARM64 guest with QEMU/HVF.
- Read [docs/architecture.md](docs/architecture.md) for component boundaries
  and the relevant component README before changing its behavior.
- `macos/` owns the native app, runtime patches, and host integration; `guest/`
  owns the image, package lock, and guest contracts. Use the root `Makefile`
  for builds and tests.

## Preparing contributions

- Use the appropriate [issue template](.github/ISSUE_TEMPLATE) for bug reports
  or large change proposals, following CONTRIBUTING.md.
- Use the [PR template](.github/pull_request_template.md), including when
  supplying a body through a CLI or API. Keep its checklist and provide the
  visual evidence required by CONTRIBUTING.md.
- Report exact verification commands and results, including failures and
  checks not run. Full native verification requires macOS; explain platform
  limitations rather than reporting skipped checks as passing.
- Leave missing validation or evidence unchecked. For conditional items that
  do not apply, explain why. Screenshots and recordings must show the actual
  app or guest; generated mockups are not verification evidence.

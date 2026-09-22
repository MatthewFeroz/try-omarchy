# Contributing

Thanks for helping improve Try Omarchy. The project has one product target: a
native Apple Silicon macOS app that runs pinned upstream Omarchy in a
project-built ARM64 virtual machine image.

## Before opening a pull request

1. Open an issue for large behavioral or architecture changes. Search existing
   open and closed issues first and use the appropriate issue template.
2. Keep changes within the current Apple Silicon, QEMU/HVF, and ARM64 guest
   architecture unless an architecture change has been discussed first.
3. Run `make test`.
4. If build inputs changed, run the relevant component build and explain how
   its pinned versions or checksums were reviewed.
5. Update documentation when commands, requirements, output paths, or security
   boundaries change.
6. Use the [PR template](.github/pull_request_template.md), explain what changed
   and why, link related issues, and complete its checklist honestly.
7. For UI changes, attach labeled before/after screenshots. For motion, timing,
   transitions, or interaction changes, also attach a short video.

Keep each PR focused on one problem. Record exact validation commands and
results, including anything that failed or could not run on your host. Leave
missing validation or visual evidence unchecked and explain what is outstanding.
Draft status is optional. For a conditional checklist item that does not apply,
explain why before checking it.
Checklist items are contributor attestations reviewed alongside CI; they are
not automated proof that screenshots or tests are sufficient.

Capture the actual app or guest in comparable before/after states and include
the steps needed to reproduce the change. Upload PR evidence to GitHub rather
than committing PR-only media. Remove secrets and unrelated personal information.

## Reporting issues

Use the bug report template for reproducible problems. Include the app version
or commit, macOS version, Apple chip, relevant guest/runtime details, steps to
reproduce, expected behavior, and actual behavior. Say when information is
unknown or a report has not been reproduced; do not guess. Include relevant
logs or visual evidence and link related reports.

Use the change proposal template for large behavioral or architecture changes.
Explain the user problem, proposed scope, alternatives, and validation plan.
Architecture changes must be discussed before implementation. Report suspected
vulnerabilities through [SECURITY.md](SECURITY.md), not public issues.

Agents should also follow [AGENTS.md](AGENTS.md) when preparing changes, issues,
and PRs.

## Build inputs and local state

The guest and QEMU supply chains are deliberately pinned. Do not update a URL,
commit, package lock, archive, or checksum independently of its associated
validation code.

Generated files in `dist/` and build caches in `macos/.build/` and
`guest/.work/` are not committed. Use `make clean` to remove project build
artifacts and caches. `make clean-all` additionally destroys persistent local
VM data and should only be used when a complete reset is intended.

Component builds use content-hashed state under `.build/state/`. A state file is
published only after the build succeeds and its output passes validation. Use
`FORCE=1` when reviewing reproducibility or when an intentionally unchanged
input must be rebuilt; do not work around the cache by editing generated state.

## Updating Omarchy

Pin an official upstream release, refresh the complete ARM64 transaction lock,
and verify the source contract with one command:

```sh
make update-omarchy OMARCHY_RELEASE=4.0.3
```

The command keeps a complete shallow source checkout under `.build/upstream/`,
verifies that its clean `HEAD` is the requested release tag, and derives the
commit, Git tree, normalized source digest, source timestamp, source-reported
version, and official release version. It then refreshes the package lock and
runs the guest contract against that exact checkout.

Before committing an update, review the upstream diff—especially changes to
`install/omarchy-base.packages`—against the intentionally trimmed
`guest/packages.txt`. Add runtime dependencies the native guest now needs, then
review every entry in `authenticity.backports`: drop a backport that the new
release contains, or refresh its strict preimage and postimage hashes after
review. Run `make guest` and `make test`. The upstream source can report a development
version even for an official tag, so never hand-edit the `version` or `release`
fields to make them agree; they record different upstream identities.

## Tests

Tests should describe a user-visible behavior, policy, data contract, or
process boundary. Keep presentation and edit rules in deterministic models that
can be exercised without opening AppKit windows. Do not make CI depend on pixel
coordinates, font metrics, display size, global window lookup, fixed run-loop
delays, or an assumed free network port.

Platform integration tests are appropriate when the operating-system boundary
is itself the contract. Use isolated temporary state, inject controllable
probes where the real resource is incidental, and use bounded readiness checks
instead of fixed settling delays.

By contributing, you agree that your contribution is licensed under the MIT
License in this repository.

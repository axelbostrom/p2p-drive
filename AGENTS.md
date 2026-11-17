# Project instructions

These instructions apply to the entire p2p-drive repository.

## Scope

- Implement only the work requested by the user. Initial repository setup does not authorize implementing the storage application.
- Keep changes focused and reviewable.

## Git and GitHub workflow

- Never commit directly to `main`. Create a descriptive feature branch from the latest `main` before editing, such as `feat/...`, `fix/...`, or `chore/...`.
- Check the working tree before changing branches; preserve existing user changes.
- Run relevant tests and checks before committing. Inspect the repository for the appropriate commands; do not invent passing results. If no test suite exists, run applicable validation and report that limitation.
- Inspect the staged diff before committing. Never commit secrets, credentials, private keys, tokens, or local environment files.
- Use descriptive commit messages that explain the change.
- Push feature branches to `origin` and create a pull request targeting `main` when the requested feature is complete.
- Include a clear description and actual validation results in each pull request.
- Never merge pull requests automatically or enable auto-merge. Leave merging to the user.
- Never force-push, including `--force-with-lease`.
- Do not bypass repository protections or hooks.

## Repository

- Canonical remote: `git@github.com:axelbostrom/p2p-drive.git`.
- Phase 1 uses Tahoe-LAFS 1.20.0, Docker, Helm, and the `k3d-p2p-drive` context. Do not operate on another cluster implicitly.
- Build/import: `./scripts/build.sh`. Deploy: `./scripts/deploy.sh`. Integration: `./scripts/test-recovery.sh`.
- Before committing run `helm lint charts/tahoe-lafs`, render with `gridEnabled=true`, `bash -n` for each script in `scripts/*.sh`, `python3 -m py_compile docker/entrypoint.py scripts/*.py`, and `git diff --check`. Run recovery integration for storage, chart, image, or script changes when the local cluster is available.
- Never print or commit Tahoe capabilities, introducer FURLs, generated node directories, or private identities. Use the bootstrap Secret flow and ignored `.local/` for local artifacts.
- Recovery tests may scale storage StatefulSets to zero temporarily; always restore them and retain PVCs. Do not delete persistent data to simulate an outage.

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
- Application tooling and tests have not been selected yet. Update these instructions with actual development and test commands when tooling is introduced.

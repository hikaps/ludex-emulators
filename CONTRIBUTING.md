# Contributing

Setup, code conventions and testing are in [AGENTS.md](AGENTS.md).

## Branches

- `main`: stable. A release PR merged here is tagged `vX.Y.Z` (see Releases).
- `develop`: integration.
- One feature or fix per branch, created from `origin/develop` (preferably in its own `git worktree`) and named after the change (for example `pcsx2-install`). Open the PR with `gh pr create --base develop`; the default branch is `main`, so `--base` is required.
- A PR is merged only after the maintainer explicitly approves that PR; green CI alone never merges it. Wait for `Tests (Python 3.11)` and `Tests (Python 3.14)`, report, and stop.
- Feature PRs are squash-merged into `develop`; the PR title becomes the commit subject and must follow the commit conventions below. Never force-push `main` or `develop`.

## Commits and PRs

- Conventional Commits: `<type>(<optional-scope>): <summary>`; types `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`, `chore`. Scopes name the subsystem (`manifest`, `installer`, `roms`, `plugin`).
- Imperative subject, no trailing period, at most 72 characters including the `(#N)` that squash merges append, so keep PR titles to 68 or fewer.
- One logical change per commit, with its tests and docs. Body: motivation, constraints, and verification actually performed.
- PR descriptions follow `.github/pull_request_template.md` (What, Why, Verification) and state what was not verified. Keep PR communication in the description; do not post progress comments.
- Manifest changes: the PR states the upstream release page the checksum was taken from and how the size and hash were cross-checked.

## Releases

1. In a feature PR on `develop`, bump `version` in `pyproject.toml` and `__version__` in `src/ludex_emulators/__init__.py` together (plain `X.Y.Z`, equal).
2. Open a PR from `develop` to `main` titled `chore(release): X.Y.Z` and merge it with a merge commit (never squash, or the branches diverge), only with the maintainer's approval.
3. Tag the merge commit `vX.Y.Z` and create a GitHub Release. Users install with `ludex plugin add git+https://github.com/hikaps/ludex-emulators@vX.Y.Z`.

CI: `tests.yml` runs on every push and PR (Python 3.11 and 3.14).

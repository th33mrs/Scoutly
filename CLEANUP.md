# DevOps cleanup — handoff

This doc covers the changes staged in your two repos and the manual
steps you need to run to land them.

## What changed

### `TrovlyAI` (this repo)

Added:

- `Dockerfile` — multi-stage Python 3.11-slim image, runs as non-root
  `trovly` user, healthcheck against `/_stcore/health`, defaults to
  `streamlit run app_hosted.py`.
- `docker-compose.yml` — local dev with hot-reload via bind-mount.
- `.dockerignore` — keeps secrets, caches, and `venv/` out of the image.
- `Makefile` — `make dev | down | logs | shell | lint | fmt | test |
  audit | clean`.
- `pyproject.toml` — ruff + black + pytest config (line-length 100,
  py311 target, security/bugbear/simplify rules on).
- `requirements-dev.txt` — pins ruff, black, pytest, pytest-cov,
  pip-audit, detect-secrets.
- `SECURITY.md` — vuln reporting + secrets policy.
- `.github/workflows/ci.yml` — lint → test → docker build →
  gitleaks secret scan, on push and PR.
- `.github/dependabot.yml` — weekly updates for pip, GitHub Actions,
  and Docker base images.
- `.github/PULL_REQUEST_TEMPLATE.md`.

Replaced:

- `.gitignore` — broader coverage (model caches, OS noise, IDE,
  `.streamlit/secrets.toml`, lint caches, etc.) and explicit
  `!.env.example` so the template is always tracked.
- `.env.example` — now lists every var `config.py:get_secret()` reads,
  plus `TROVLY_ENV` and `LOG_LEVEL` as runtime knobs.

### `trovly-landing` (sibling repo)

Added: `.gitignore`, `README.md`, `Dockerfile` (nginx:1.27-alpine
serving `index.html`), `docker-compose.yml`, `Makefile`, `.htmlhintrc`,
`.github/workflows/ci.yml` (htmlhint + lychee link check + docker
build), `.github/dependabot.yml`.

## What did **not** change (intentional)

- `app.py` (legacy local) and `app_hosted.py` (production) are still
  side-by-side. They diverged early. Pick one to be the canonical
  entrypoint — recommend renaming `app_hosted.py` → `app.py` and
  deleting the legacy file in a follow-up PR.
- `config_cloud.py` and `config.py.template` are tracked but unused
  (no `import config_cloud` anywhere). Recommend deleting in the same
  follow-up PR — they're noise.
- `app_hosted.py` has two `import config` statements buried inside
  function bodies (lines 310, 362). Lift to top of file when you
  refactor.
- No tests yet — `tests/` directory doesn't exist. CI's `test` job
  no-ops gracefully until you add it.

## Audit notes

- **Secrets:** `.env` on disk has a live Discord webhook URL. I
  searched git history (`git log -S "discord.com/api/webhooks/"`) —
  the live URL is **not** in any commit, only in your local `.env`.
  No history rewrite needed.
- **Large local junk:** `venv/` is 1.1 GB, `job_scanner.log` is 460
  KB, `__pycache__/` is 132 KB. All gitignored, so harmless to git
  but you can `make clean` to free disk.

## Land the changes

The repo currently has a stuck `.git/index.lock` — clear it first.

```sh
cd /Users/carlysejordan/PenTest_Princess/job_scanner

# 1. Clear the stale lock and confirm clean state
rm -f .git/index.lock
git status

# 2. Cut the cleanup branch and stage everything
git checkout -b chore/devops-cleanup
git add .gitignore .env.example pyproject.toml requirements-dev.txt \
        Dockerfile .dockerignore docker-compose.yml Makefile \
        SECURITY.md CLEANUP.md \
        .github/workflows/ci.yml .github/dependabot.yml \
        .github/PULL_REQUEST_TEMPLATE.md
git status   # eyeball the diff
git commit -m "chore(devops): hygiene, CI, Docker dev env, dependabot"

# 3. Push and open the PR
git push -u origin chore/devops-cleanup
```

Same flow for the landing repo:

```sh
cd /Users/carlysejordan/PenTest_Princess/trovly-landing
git checkout -b chore/devops-cleanup
git add .gitignore README.md Dockerfile docker-compose.yml Makefile \
        .htmlhintrc .github/workflows/ci.yml .github/dependabot.yml
git commit -m "chore(devops): add .gitignore, README, Docker, CI"
git push -u origin chore/devops-cleanup
```

## Run the dev site

```sh
cd /Users/carlysejordan/PenTest_Princess/job_scanner
cp .env.example .env       # then fill in real values
make dev                    # → http://localhost:8501

# Landing dev preview:
cd ../trovly-landing
make dev                    # → http://localhost:8080
```

## Recommended follow-ups (separate PRs)

1. **Collapse `app.py` / `app_hosted.py`** into a single entrypoint
   driven by `TROVLY_ENV` (dev vs prod feature flags).
2. **Delete unused config files** (`config_cloud.py`,
   `config.py.template`).
3. **Add `tests/`** — start with `test_security.py` (input
   validation, bcrypt round-trip) and `test_matcher.py` (similarity
   threshold sanity).
4. **Run `make fmt` once** to apply black/ruff to the existing
   codebase. Big diff, but does it once and CI keeps it clean
   forever.
5. **Streamlit Cloud staging app:** when you want a hosted dev site,
   create a second Streamlit Cloud app pointed at the `dev` branch
   and CNAME `dev.trovlyai.us` to it in Cloudflare DNS.

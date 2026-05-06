# Security Policy

## Reporting a vulnerability

Please do **not** open a public GitHub issue for security findings.
Email `terronchapman@gmail.com` with details and a proof-of-concept if
possible. We aim to acknowledge within 72 hours.

## Secrets

- All secrets load from environment variables via `security.get_secret()`.
- `.env` is the local secret store and is gitignored. Use `.env.example`
  as a template.
- Streamlit Cloud secrets live in the app's "Secrets" pane, not in code.
- Rotate any credential that touched a workstation or a non-prod
  environment before promoting it to production.

## Authentication

- Passwords are stored bcrypt-hashed (`auth.py`).
- Account lockout, rate limiting, and input validation are in
  `security.py`.
- Sessions are scoped per Streamlit user; do not share tokens across
  environments.

## Dependencies

- Pinned dev dependencies live in `requirements-dev.txt`.
- Production dependencies live in `requirements.txt`.
- Dependabot (see `.github/dependabot.yml`) opens PRs weekly for
  security updates.

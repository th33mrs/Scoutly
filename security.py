"""
Scoutly - Security Module
====================================
Handles secrets management, input sanitization, and secure defaults.

Security principles applied:
  1. Secrets never live in source code — use environment variables or .env
  2. All external input is sanitized before processing
  3. Dependencies are pinned to exact versions
  4. File permissions are restricted
  5. API responses are validated before use
  6. Logging never exposes secrets
"""

import logging
import os
import re
import stat
from pathlib import Path

logger = logging.getLogger("job_scanner.security")


# ─── Secrets Management ────────────────────────────────────────────
# Instead of hardcoding API keys in config.py, load from environment
# variables or a .env file. This prevents accidental exposure in git.

def get_secret(key, default=""):
    """
    Load a secret from environment variables.

    Priority order:
      1. OS environment variable (export DISCORD_WEBHOOK_URL=...)
      2. .env file in project directory
      3. Fall back to default (empty string)

    NEVER log the actual secret value.
    """
    # Check OS environment first
    value = os.environ.get(key, "")
    if value:
        logger.debug("Loaded secret '{}' from environment".format(key))
        return value

    # Check .env file
    env_path = Path(".env")
    if env_path.exists():
        try:
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")  # Remove surrounding quotes
                        if k == key:
                            logger.debug("Loaded secret '{}' from .env".format(key))
                            return v
        except Exception as e:
            logger.error("Error reading .env file: {}".format(e))

    return default


def mask_secret(value, visible_chars=4):
    """
    Mask a secret for safe logging.
    'https://discord.com/api/webhooks/123/abcdef' → '...cdef'
    """
    if not value or len(value) <= visible_chars:
        return "***"
    return "...{}".format(value[-visible_chars:])


# ─── Input Sanitization ────────────────────────────────────────────
# External input (job descriptions, API responses) must be cleaned
# before rendering in Streamlit or storing in JSON.

def sanitize_html(text):
    """
    Remove potentially dangerous HTML/JS from text.
    Prevents XSS if rendered in Streamlit with unsafe_allow_html.
    """
    if not text:
        return ""
    # Remove script tags and their content
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove event handlers (onclick, onerror, etc.)
    text = re.sub(r"\bon\w+\s*=\s*[\"'][^\"']*[\"']", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bon\w+\s*=\s*\S+", "", text, flags=re.IGNORECASE)
    # Remove iframes
    text = re.sub(r"<iframe[^>]*>.*?</iframe>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove object/embed tags
    text = re.sub(r"<(object|embed|applet)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove javascript: URLs
    text = re.sub(r"javascript\s*:", "", text, flags=re.IGNORECASE)
    # Remove data: URLs (can contain scripts)
    text = re.sub(r"data\s*:[^,]*;base64", "", text, flags=re.IGNORECASE)
    return text


def sanitize_filename(name):
    """Sanitize a string for use as a filename."""
    # Remove path separators and null bytes
    name = re.sub(r"[/\\:\x00]", "", name)
    # Remove other potentially dangerous characters
    name = re.sub(r"[^a-zA-Z0-9._\-]", "_", name)
    # Prevent directory traversal
    name = name.lstrip(".")
    return name[:100]  # Limit length


def validate_url(url):
    """Basic URL validation — reject suspicious patterns."""
    if not url:
        return False
    # Must start with http:// or https://
    if not re.match(r"^https?://", url, re.IGNORECASE):
        return False
    # Reject javascript: and data: schemes
    if re.match(r"^(javascript|data|file|ftp):", url, re.IGNORECASE):
        return False
    # Reject URLs with @ (potential credential stuffing)
    if "@" in url.split("//", 1)[-1].split("/", 1)[0]:
        return False
    return True


# ─── API Response Validation ───────────────────────────────────────

def validate_api_response(response, expected_keys=None):
    """
    Validate an API response before trusting its data.
    Returns (is_valid, data_or_error_message).
    """
    # Check status code
    if response.status_code != 200:
        return False, "HTTP {}".format(response.status_code)

    # Check content type
    content_type = response.headers.get("content-type", "")
    if "json" not in content_type and "xml" not in content_type and "rss" not in content_type:
        # Allow text responses but log a warning
        logger.warning("Unexpected content-type: {}".format(content_type))

    # Try to parse JSON
    try:
        data = response.json()
    except Exception:
        return False, "Invalid JSON response"

    # Check for expected keys if specified
    if expected_keys:
        missing = [k for k in expected_keys if k not in data]
        if missing:
            return False, "Missing keys: {}".format(missing)

    return True, data


# ─── File Security ──────────────────────────────────────────────────

def secure_file_permissions(filepath):
    """
    Set file permissions to owner-only read/write (600).
    Prevents other users on the system from reading your data.
    """
    path = Path(filepath)
    if path.exists():
        # 0o600 = owner read+write only, no group/other access
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        logger.debug("Secured permissions on {}".format(filepath))


def secure_data_files():
    """Secure all data files in the project."""
    sensitive_files = [
        ".env",
        "config.py",
        "seen_jobs.json",
        "tracked_jobs.json",
        "saved_jds.json",
        "job_scanner.log",
    ]
    for f in sensitive_files:
        if Path(f).exists():
            secure_file_permissions(f)


# ─── Rate Limiting ──────────────────────────────────────────────────

class RateLimiter:
    """
    Simple in-memory rate limiter to prevent API abuse.
    Tracks call timestamps per source and enforces minimum intervals.
    """

    def __init__(self):
        self._last_call = {}  # source_name -> timestamp

    def can_call(self, source, min_interval_sec=1.0):
        """Check if enough time has passed since last call to this source."""
        import time
        now = time.time()
        last = self._last_call.get(source, 0)
        if now - last >= min_interval_sec:
            self._last_call[source] = now
            return True
        return False

    def wait_if_needed(self, source, min_interval_sec=1.0):
        """Block until rate limit allows the next call."""
        import time
        now = time.time()
        last = self._last_call.get(source, 0)
        wait_time = min_interval_sec - (now - last)
        if wait_time > 0:
            time.sleep(wait_time)
        self._last_call[source] = time.time()


# Global rate limiter instance
rate_limiter = RateLimiter()


# ─── Security Audit ────────────────────────────────────────────────

def run_security_audit():
    """
    Check for common security issues in the project.
    Run with: python security.py
    """
    issues = []
    warnings = []

    # Check for plaintext secrets in config.py
    if Path("config.py").exists():
        with open("config.py", "r") as f:
            config_text = f.read()
        if "discord.com/api/webhooks/" in config_text:
            issues.append("Discord webhook URL is hardcoded in config.py — move to .env")
        if re.search(r'ADZUNA_APP_ID\s*=\s*"[^"]{5,}"', config_text):
            issues.append("Adzuna API key is hardcoded in config.py — move to .env")
        if re.search(r'TELEGRAM_BOT_TOKEN\s*=\s*"[^"]{5,}"', config_text):
            issues.append("Telegram token is hardcoded in config.py — move to .env")

    # Check for .env file
    if not Path(".env").exists():
        warnings.append("No .env file found — create one for secrets management")

    # Check for .gitignore
    if Path(".gitignore").exists():
        with open(".gitignore", "r") as f:
            gitignore = f.read()
        if ".env" not in gitignore:
            issues.append(".env is not in .gitignore — secrets will be committed")
        if "*.json" not in gitignore and "tracked_jobs.json" not in gitignore:
            warnings.append("JSON data files not in .gitignore")
    else:
        issues.append("No .gitignore file — create one before pushing to GitHub")

    # Check file permissions
    sensitive_files = [".env", "config.py"]
    for f in sensitive_files:
        if Path(f).exists():
            mode = oct(os.stat(f).st_mode)[-3:]
            if mode != "600":
                warnings.append("{} has permissions {} — should be 600".format(f, mode))

    # Check dependency pinning
    if Path("requirements.txt").exists():
        with open("requirements.txt", "r") as f:
            for line in f:
                if ">=" in line and "==" not in line:
                    warnings.append("Unpinned dependency: {} — pin with ==".format(line.strip()))

    # Print results
    print("\n" + "=" * 55)
    print("  SECURITY AUDIT")
    print("=" * 55)

    if issues:
        print("\n  ISSUES (fix these before going public)")
        for i in issues:
            print("    [X] {}".format(i))
    else:
        print("\n  No critical issues found")

    if warnings:
        print("\n  WARNINGS (recommended fixes)")
        for w in warnings:
            print("    [!] {}".format(w))
    else:
        print("\n  No warnings")

    print("\n  RECOMMENDATIONS")
    print("    1. Move all secrets to .env file")
    print("    2. Add .env and *.json to .gitignore")
    print("    3. Pin all dependencies to exact versions")
    print("    4. Run: python security.py  (this audit) before every commit")
    print("    5. Run: pip audit  (checks for known vulnerabilities)")
    print("=" * 55)

    return len(issues) == 0


if __name__ == "__main__":
    run_security_audit()

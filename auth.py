"""
Trovly - Authentication (Hardened)
Security features:
- bcrypt password hashing (replaces SHA-256)
- Email + username uniqueness checks
- Password strength requirements
- Rate limiting on login attempts
- Account lockout after failed attempts
- Timing attack protection (constant-time comparison)
- Email format validation
- Username format validation (no special chars except _ and -)
"""

import json
import logging
import re
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path

import bcrypt
import streamlit as st

logger = logging.getLogger("trovly.auth")

# Security settings
MIN_PASSWORD_LENGTH = 12
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
RATE_LIMIT_SECONDS = 2
BCRYPT_ROUNDS = 12

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def hash_password(password):
    """Hash password using bcrypt with random salt."""
    if isinstance(password, str):
        password = password.encode("utf-8")
    return bcrypt.hashpw(password, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(password, stored_hash):
    """Verify password against bcrypt hash. Constant-time comparison."""
    if isinstance(password, str):
        password = password.encode("utf-8")
    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode("utf-8")
    try:
        return bcrypt.checkpw(password, stored_hash)
    except Exception as e:
        logger.error("Password verification error: {}".format(e))
        return False


def validate_username(username):
    """Validate username format."""
    if not username or not isinstance(username, str):
        return False, "Username is required"
    username = username.strip()
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 32:
        return False, "Username must be 32 characters or less"
    if not USERNAME_PATTERN.match(username):
        return False, "Username can only contain letters, numbers, underscores, and hyphens"
    return True, username


def validate_email(email):
    """Validate email format."""
    if not email or not isinstance(email, str):
        return False, "Email is required"
    email = email.strip().lower()
    if len(email) > 254:
        return False, "Email is too long"
    if not EMAIL_PATTERN.match(email):
        return False, "Invalid email format"
    return True, email


def validate_password(password):
    """Validate password strength."""
    if not password or not isinstance(password, str):
        return False, "Password is required"
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, "Password must be at least {} characters".format(MIN_PASSWORD_LENGTH)
    if len(password) > 128:
        return False, "Password is too long (max 128 characters)"

    has_upper = bool(re.search(r"[A-Z]", password))
    has_lower = bool(re.search(r"[a-z]", password))
    has_digit = bool(re.search(r"[0-9]", password))
    has_special = bool(re.search(r"[!@#$%^&*()_+\-=\[\]{};:,.<>?/]", password))

    strength_count = sum([has_upper, has_lower, has_digit, has_special])
    if strength_count < 3:
        return False, "Password must contain at least 3 of: uppercase, lowercase, numbers, special characters"

    common_passwords = {
        "password", "12345678", "qwerty", "letmein", "welcome",
        "admin123", "password123", "trovly", "trovlyai",
    }
    if password.lower() in common_passwords:
        return False, "This password is too common, please choose another"

    return True, "Strong password"


def load_users():
    """Load all users from disk."""
    users_path = Path("users.json")
    if not users_path.exists():
        return {}
    try:
        return json.loads(users_path.read_text())
    except Exception as e:
        logger.error("Error loading users: {}".format(e))
        return {}


def save_users(users):
    """Save all users to disk."""
    users_path = Path("users.json")
    users_path.write_text(json.dumps(users, indent=2))


def email_exists(email, exclude_username=None):
    """Check if email is already in use."""
    email = email.lower().strip()
    users = load_users()
    for uname, data in users.items():
        if uname == exclude_username:
            continue
        if data.get("email", "").lower().strip() == email:
            return True
    return False


def username_exists(username):
    """Check if username is already taken."""
    users = load_users()
    return username in users


def is_account_locked(username):
    """Check if account is currently locked due to failed attempts."""
    users = load_users()
    user = users.get(username, {})
    locked_until = user.get("locked_until")
    if not locked_until:
        return False, None

    try:
        lock_time = datetime.fromisoformat(locked_until)
        if datetime.now() < lock_time:
            remaining = (lock_time - datetime.now()).total_seconds() / 60
            return True, "Account locked. Try again in {} minutes".format(int(remaining) + 1)
    except Exception:
        pass
    return False, None


def record_failed_login(username):
    """Track failed login attempts and lock account if threshold reached."""
    users = load_users()
    if username not in users:
        return

    user = users[username]
    failed = user.get("failed_attempts", 0) + 1
    user["failed_attempts"] = failed
    user["last_failed_attempt"] = datetime.now().isoformat()

    if failed >= MAX_LOGIN_ATTEMPTS:
        lock_until = datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
        user["locked_until"] = lock_until.isoformat()
        logger.warning("Account locked: {} after {} failed attempts".format(username, failed))

    users[username] = user
    save_users(users)


def reset_failed_attempts(username):
    """Clear failed attempt counter on successful login."""
    users = load_users()
    if username in users:
        users[username]["failed_attempts"] = 0
        users[username]["locked_until"] = None
        users[username]["last_login"] = datetime.now().isoformat()
        save_users(users)


def check_credentials(username, password):
    """
    Verify login credentials with security protections.
    Returns (success, message).
    """
    if not username or not password:
        time.sleep(RATE_LIMIT_SECONDS)
        return False, "Username and password are required"

    users = load_users()

    # Always do a bcrypt operation to prevent username enumeration via timing
    if username not in users:
        bcrypt.checkpw(b"dummy", bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=4)))
        time.sleep(RATE_LIMIT_SECONDS)
        return False, "Invalid username or password"

    locked, lock_msg = is_account_locked(username)
    if locked:
        return False, lock_msg

    user = users[username]
    stored_hash = user.get("password_hash", "")

    if not verify_password(password, stored_hash):
        record_failed_login(username)
        time.sleep(RATE_LIMIT_SECONDS)
        attempts_left = MAX_LOGIN_ATTEMPTS - user.get("failed_attempts", 0) - 1
        if attempts_left <= 2 and attempts_left > 0:
            return False, "Invalid credentials. {} attempts remaining before lockout.".format(attempts_left)
        return False, "Invalid username or password"

    reset_failed_attempts(username)
    return True, "Login successful"


def register_user(username, password, email):
    """
    Register new user with full validation.
    Returns (success, message).
    """
    # Validate username
    valid, result = validate_username(username)
    if not valid:
        return False, result
    username = result

    # Validate email
    valid, result = validate_email(email)
    if not valid:
        return False, result
    email = result

    # Validate password
    valid, result = validate_password(password)
    if not valid:
        return False, result

    # Check uniqueness
    if username_exists(username):
        return False, "Username already taken"

    if email_exists(email):
        return False, "An account with this email already exists"

    # Create user
    users = load_users()
    users[username] = {
        "password_hash": hash_password(password),
        "email": email,
        "created_at": datetime.now().isoformat(),
        "last_login": None,
        "failed_attempts": 0,
        "locked_until": None,
        "tier": "free",
        "resume": "",
        "queries": [],
        "threshold": 0.55,
        "remote_only": True,
    }
    save_users(users)
    logger.info("New user registered: {}".format(username))
    return True, "Account created successfully"


def get_user_data(username):
    """Get user profile data."""
    users = load_users()
    return users.get(username, {})


def save_user_data(username, data):
    """Update user profile data (excludes auth fields)."""
    users = load_users()
    if username in users:
        # Don't allow auth fields to be overwritten
        protected_fields = {"password_hash", "failed_attempts", "locked_until", "created_at"}
        safe_data = {k: v for k, v in data.items() if k not in protected_fields}
        users[username].update(safe_data)
    else:
        users[username] = data
    save_users(users)


def login_page():
    """Render login/register page."""
    if "authenticated" in st.session_state and st.session_state.authenticated:
        return st.session_state.username

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
        <div style='text-align:center; padding: 2rem 0 1rem;'>
            <div style='width: 64px; height: 64px; margin: 0 auto 16px; background: linear-gradient(135deg, #fde047 0%, #fbbf24 30%, #f97316 65%, #ec4899 100%); border-radius: 16px; display: flex; align-items: center; justify-content: center; color: #0d1117; font-family: Outfit, sans-serif; font-weight: 700; font-size: 36px; box-shadow: 0 8px 24px rgba(251, 191, 36, 0.3);'>T</div>
            <h1 style='font-family: Outfit, sans-serif; font-weight: 700; font-size: 36px; margin: 0; background: linear-gradient(135deg, #fbbf24 0%, #ec4899 100%); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;'>Trovly</h1>
            <p style='color:#cbd5e1; margin-top: 8px; letter-spacing: 0.05em;'>AI JOB INTELLIGENCE</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

        tab_login, tab_register = st.tabs(["Log in", "Sign up"])

        with tab_login:
            login_user = st.text_input("Username", key="login_user", max_chars=32)
            login_pass = st.text_input("Password", type="password", key="login_pass", max_chars=128)

            if st.button("Log in", type="primary", use_container_width=True):
                success, msg = check_credentials(login_user.strip(), login_pass)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.username = login_user.strip()
                    st.rerun()
                else:
                    st.error(msg)

        with tab_register:
            reg_user = st.text_input("Username", key="reg_user", max_chars=32,
                                     help="3-32 characters. Letters, numbers, underscores, hyphens only.")
            reg_email = st.text_input("Email", key="reg_email", max_chars=254)
            reg_pass = st.text_input("Password", type="password", key="reg_pass", max_chars=128,
                                     help="At least 12 characters with 3 of: uppercase, lowercase, numbers, symbols")
            reg_pass2 = st.text_input("Confirm password", type="password", key="reg_pass2", max_chars=128)

            if st.button("Create account", type="primary", use_container_width=True):
                if reg_pass != reg_pass2:
                    st.error("Passwords don't match")
                else:
                    success, msg = register_user(reg_user, reg_pass, reg_email)
                    if success:
                        st.success(msg + ". Log in above.")
                    else:
                        st.error(msg)

    return None


def logout():
    """Clear session state."""
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.rerun()

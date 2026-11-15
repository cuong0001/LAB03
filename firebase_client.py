"""Firebase email/password sign-in"""
import time

import requests

from config import FIREBASE_API_KEY, FIREBASE_PROJECT_ID

REQUEST_TIMEOUT = 15  # a dead connection must not freeze the UI


class FirebaseError(Exception):
    """A short message safe to display, without raw responses or credentials."""


def validate_config():
    """Check .env locally; this does not contact Firebase."""
    if not FIREBASE_PROJECT_ID or not FIREBASE_API_KEY:
        raise FirebaseError("Copy .env.example to .env, fill in Project ID and Web API Key, "
                            "then restart the app.")


def _authenticate(action, email, password):
    validate_config()
    email = email.strip()
    if not email or not password:
        raise FirebaseError("Enter both email and password.")
    try:
        response = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:{action}",
            params={"key": FIREBASE_API_KEY},
            json={"email": email, "password": password, "returnSecureToken": True},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        # Raw exceptions can contain the API key in the URL: never show them.
        raise FirebaseError("Cannot reach Firebase. Check your connection and try again.") from None
    try:
        data = response.json()
    except ValueError:
        raise FirebaseError("Firebase returned an unexpected response. Try again later.") from None
    if response.ok:
        return data

    error = data.get("error", {}) if isinstance(data, dict) else {}
    code = str(error.get("message", "")) if isinstance(error, dict) else ""
    if "EMAIL_EXISTS" in code:
        raise FirebaseError("That email is already registered. Choose Sign in instead.")
    if "OPERATION_NOT_ALLOWED" in code:
        raise FirebaseError("Enable Email/Password in Firebase Console > Authentication > Sign-in method.")
    if "WEAK_PASSWORD" in code or "PASSWORD_DOES_NOT_MEET_REQUIREMENTS" in code:
        raise FirebaseError("Choose a stronger password (at least 6 characters).")
    if "INVALID_EMAIL" in code:
        raise FirebaseError("Enter a valid email address.")
    if any(c in code for c in ("INVALID_LOGIN_CREDENTIALS", "INVALID_PASSWORD", "EMAIL_NOT_FOUND")):
        raise FirebaseError("Sign-in failed. Check your email and password.")
    if "USER_DISABLED" in code:
        raise FirebaseError("This account has been disabled.")
    if "TOO_MANY_ATTEMPTS" in code or response.status_code == 429:
        raise FirebaseError("Too many requests. Wait a little before trying again.")
    if "API_KEY" in code:
        raise FirebaseError("Check FIREBASE_API_KEY in .env.")
    raise FirebaseError("Firebase could not complete the request. Check your setup.")


def create_account(email, password):
    """Create an app account. Tokens are discarded: the user signs in next."""
    _authenticate("signUp", email, password)


def sign_in(email, password):
    """Return session data (never the password). Do not log this dictionary."""
    data = _authenticate("signInWithPassword", email, password)
    return {
        "uid": data["localId"],
        "email": data["email"],
        "id_token": data["idToken"],
        "expires_at": time.time() + int(data["expiresIn"]),
    }
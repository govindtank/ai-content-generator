from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.db import get_user_by_id, get_provider_api_keys

        user = get_user_by_id(session.get("user_id"))
        if not user:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("auth.login"))

        # Check if user has at least one provider API key
        has_key = bool(user.get("gemini_api_key", ""))
        if not has_key:
            provider_keys = get_provider_api_keys(user["id"])
            has_key = any(k["api_key"] for k in provider_keys)

        if not has_key:
            flash("Please set at least one API key in Settings to generate content.", "warning")
            return redirect(url_for("dashboard.settings"))
        return f(*args, **kwargs)
    return decorated_function

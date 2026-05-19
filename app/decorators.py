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
        from app.db import get_user_by_id
        user = get_user_by_id(session.get("user_id"))
        if not user or not user["gemini_api_key"]:
            flash("Please set your Gemini API key in settings.", "warning")
            return redirect(url_for("dashboard.settings"))
        return f(*args, **kwargs)
    return decorated_function

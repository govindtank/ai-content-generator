import secrets
import json
from urllib.parse import urlencode

import requests
from flask import (
    Blueprint,
    session,
    redirect,
    request,
    url_for,
    render_template,
    flash,
)
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.config import Config
from app.db import (
    get_user_by_google_id,
    create_user,
    update_user_google_info,
)

auth_bp = Blueprint("auth", __name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
SCOPES = [
    "openid",
    "email",
    "profile",
]


@auth_bp.route("/login")
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard.index"))
    
    # Dev mode: show dev login if Google OAuth not configured
    has_google_auth = bool(Config.GOOGLE_CLIENT_ID)
    
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    params = {
        "client_id": Config.GOOGLE_CLIENT_ID or "dev",
        "redirect_uri": Config.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    auth_uri = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return render_template("login.html", auth_url=auth_uri, has_google_auth=has_google_auth)


@auth_bp.route("/dev-login", methods=["POST"])
def dev_login():
    """Dev-mode local login (no Google OAuth required)."""
    name = (request.form.get("name") or "Dev User").strip()
    # Create or get a dev user
    from app.db import get_db
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", ("dev@localhost",)).fetchone()
    if user:
        session["user_id"] = user["id"]
        session["user_name"] = name
        session["user_avatar"] = ""
        session["user_email"] = "dev@localhost"
    else:
        import uuid
        db.execute(
            "INSERT INTO users (google_id, email, name, avatar_url) VALUES (?, ?, ?, ?)",
            (f"dev_{uuid.uuid4().hex[:12]}", "dev@localhost", name, ""),
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE email = ?", ("dev@localhost",)).fetchone()
        session["user_id"] = user["id"]
        session["user_name"] = name
        session["user_avatar"] = ""
        session["user_email"] = "dev@localhost"
    flash(f"Signed in as {name} (dev mode)", "success")
    return redirect(url_for("dashboard.index"))


@auth_bp.route("/auth/callback")
def callback():
    error = request.args.get("error")
    if error:
        flash(f"Google sign-in failed: {error}", "danger")
        return redirect(url_for("auth.login"))

    state = request.args.get("state")
    saved_state = session.pop("oauth_state", None)
    if not state or state != saved_state:
        flash("Security check failed. Please try again.", "danger")
        return redirect(url_for("auth.login"))

    code = request.args.get("code")
    if not code:
        flash("No authorization code received.", "danger")
        return redirect(url_for("auth.login"))

    token_data = {
        "code": code,
        "client_id": Config.GOOGLE_CLIENT_ID,
        "client_secret": Config.GOOGLE_CLIENT_SECRET,
        "redirect_uri": Config.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    resp = requests.post(GOOGLE_TOKEN_URL, data=token_data, timeout=10)
    if not resp.ok:
        flash("Failed to exchange authorization code.", "danger")
        return redirect(url_for("auth.login"))

    tokens = resp.json()
    id_token_str = tokens.get("id_token")

    try:
        info = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            Config.GOOGLE_CLIENT_ID,
        )
    except ValueError as e:
        flash(f"Invalid ID token: {e}", "danger")
        return redirect(url_for("auth.login"))

    google_id = info.get("sub")
    email = info.get("email", "")
    name = info.get("name", "")
    avatar = info.get("picture", "")

    user = get_user_by_google_id(google_id)
    if user:
        update_user_google_info(user["id"], email, name, avatar)
        session["user_id"] = user["id"]
    else:
        user_id = create_user(google_id, email, name, avatar)
        session["user_id"] = user_id

    session["user_name"] = name
    session["user_avatar"] = avatar
    session["user_email"] = email
    flash("Signed in successfully!", "success")
    return redirect(url_for("dashboard.index"))


@auth_bp.route("/auth/logout")
def logout():
    session.clear()
    flash("Signed out successfully.", "info")
    return redirect(url_for("auth.login"))

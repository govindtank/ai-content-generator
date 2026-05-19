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

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
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
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    params = {
        "client_id": Config.GOOGLE_CLIENT_ID,
        "redirect_uri": Config.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    auth_uri = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return render_template("login.html", auth_url=auth_uri)


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

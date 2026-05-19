from flask import Blueprint, render_template, session, redirect, url_for, flash, request

from app.decorators import login_required
from app.db import (
    get_user_by_id,
    set_gemini_api_key,
    get_generations,
)
from app.gemini import GeminiClient

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    user = get_user_by_id(session["user_id"])
    recent = get_generations(user["id"], limit=10)
    return render_template(
        "dashboard.html",
        user=user,
        recent=list(recent),
        remaining=user["image_generations_limit"] - user["image_generations_used"],
    )


@dashboard_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user = get_user_by_id(session["user_id"])

    if request.method == "POST":
        api_key = request.form.get("gemini_api_key", "").strip()
        if not api_key:
            flash("API key is required.", "danger")
            return render_template("settings.html", user=user)

        valid, msg = GeminiClient.validate_api_key(api_key)
        if not valid:
            flash(f"Invalid API key: {msg}", "danger")
            return render_template("settings.html", user=user)

        set_gemini_api_key(user["id"], api_key)
        session["has_api_key"] = True
        flash("API key saved successfully!", "success")
        return redirect(url_for("dashboard.settings"))

    return render_template("settings.html", user=user)


@dashboard_bp.route("/history")
@login_required
def history():
    user = get_user_by_id(session["user_id"])
    all_gens = get_generations(user["id"], limit=50)
    return render_template("history.html", user=user, generations=list(all_gens))

from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify

from app.decorators import login_required
from app.db import (
    get_user_by_id,
    get_generations,
    count_generations,
    get_format_types,
    get_prompt_templates,
    get_provider_api_keys,
    set_provider_api_key,
    get_folders,
    get_presets,
)
from app.providers import router, guess_provider_from_key

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    user = get_user_by_id(session["user_id"])
    recent = get_generations(user["id"], limit=10)
    formats = get_format_types()
    templates = get_prompt_templates(user["id"])
    providers = router.get_available()
    provider_keys = get_provider_api_keys(user["id"])
    key_map = {k["provider"]: bool(k["api_key"]) for k in provider_keys}
    folders = get_folders(user["id"])
    presets_list = get_presets(user["id"])

    # Check if user has at least one provider key
    has_any_key = any(key_map.values()) or bool(user["gemini_api_key"])

    return render_template(
        "dashboard.html",
        user=user,
        recent=list(recent),
        remaining=user["image_generations_limit"] - user["image_generations_used"],
        formats=[dict(f) for f in formats],
        templates=[dict(t) for t in templates],
        providers=providers,
        provider_keys=key_map,
        has_any_key=has_any_key,
        folders=list(folders),
        presets=list(presets_list),
    )


@dashboard_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user = get_user_by_id(session["user_id"])
    if request.method == "POST":
        api_key = (request.form.get("api_key") or "").strip()
        provider = request.form.get("provider", "gemini")
        if api_key:
            set_provider_api_key(user["id"], provider, api_key)
            flash(f"API key saved for {provider}", "success")
        return redirect(url_for("dashboard.settings"))

    providers = router.get_available()
    provider_keys = get_provider_api_keys(user["id"])
    key_map = {}
    for k in provider_keys:
        key_map[k["provider"]] = {
            "set": bool(k["api_key"]),
            "preview": k["api_key"][:8] + "..." if len(k["api_key"]) > 12 else "",
        }

    return render_template(
        "settings.html",
        user=user,
        providers=providers,
        provider_keys=key_map,
    )


@dashboard_bp.route("/history")
@login_required
def history():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()
    per_page = 20
    offset = (page - 1) * per_page
    user = get_user_by_id(session["user_id"])

    generations = get_generations(user["id"], limit=per_page, offset=offset, search_query=search or None)
    total = count_generations(user["id"], search_query=search or None)
    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        "history.html",
        user=user,
        generations=list(generations),
        page=page,
        total_pages=total_pages,
        search=search,
    )


@dashboard_bp.route("/api/search-history")
@login_required
def search_history():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"items": []})
    user = get_user_by_id(session["user_id"])
    results = get_generations(user["id"], limit=20, search_query=q)
    return jsonify({
        "items": [dict(r) for r in results]
    })

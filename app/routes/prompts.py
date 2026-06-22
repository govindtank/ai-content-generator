"""Prompt template management routes."""

from flask import Blueprint, request, jsonify, session

from app.decorators import login_required
from app.db import (
    get_prompt_templates,
    get_prompt_template,
    create_prompt_template,
    update_prompt_template,
    delete_prompt_template,
)

prompts_bp = Blueprint("prompts", __name__, url_prefix="/api/prompts")


@prompts_bp.route("", methods=["GET"])
@login_required
def list_templates():
    category = request.args.get("category")
    templates = get_prompt_templates(session["user_id"], category=category)
    return jsonify({
        "templates": [dict(t) for t in templates]
    })


@prompts_bp.route("", methods=["POST"])
@login_required
def create_template():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    prompt_text = (data.get("prompt_text") or "").strip()
    if not name or not prompt_text:
        return jsonify({"error": "Name and prompt text are required"}), 400

    template_id = create_prompt_template(
        user_id=session["user_id"],
        name=name,
        prompt_text=prompt_text,
        category=data.get("category", "general"),
        format_type=data.get("format_type", "general"),
        description=data.get("description", ""),
    )
    return jsonify({"ok": True, "id": template_id})


@prompts_bp.route("/<int:template_id>", methods=["GET", "PUT", "DELETE"])
@login_required
def manage_template(template_id):
    user_id = session["user_id"]
    template = get_prompt_template(template_id, user_id)
    if not template:
        return jsonify({"error": "Template not found"}), 404

    if request.method == "GET":
        return jsonify(dict(template))

    if request.method == "DELETE":
        delete_prompt_template(template_id, user_id)
        return jsonify({"ok": True})

    # PUT: update
    data = request.get_json(silent=True) or {}
    update_prompt_template(
        template_id, user_id,
        name=data.get("name"),
        prompt_text=data.get("prompt_text"),
        description=data.get("description"),
        category=data.get("category"),
        format_type=data.get("format_type"),
    )
    return jsonify({"ok": True})


@prompts_bp.route("/categories")
@login_required
def list_categories():
    """Get available template categories."""
    return jsonify({
        "categories": [
            {"id": "general", "name": "General"},
            {"id": "marketing", "name": "Marketing"},
            {"id": "social", "name": "Social Media"},
            {"id": "seo", "name": "SEO & Blogging"},
            {"id": "email", "name": "Email"},
            {"id": "creative", "name": "Creative Writing"},
        ]
    })

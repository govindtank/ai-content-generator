"""Integrations — API Tokens & Webhooks management."""

from flask import Blueprint, jsonify, request, session, render_template

from app.decorators import login_required
from app.db import (
    get_api_tokens, create_api_token, revoke_api_token,
    get_webhooks, create_webhook, update_webhook, delete_webhook,
)
from app.db import get_user_by_id

integrations_bp = Blueprint("integrations", __name__, url_prefix="/api/integrations")


# ─── API Tokens ───────────────────────────────────────────────────


@integrations_bp.route("/tokens", methods=["GET"])
@login_required
def list_tokens():
    tokens = get_api_tokens(session["user_id"])
    # Never expose the full token in listing
    safe = []
    for t in tokens:
        d = dict(t)
        d["token_preview"] = d["token"][:12] + "..." + d["token"][-4:]
        d["token"] = "***REDACTED***"
        safe.append(d)
    return jsonify({"tokens": safe})


@integrations_bp.route("/tokens", methods=["POST"])
@login_required
def create_token():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name required"}), 400
    result = create_api_token(
        user_id=session["user_id"],
        name=name,
        scopes=data.get("scopes", "read"),
        expires_at=data.get("expires_at"),
    )
    return jsonify(result), 201


@integrations_bp.route("/tokens/<int:token_id>/revoke", methods=["POST"])
@login_required
def revoke_token(token_id):
    revoke_api_token(token_id, session["user_id"])
    return jsonify({"ok": True})


# ─── Webhooks ────────────────────────────────────────────────────


@integrations_bp.route("/webhooks", methods=["GET"])
@login_required
def list_webhooks():
    hooks = get_webhooks(session["user_id"])
    return jsonify({"webhooks": [dict(h) for h in hooks]})


@integrations_bp.route("/webhooks", methods=["POST"])
@login_required
def add_webhook():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    url = (data.get("url") or "").strip()
    if not name or not url:
        return jsonify({"error": "Name and URL required"}), 400
    hid = create_webhook(
        user_id=session["user_id"],
        name=name,
        url=url,
        events=data.get("events", "content.created"),
        secret=data.get("secret", ""),
    )
    return jsonify({"ok": True, "id": hid}), 201


@integrations_bp.route("/webhooks/<int:webhook_id>", methods=["PUT"])
@login_required
def edit_webhook(webhook_id):
    data = request.get_json(silent=True) or {}
    update_webhook(webhook_id, session["user_id"], **data)
    return jsonify({"ok": True})


@integrations_bp.route("/webhooks/<int:webhook_id>", methods=["DELETE"])
@login_required
def remove_webhook(webhook_id):
    delete_webhook(webhook_id, session["user_id"])
    return jsonify({"ok": True})


# ─── Settings Page with Integrations ──────────────────────────────


@integrations_bp.route("/page")
@login_required
def integrations_page():
    user = get_user_by_id(session["user_id"])
    return render_template("integrations.html", user=user)

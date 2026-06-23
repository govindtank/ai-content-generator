"""Campaigns — Thematic content series management."""

from flask import Blueprint, jsonify, request, session

from app.decorators import login_required
from app.db import (
    get_campaigns, get_campaign, create_campaign,
    update_campaign, delete_campaign,
    get_campaign_content, add_campaign_content, remove_campaign_content,
)

campaigns_bp = Blueprint("campaigns", __name__, url_prefix="/api/campaigns")


@campaigns_bp.route("", methods=["GET"])
@login_required
def list_campaigns():
    campaigns = get_campaigns(session["user_id"])
    return jsonify({"campaigns": [dict(c) for c in campaigns]})


@campaigns_bp.route("/<int:campaign_id>", methods=["GET"])
@login_required
def get_one(campaign_id):
    camp = get_campaign(campaign_id, session["user_id"])
    if not camp:
        return jsonify({"error": "Not found"}), 404
    content = get_campaign_content(campaign_id)
    result = dict(camp)
    result["content"] = [dict(c) for c in content]
    return jsonify(result)


@campaigns_bp.route("", methods=["POST"])
@login_required
def add_campaign():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name required"}), 400
    cid = create_campaign(
        user_id=session["user_id"],
        name=name,
        description=data.get("description", ""),
        goal=data.get("goal", ""),
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
        status=data.get("status", "planning"),
    )
    return jsonify({"ok": True, "id": cid}), 201


@campaigns_bp.route("/<int:campaign_id>", methods=["PUT"])
@login_required
def edit_campaign(campaign_id):
    data = request.get_json(silent=True) or {}
    update_campaign(campaign_id, session["user_id"], **data)
    return jsonify({"ok": True})


@campaigns_bp.route("/<int:campaign_id>", methods=["DELETE"])
@login_required
def remove_campaign(campaign_id):
    delete_campaign(campaign_id, session["user_id"])
    return jsonify({"ok": True})


@campaigns_bp.route("/<int:campaign_id>/content", methods=["POST"])
@login_required
def add_content(campaign_id):
    data = request.get_json(silent=True) or {}
    gen_id = data.get("generation_id")
    if not gen_id:
        return jsonify({"error": "generation_id required"}), 400
    add_campaign_content(
        campaign_id, gen_id,
        slot_order=data.get("slot_order", 0),
        notes=data.get("notes", ""),
    )
    return jsonify({"ok": True}), 201


@campaigns_bp.route("/<int:campaign_id>/content/<int:gen_id>", methods=["DELETE"])
@login_required
def remove_content(campaign_id, gen_id):
    remove_campaign_content(campaign_id, gen_id)
    return jsonify({"ok": True})

"""Comments — Content collaboration & feedback."""

from flask import Blueprint, jsonify, request, session

from app.decorators import login_required
from app.db import get_content_comments, add_content_comment

comments_bp = Blueprint("comments", __name__, url_prefix="/api/comments")


@comments_bp.route("/<int:generation_id>", methods=["GET"])
@login_required
def list_comments(generation_id):
    comments = get_content_comments(generation_id)
    return jsonify({"comments": [dict(c) for c in comments]})


@comments_bp.route("/<int:generation_id>", methods=["POST"])
@login_required
def add_comment(generation_id):
    data = request.get_json(silent=True) or {}
    text = (data.get("comment") or "").strip()
    if not text:
        return jsonify({"error": "Comment text required"}), 400
    cid = add_content_comment(generation_id, session["user_id"], text)
    return jsonify({"ok": True, "id": cid}), 201

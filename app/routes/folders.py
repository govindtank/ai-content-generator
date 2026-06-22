"""Folders — organize generated content into folders."""

from flask import Blueprint, jsonify, request, session

from app.decorators import login_required
from app.db import get_folders, create_folder, update_folder, delete_folder, get_db

folders_bp = Blueprint("folders", __name__, url_prefix="/api/folders")


@folders_bp.route("", methods=["GET"])
@login_required
def list_folders():
    folders = get_folders(session["user_id"])
    return jsonify({
        "folders": [dict(f) for f in folders]
    })


@folders_bp.route("", methods=["POST"])
@login_required
def new_folder():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Folder name required"}), 400
    folder_id = create_folder(session["user_id"], name, data.get("parent_id"))
    return jsonify({"ok": True, "id": folder_id}), 201


@folders_bp.route("/<int:folder_id>", methods=["PUT"])
@login_required
def rename_folder(folder_id):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Folder name required"}), 400
    update_folder(folder_id, session["user_id"], name)
    return jsonify({"ok": True})


@folders_bp.route("/<int:folder_id>", methods=["DELETE"])
@login_required
def remove_folder(folder_id):
    delete_folder(folder_id, session["user_id"])
    return jsonify({"ok": True})


@folders_bp.route("/<int:folder_id>/content", methods=["GET"])
@login_required
def folder_content(folder_id):
    """Get generations in a folder."""
    db = get_db()
    items = db.execute(
        """SELECT * FROM generations WHERE user_id = ? AND folder_id = ?
           ORDER BY created_at DESC LIMIT 50""",
        (session["user_id"], folder_id),
    ).fetchall()
    return jsonify({
        "items": [dict(i) for i in items]
    })


@folders_bp.route("/move/<int:gen_id>", methods=["POST"])
@login_required
def move_to_folder(gen_id):
    """Move a generation to a folder (or root)."""
    data = request.get_json(silent=True) or {}
    folder_id = data.get("folder_id")  # None = move to root
    db = get_db()
    db.execute(
        "UPDATE generations SET folder_id = ? WHERE id = ? AND user_id = ?",
        (folder_id, gen_id, session["user_id"]),
    )
    db.commit()
    return jsonify({"ok": True})

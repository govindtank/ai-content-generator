from flask import Blueprint, request, jsonify, session

from app.decorators import login_required, api_key_required
from app.db import get_user_by_id, record_generation
from app.gemini import GeminiClient

text_bp = Blueprint("text", __name__)


@text_bp.route("/api/generate-text", methods=["POST"])
@login_required
@api_key_required
def generate_text():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    model = data.get("model") or None
    user = get_user_by_id(session["user_id"])

    try:
        client = GeminiClient(user["gemini_api_key"])
        result = client.generate_text(prompt, model=model)
        record_generation(user["id"], "text", prompt, model or "default")
        return jsonify({"text": result, "ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

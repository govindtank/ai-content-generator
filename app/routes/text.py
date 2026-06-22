from flask import Blueprint, request, jsonify, session

from app.decorators import login_required, api_key_required
from app.db import get_user_by_id, get_provider_api_key, record_generation

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

    user = get_user_by_id(session["user_id"])
    user_id = user["id"]

    # Determine provider
    provider_slug = data.get("provider") or "gemini"
    provider_key_entry = get_provider_api_key(user_id, provider_slug)
    api_key = provider_key_entry["api_key"] if provider_key_entry else user.get("gemini_api_key", "")

    if not api_key:
        # Fallback to Gemini API key from user profile
        api_key = user.get("gemini_api_key", "")
        if not api_key:
            return jsonify({"error": f"No API key found for {provider_slug}. Set it in Settings."}), 400
        provider_slug = "gemini"

    model = data.get("model") or None
    format_type = data.get("format_type") or "general"
    system_prompt = data.get("system_prompt") or ""

    # Add system prompt / format context to the user prompt
    full_prompt = prompt
    if system_prompt:
        full_prompt = f"{system_prompt}\n\n---\n\n{prompt}"

    try:
        from app.providers import router as provider_router
        client = provider_router.get_provider(provider_slug, api_key)
        result = client.generate_text(full_prompt, model=model)

        record_generation(
            user_id, "text", prompt, content=result,
            model=model or provider_slug,
            provider=provider_slug, format_type=format_type,
        )
        return jsonify({"text": result, "ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

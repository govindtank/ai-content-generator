import base64

from flask import Blueprint, request, jsonify, session

from app.config import Config
from app.decorators import login_required, api_key_required
from app.db import (
    get_user_by_id,
    get_provider_api_key,
    record_generation,
    get_format_type,
)

image_bp = Blueprint("image", __name__)


@image_bp.route("/api/generate-image", methods=["POST"])
@login_required
@api_key_required
def generate_image():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    user = get_user_by_id(session["user_id"])
    user_id = user["id"]

    remaining = user["image_generations_limit"] - user["image_generations_used"]
    if remaining <= 0 and not user["is_subscribed"]:
        return jsonify({
            "error": "You've used all your free generations. Subscribe to continue generating images.",
            "quota_exhausted": True,
            "remaining": 0,
        }), 403

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
    aspect_ratio = data.get("aspect_ratio") or "1:1"
    format_type = data.get("format_type") or "general"

    try:
        from app.providers import router as provider_router
        client = provider_router.get_provider(provider_slug, api_key)
        result = client.generate_image(prompt, model=model, aspect_ratio=aspect_ratio)
        if result is None:
            return jsonify({"error": f"{provider_slug} does not support image generation or no image returned."}), 500

        img_bytes, mime_type = result
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64}"

        record_generation(
            user_id, "image", prompt, content=data_url,
            model=model or Config.GEMINI_IMAGE_MODEL,
            provider=provider_slug, format_type=format_type,
        )

        remaining_new = user["image_generations_limit"] - user["image_generations_used"] - 1
        return jsonify({
            "image": data_url,
            "mime_type": mime_type,
            "ok": True,
            "remaining": max(0, remaining_new),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@image_bp.route("/api/quota")
@login_required
def quota():
    user = get_user_by_id(session["user_id"])
    remaining = user["image_generations_limit"] - user["image_generations_used"]
    return jsonify({
        "total": user["image_generations_limit"],
        "used": user["image_generations_used"],
        "remaining": max(0, remaining),
        "is_subscribed": bool(user["is_subscribed"]),
    })

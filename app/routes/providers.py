"""Provider management API routes."""

from flask import Blueprint, request, jsonify, session

from app.decorators import login_required
from app.db import (
    get_provider_api_keys,
    get_provider_api_key,
    set_provider_api_key,
    delete_provider_api_key,
)
from app.providers import router, guess_provider_from_key

provider_bp = Blueprint("providers", __name__, url_prefix="/api/providers")


@provider_bp.route("")
@login_required
def list_providers():
    """List all registered providers with their status for this user."""
    available = router.get_available()
    user_keys = get_provider_api_keys(session["user_id"])
    key_map = {k["provider"]: k["api_key"] for k in user_keys}

    result = []
    for p in available:
        has_key = bool(key_map.get(p["slug"]))
        result.append({
            **p,
            "has_key": has_key,
            "key_preview": key_map.get(p["slug"], "")[:8] + "..." if has_key else None,
        })
    return jsonify({"providers": result})


@provider_bp.route("/<provider>/key", methods=["GET", "POST", "DELETE"])
@login_required
def manage_key(provider):
    user_id = session["user_id"]

    if request.method == "GET":
        key = get_provider_api_key(user_id, provider)
        return jsonify({
            "has_key": key is not None and bool(key["api_key"]),
            "provider": provider,
        })

    if request.method == "DELETE":
        delete_provider_api_key(user_id, provider)
        return jsonify({"ok": True})

    # POST: save and validate key
    data = request.get_json(silent=True) or {}
    api_key = (data.get("api_key") or "").strip()
    if not api_key:
        return jsonify({"error": "API key is required"}), 400

    # Validate the key
    try:
        prov = router.get_provider(provider, api_key)
        valid, msg = prov.validate_key(api_key)
        if not valid:
            return jsonify({"error": f"Invalid API key: {msg}"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Could not validate key: {str(e)}"}), 400

    set_provider_api_key(user_id, provider, api_key)
    return jsonify({"ok": True, "provider": provider})


@provider_bp.route("/detect", methods=["POST"])
@login_required
def detect_provider():
    """Guess the provider from an API key prefix."""
    data = request.get_json(silent=True) or {}
    api_key = (data.get("api_key") or "").strip()
    if not api_key:
        return jsonify({"provider": None})
    guessed = guess_provider_from_key(api_key)
    return jsonify({"provider": guessed})


@provider_bp.route("/defaults")
@login_required
def get_default_models():
    from app.config import Config
    return jsonify({
        "gemini": {"text": Config.GEMINI_TEXT_MODEL, "image": Config.GEMINI_IMAGE_MODEL},
        "openai": {"text": Config.OPENAI_TEXT_MODEL, "image": Config.OPENAI_IMAGE_MODEL},
        "anthropic": {"text": Config.ANTHROPIC_TEXT_MODEL, "image": None},
    })

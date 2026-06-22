"""Content Workbench — Editor, Refinement, Repurpose & Multi-Model Compare."""

import json
from flask import Blueprint, jsonify, request, session, render_template

from app.decorators import login_required
from app.db import get_user_by_id, get_db, record_generation
from app.providers import router

workbench_bp = Blueprint("workbench", __name__, url_prefix="/api/workbench")


# ─── CONTENT EDITOR ──────────────────────────────────────────────


@workbench_bp.route("/generation/<int:gen_id>", methods=["GET"])
@login_required
def get_generation(gen_id):
    db = get_db()
    gen = db.execute(
        "SELECT * FROM generations WHERE id = ? AND user_id = ?",
        (gen_id, session["user_id"]),
    ).fetchone()
    if not gen:
        return jsonify({"error": "Not found"}), 404
    return jsonify(dict(gen))


@workbench_bp.route("/generation/<int:gen_id>", methods=["PUT"])
@login_required
def update_generation(gen_id):
    """Save content edits."""
    data = request.get_json(silent=True) or {}
    content = data.get("content", "").strip()
    if not content:
        return jsonify({"error": "Content required"}), 400
    db = get_db()
    db.execute(
        "UPDATE generations SET content = ? WHERE id = ? AND user_id = ?",
        (content, gen_id, session["user_id"]),
    )
    db.commit()
    return jsonify({"ok": True})


# ─── REFINEMENT ──────────────────────────────────────────────────


@workbench_bp.route("/refine", methods=["POST"])
@login_required
def refine_content():
    """AI-powered refinement: rephrase, expand, shorten, etc."""
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    instruction = (data.get("instruction") or "improve").strip()
    provider_name = data.get("provider", "gemini")
    model = data.get("model", "")

    if not content:
        return jsonify({"error": "Content is required"}), 400

    instructions = {
        "improve": "Improve the following content: make it clearer, more engaging, and better structured. Return only the improved content.",
        "simplify": "Simplify the following content: make it easier to understand, using simpler words and shorter sentences. Return only the simplified content.",
        "expand": "Expand on the following content: add more details, examples, and depth while maintaining the original style. Return only the expanded content.",
        "shorten": "Shorten the following content to its essential key points. Keep it concise and impactful. Return only the shortened content.",
        "professional": "Rewrite the following content in a professional, formal tone. Return only the rewritten content.",
        "casual": "Rewrite the following content in a casual, conversational tone. Return only the rewritten content.",
    }

    system_prompt = instructions.get(
        instruction,
        f"{instruction}\n\nReturn only the modified content.",
    )

    try:
        provider_cls = router.get_provider(provider_name)
        if not provider_cls:
            return jsonify({"error": f"Provider '{provider_name}' not available"}), 400

        provider = provider_cls(session["user_id"])
        full_prompt = f"{system_prompt}\n\n---\n\n{content}"
        result = provider.generate_text(full_prompt)

        if result:
            return jsonify({"ok": True, "content": result})
        return jsonify({"error": "Provider returned empty result"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── CONTENT REPURPOSING ────────────────────────────────────────


@workbench_bp.route("/repurpose", methods=["POST"])
@login_required
def repurpose_content():
    """Convert content from one format to another."""
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    target_format = (data.get("format") or "blog-post").strip()
    provider_name = data.get("provider", "gemini")

    if not content:
        return jsonify({"error": "Content is required"}), 400

    format_prompts = {
        "blog-post": "Rewrite the following content as a well-structured blog post with headings, introduction, body, and conclusion. Return only the final blog post.",
        "twitter-thread": "Convert the following content into an engaging Twitter/X thread with numbered tweets. Each tweet under 280 characters. Return only the thread.",
        "linkedin-post": "Convert the following content into a professional LinkedIn post with a hook, personal insight, and call to action. Return only the post.",
        "email-newsletter": "Convert the following content into an email newsletter with a subject line, greeting, main body, and sign-off. Return only the newsletter.",
        "ad-copy": "Convert the following content into concise, persuasive ad copy with headline, body, and CTA. Return only the ad copy.",
        "social-post": "Convert the following content into a short, engaging social media post. Return only the post.",
        "video-script": "Convert the following content into a video script with hook, key points, and CTA. Include timing cues. Return only the script.",
    }

    system_prompt = format_prompts.get(
        target_format,
        f"Rewrite the following content as {target_format}. Return only the rewritten content.",
    )

    try:
        provider_cls = router.get_provider(provider_name)
        if not provider_cls:
            return jsonify({"error": f"Provider '{provider_name}' not available"}), 400

        provider = provider_cls(session["user_id"])
        full_prompt = f"{system_prompt}\n\n---\n\n{content}"
        result = provider.generate_text(full_prompt)

        if result:
            return jsonify({"ok": True, "content": result})
        return jsonify({"error": "Provider returned empty result"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── MULTI-MODEL COMPARE ────────────────────────────────────────


@workbench_bp.route("/compare", methods=["POST"])
@login_required
def compare_models():
    """Generate the same prompt across multiple models/providers."""
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    models = data.get("models", [])

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400
    if not models or len(models) < 2:
        return jsonify({"error": "Select at least 2 models to compare"}), 400

    results = []
    errors = []

    for m in models:
        provider_name = m.get("provider", "gemini")
        model_name = m.get("model", "")
        try:
            provider_cls = router.get_provider(provider_name)
            if not provider_cls:
                errors.append({"model": model_name, "error": "Provider not available"})
                continue

            provider = provider_cls(session["user_id"])
            result = provider.generate_text(prompt)

            if result:
                results.append({
                    "provider": provider_name,
                    "model": model_name,
                    "content": result,
                })
                # Record each comparison generation
                record_generation(
                    user_id=session["user_id"],
                    gen_type="text",
                    prompt=prompt,
                    model=model_name,
                    provider=provider_name,
                    format_type="general",
                    content=result,
                )
            else:
                errors.append({"model": model_name, "error": "Empty response"})
        except Exception as e:
            errors.append({"model": model_name, "error": str(e)})

    return jsonify({
        "results": results,
        "errors": errors,
        "total": len(results),
    })


# ─── WORKBENCH PAGE ──────────────────────────────────────────────


@workbench_bp.route("/workbench")
@login_required
def workbench_page():
    user = get_user_by_id(session["user_id"])
    return render_template("workbench.html", user=user)

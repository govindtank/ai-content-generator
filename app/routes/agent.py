"""Autonomous Agent — Multi-step content generation, briefs & scheduling."""

import json
from datetime import datetime
from flask import Blueprint, jsonify, request, session

from app.decorators import login_required
from app.db import (
    get_user_by_id, record_generation, get_db,
    create_agent_task, get_agent_tasks, update_agent_task,
    create_content_brief, get_content_briefs, get_content_brief,
    create_scheduled_publish, get_scheduled_publishes, update_scheduled_publish,
)
from app.providers import router

agent_bp = Blueprint("agent", __name__, url_prefix="/api/agent")


# ─── CONTENT BRIEF GENERATION ────────────────────────────────────


@agent_bp.route("/brief", methods=["POST"])
@login_required
def generate_brief():
    """AI-powered content brief generation."""
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    title = (data.get("title") or topic).strip()
    goal = (data.get("goal") or "").strip()
    provider_name = data.get("provider", "gemini")

    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    try:
        provider_cls = router.get_provider(provider_name)
        if not provider_cls:
            return jsonify({"error": f"Provider '{provider_name}' not available"}), 400

        provider = provider_cls(session["user_id"])
        brief_prompt = (
            f"Create a detailed content brief for the topic: '{topic}'\n\n"
            f"Goal: {goal if goal else 'Inform and engage'}\n\n"
            f"Return EXACTLY in this JSON format (no markdown, no code blocks):\n"
            f"{{\n"
            f"  \"outline\": \"comma-separated bullet outline\",\n"
            f"  \"keywords\": [\"keyword1\", \"keyword2\", \"keyword3\", \"keyword4\", \"keyword5\"],\n"
            f"  \"target_audience\": \"description of target audience\",\n"
            f"  \"angle\": \"unique angle or perspective for this content\",\n"
            f"  \"suggested_title\": \"SEO-optimized title\"\n"
            f"}}"
        )
        result = provider.generate_text(brief_prompt)

        brief_data = {}
        if result:
            # Try to parse JSON from response
            import re
            json_match = re.search(r"\{.*\}", result, re.DOTALL)
            if json_match:
                try:
                    brief_data = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

        outline = brief_data.get("outline", "")
        keywords = brief_data.get("keywords", [])
        audience = brief_data.get("target_audience", "")
        angle = brief_data.get("angle", "")
        suggested_title = brief_data.get("suggested_title", title)

        # Save brief
        brief_id = create_content_brief(
            user_id=session["user_id"],
            title=suggested_title,
            topic=topic,
            outline=outline,
            keywords=keywords,
            target_audience=audience,
            angle=angle,
            goal=goal,
        )

        return jsonify({
            "ok": True,
            "brief_id": brief_id,
            "title": suggested_title,
            "outline": outline,
            "keywords": keywords,
            "target_audience": audience,
            "angle": angle,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── AUTO-REPURPOSE (Format cascade) ────────────────────────────


REPURPOSE_CHAIN = {
    "blog-post": ["twitter-thread", "linkedin-post", "email-newsletter", "social-post"],
    "twitter-thread": ["social-post", "linkedin-post"],
    "linkedin-post": ["blog-post", "social-post"],
    "email-newsletter": ["blog-post", "social-post"],
    "video-script": ["blog-post", "social-post"],
    "social-post": ["email-newsletter"],
}


@agent_bp.route("/auto-repurpose", methods=["POST"])
@login_required
def auto_repurpose():
    """Automatically repurpose content across multiple formats."""
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    source_format = (data.get("source_format") or "blog-post").strip()
    target_formats = data.get("formats") or REPURPOSE_CHAIN.get(source_format, ["social-post"])
    provider_name = data.get("provider", "gemini")

    if not content:
        return jsonify({"error": "Content is required"}), 400

    prompt_map = {
        "blog-post": "Rewrite as a full blog post with headings, intro, body, conclusion.",
        "twitter-thread": "Convert into an engaging Twitter/X thread, each tweet under 280 chars. Number each tweet.",
        "linkedin-post": "Rewrite as a professional LinkedIn post with a hook, insight, and CTA.",
        "email-newsletter": "Rewrite as an email newsletter with subject line, greeting, body, sign-off.",
        "social-post": "Rewrite as a short engaging social media post (under 280 chars).",
        "ad-copy": "Rewrite as persuasive ad copy with headline, body, CTA.",
        "video-script": "Rewrite as video script with hook, key points, and CTA with timing.",
    }

    try:
        provider_cls = router.get_provider(provider_name)
        if not provider_cls:
            return jsonify({"error": f"Provider '{provider_name}' not available"}), 400

        provider = provider_cls(session["user_id"])
        results = []

        for fmt in target_formats:
            instruction = prompt_map.get(fmt, f"Rewrite as {fmt}.")
            full_prompt = f"{instruction}\n\nReturn only the rewritten content.\n\n---\n\n{content}"
            result = provider.generate_text(full_prompt)
            results.append({
                "format": fmt,
                "content": result or "(empty)",
                "success": bool(result),
            })

        return jsonify({"results": results, "total": len(results)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── AGENT: GENERATE FROM BRIEF ──────────────────────────────────


@agent_bp.route("/generate-from-brief", methods=["POST"])
@login_required
def generate_from_brief():
    """Generate full content from a content brief."""
    data = request.get_json(silent=True) or {}
    brief_id = data.get("brief_id")
    provider_name = data.get("provider", "gemini")
    model = data.get("model", "")

    if not brief_id:
        return jsonify({"error": "brief_id required"}), 400

    brief = get_content_brief(brief_id, session["user_id"])
    if not brief:
        return jsonify({"error": "Brief not found"}), 404

    import json as json_mod
    keywords = ", ".join(json_mod.loads(brief["keywords"]) if isinstance(brief["keywords"], str) else brief["keywords"])

    try:
        provider_cls = router.get_provider(provider_name)
        if not provider_cls:
            return jsonify({"error": "Provider not available"}), 400

        provider = provider_cls(session["user_id"])

        gen_prompt = (
            f"Write comprehensive content based on this brief:\n\n"
            f"Title: {brief['title']}\n"
            f"Topic: {brief['topic']}\n"
            f"Target Audience: {brief['target_audience']}\n"
            f"Angle: {brief['angle']}\n"
            f"Goal: {brief['goal']}\n"
            f"Keywords: {keywords}\n"
            f"Outline: {brief['outline']}\n\n"
            f"Write well-structured, engaging content that covers all points above."
        )

        result = provider.generate_text(gen_prompt)

        if result:
            gen_id = record_generation(
                user_id=session["user_id"],
                gen_type="text",
                prompt=f"Brief: {brief['title']}",
                model=model or provider_name,
                provider=provider_name,
                format_type="general",
                content=result,
            )
            return jsonify({
                "ok": True,
                "content": result,
                "generation_id": gen_id,
            })
        return jsonify({"error": "Generation returned empty"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── AGENT TASK: FULL AUTONOMOUS WORKFLOW ───────────────────────


@agent_bp.route("/task", methods=["POST"])
@login_required
def create_task():
    """Create a multi-step agent task: brief → generate → repurpose → schedule."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    topic = (data.get("topic") or "").strip()
    goal = (data.get("goal") or "").strip()
    format_type = data.get("format_type", "blog-post")
    provider_name = data.get("provider", "gemini")

    if not name or not topic:
        return jsonify({"error": "Name and topic required"}), 400

    task_id = create_agent_task(
        user_id=session["user_id"],
        name=name,
        topic=topic,
        goal=goal,
        format_type=format_type,
        provider=provider_name,
    )

    # Run the autonomous workflow asynchronously (in this request)
    try:
        provider_cls = router.get_provider(provider_name)
        if not provider_cls:
            update_agent_task(task_id, session["user_id"], status="failed", progress="Provider not available")
            return jsonify({"error": "Provider not available"}), 400

        provider = provider_cls(session["user_id"])
        update_agent_task(task_id, session["user_id"], status="running", progress="Generating content brief...")

        # Step 1: Generate brief
        brief_prompt = (
            f"Create a content brief for: '{topic}'. "
            f"Goal: {goal if goal else 'Inform'}. "
            f"Return JSON: {{\"outline\":\"...\",\"keywords\":[...],\"angle\":\"...\",\"audience\":\"...\"}}"
        )
        brief_result = provider.generate_text(brief_prompt)
        update_agent_task(task_id, session["user_id"], progress="Brief ready. Generating content...")

        # Step 2: Generate content
        content_prompt = (
            f"Write a {format_type} about: {topic}. "
            f"{'Goal: ' + goal if goal else ''}"
            f"\n\nWrite a complete, well-structured piece."
        )
        content = provider.generate_text(content_prompt)

        if not content:
            update_agent_task(task_id, session["user_id"], status="failed", progress="Generation returned empty")
            return jsonify({"error": "Generation failed"}), 500

        # Save the generation
        gen_id = record_generation(
            user_id=session["user_id"],
            gen_type="text",
            prompt=f"Agent: {name} — {topic}",
            model=provider_name,
            provider=provider_name,
            format_type=format_type,
            content=content,
        )
        update_agent_task(task_id, session["user_id"],
                          status="completed",
                          progress="Content generated successfully!",
                          result_id=gen_id,
                          completed_at=datetime.utcnow().isoformat())

        return jsonify({
            "ok": True,
            "task_id": task_id,
            "generation_id": gen_id,
            "content": content,
            "message": f"Agent completed: {name}",
        })
    except Exception as e:
        update_agent_task(task_id, session["user_id"], status="failed", progress=str(e))
        return jsonify({"error": str(e)}), 500


@agent_bp.route("/tasks", methods=["GET"])
@login_required
def list_tasks():
    tasks = get_agent_tasks(session["user_id"])
    return jsonify({"tasks": [dict(t) for t in tasks]})


@agent_bp.route("/briefs", methods=["GET"])
@login_required
def list_briefs():
    briefs = get_content_briefs(session["user_id"])
    result = []
    for b in briefs:
        d = dict(b)
        import json as j
        if isinstance(d.get("keywords"), str):
            d["keywords"] = j.loads(d["keywords"])
        if isinstance(d.get("sources"), str):
            d["sources"] = j.loads(d["sources"])
        result.append(d)
    return jsonify({"briefs": result})


# ─── SCHEDULE ─────────────────────────────────────────────────────


@agent_bp.route("/schedule", methods=["POST"])
@login_required
def create_schedule():
    """Schedule content for future publication."""
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    scheduled_date = (data.get("scheduled_date") or "").strip()
    platform = (data.get("platform") or "blog").strip()
    generation_id = data.get("generation_id")

    if not title or not scheduled_date:
        return jsonify({"error": "Title and scheduled_date required"}), 400

    try:
        pub_id = create_scheduled_publish(
            user_id=session["user_id"],
            title=title,
            scheduled_date=scheduled_date,
            generation_id=generation_id,
            platform=platform,
        )
        return jsonify({"ok": True, "publish_id": pub_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@agent_bp.route("/schedule", methods=["GET"])
@login_required
def list_schedule():
    pubs = get_scheduled_publishes(session["user_id"])
    return jsonify({"schedules": [dict(p) for p in pubs]})


# ─── AGENT PAGE ──────────────────────────────────────────────────


@agent_bp.route("/page")
@login_required
def agent_page():
    from flask import render_template
    user = get_user_by_id(session["user_id"])
    return render_template("agent.html", user=user)

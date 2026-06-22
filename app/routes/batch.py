"""Batch content generation routes."""

import json
from datetime import datetime

from flask import Blueprint, jsonify, request, session

from app.decorators import login_required
from app.db import (
    create_batch_job,
    get_batch_jobs,
    get_batch_job,
    update_batch_job_status,
    record_generation,
    get_user_by_id,
)
from app.providers import router

batch_bp = Blueprint("batch", __name__, url_prefix="/api/batch")


@batch_bp.route("", methods=["GET"])
@login_required
def list_batch_jobs():
    jobs = get_batch_jobs(session["user_id"])
    return jsonify({
        "jobs": [dict(j) for j in jobs]
    })


@batch_bp.route("/<int:job_id>", methods=["GET"])
@login_required
def get_job(job_id):
    job = get_batch_job(job_id, session["user_id"])
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(dict(job))


@batch_bp.route("/create", methods=["POST"])
@login_required
def create_job():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    prompt_template = (data.get("prompt_template") or "").strip()
    variables = data.get("variables", {})
    provider = data.get("provider", "gemini")
    model = data.get("model", "")
    format_type = data.get("format_type", "general")

    if not name:
        return jsonify({"error": "Job name is required"}), 400
    if not prompt_template:
        return jsonify({"error": "Prompt template is required"}), 400
    if not variables or not isinstance(variables, dict):
        return jsonify({"error": "Variables dict is required"}), 400

    # Calculate total iterations
    var_names = list(variables.keys())
    if not var_names:
        return jsonify({"error": "At least one variable required"}), 400
    
    total = 1
    for vals in variables.values():
        if isinstance(vals, list):
            total = max(total, len(vals))
    
    job_id = create_batch_job(
        user_id=session["user_id"],
        name=name,
        prompt_template=prompt_template,
        variables=variables,
        provider=provider,
        model=model,
        format_type=format_type,
    )
    
    update_batch_job_status(job_id, session["user_id"], "running", 0, total)
    
    return jsonify({"ok": True, "id": job_id, "total": total}), 201


@batch_bp.route("/<int:job_id>/execute", methods=["POST"])
@login_required
def execute_job(job_id):
    """Execute a batch job (run all generations)."""
    user_id = session["user_id"]
    job = get_batch_job(job_id, user_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    user = get_user_by_id(user_id)
    variables = json.loads(job["variables"])
    prompt_template = job["prompt_template"]
    provider_name = job["provider"]
    model = job["model"]
    format_type = job["format_type"]

    # Collect all value combinations
    var_items = list(variables.items())
    keys = [item[0] for item in var_items]
    values_lists = [item[1] if isinstance(item[1], list) else [item[1]] for item in var_items]

    from itertools import product
    combinations = list(product(*values_lists))
    
    if not combinations:
        combinations = [tuple()]  # Empty template

    total = len(combinations)
    completed = 0
    results = []
    errors = []

    update_batch_job_status(job_id, user_id, "running", 0, total)

    for combo in combinations:
        # Fill template with variable values
        filled = prompt_template
        ctx = {}
        for i, key in enumerate(keys):
            value = combo[i] if i < len(combo) else ""
            ctx[key] = value
            filled = filled.replace("{{ " + key + " }}", str(value))
            filled = filled.replace("{{" + key + "}}", str(value))

        try:
            provider_cls = router.get_provider(provider_name)
            if not provider_cls:
                raise ValueError(f"Provider '{provider_name}' not available")

            provider_instance = provider_cls(user_id)
            result = provider_instance.generate_text(filled)

            if result:
                record_generation(
                    user_id=user_id,
                    gen_type="text",
                    prompt=filled,
                    model=model or f"{provider_name}-default",
                    provider=provider_name,
                    format_type=format_type,
                    content=result,
                )
                results.append({"vars": ctx, "content": result, "status": "ok"})
            else:
                errors.append({"vars": ctx, "error": "Empty response"})
            
            completed += 1
            if completed % 3 == 0 or completed == total:
                update_batch_job_status(job_id, user_id, "running", completed, total)

        except Exception as e:
            errors.append({"vars": ctx, "error": str(e)})
            completed += 1

    status = "completed" if not errors else "completed_with_errors"
    update_batch_job_status(job_id, user_id, status, completed, total)

    return jsonify({
        "ok": True,
        "status": status,
        "completed": completed,
        "total": total,
        "results": results,
        "errors": errors,
    })

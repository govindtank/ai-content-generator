"""Export routes — download generated content in various formats."""

import json
from flask import Blueprint, jsonify, request, session, send_file

from app.decorators import login_required
from app.db import get_db, record_export, get_exports

export_bp = Blueprint("export", __name__, url_prefix="/api/exports")


@export_bp.route("", methods=["GET"])
@login_required
def list_exports():
    exports = get_exports(session["user_id"])
    return jsonify({
        "exports": [dict(e) for e in exports]
    })


@export_bp.route("/<int:gen_id>", methods=["POST"])
@login_required
def export_generation(gen_id):
    """Export a generation to the requested format."""
    data = request.get_json(silent=True) or {}
    export_type = data.get("type", "markdown")

    db = get_db()
    gen = db.execute(
        "SELECT * FROM generations WHERE id = ? AND user_id = ?",
        (gen_id, session["user_id"]),
    ).fetchone()

    if not gen:
        return jsonify({"error": "Generation not found"}), 404

    content = gen["content"]
    prompt = gen["prompt"]
    timestamp = gen["created_at"]

    if export_type == "markdown":
        output = _to_markdown(content, prompt, timestamp)
        mimetype = "text/markdown"
        ext = "md"
    elif export_type == "html":
        output = _to_html(content, prompt, timestamp)
        mimetype = "text/html"
        ext = "html"
    elif export_type == "text":
        output = content
        mimetype = "text/plain"
        ext = "txt"
    else:
        return jsonify({"error": f"Unsupported export type: {export_type}"}), 400

    record_export(session["user_id"], gen_id, export_type, output)

    # Save to temp file and return
    import tempfile, os
    safe_name = prompt[:40].replace(" ", "_").replace("/", "_").strip("_") or "content"
    fd, path = tempfile.mkstemp(suffix=f".{ext}", prefix=f"{safe_name}_")
    with os.fdopen(fd, "w") as f:
        f.write(output)

    return send_file(path, mimetype=mimetype, as_attachment=True,
                     download_name=f"{safe_name}.{ext}")


@export_bp.route("/batch/<int:job_id>", methods=["POST"])
@login_required
def export_batch(job_id):
    """Export all results from a batch job as a combined file."""
    data = request.get_json(silent=True) or {}
    export_type = data.get("type", "markdown")

    db = get_db()
    job = db.execute(
        "SELECT * FROM batch_jobs WHERE id = ? AND user_id = ?",
        (job_id, session["user_id"]),
    ).fetchone()

    if not job:
        return jsonify({"error": "Batch job not found"}), 404

    generations = db.execute(
        """SELECT * FROM generations WHERE id IN (
            SELECT generation_id FROM batch_results WHERE batch_job_id = ?
        ) AND user_id = ? ORDER BY created_at ASC""",
        (job_id, session["user_id"]),
    ).fetchall()

    if not generations:
        # Fall back to searching by prompt template pattern
        generations = db.execute(
            """SELECT * FROM generations WHERE user_id = ? AND prompt LIKE ?
               ORDER BY created_at ASC LIMIT 20""",
            (session["user_id"], f"{job['prompt_template'][:50]}%"),
        ).fetchall()

    lines = []
    for g in generations:
        title = g["prompt"][:80]
        lines.append(f"## {title}\n")
        lines.append(f"*Model: {g['model']} | Provider: {g['provider']} | Type: {g['type']}*\n")
        lines.append(g["content"] or "")
        lines.append("\n---\n")

    output = "\n".join(lines)
    
    if export_type == "markdown":
        mimetype, ext = "text/markdown", "md"
    elif export_type == "html":
        rows = "\n".join(
            f"<h2>{g['prompt'][:80]}</h2><pre>{g['content']}</pre><hr>"
            for g in generations
        )
        output = f"<html><body>{rows}</body></html>"
        mimetype, ext = "text/html", "html"
    else:
        mimetype, ext = "text/plain", "txt"

    import tempfile, os
    safe_name = job["name"][:40].replace(" ", "_").replace("/", "_").strip("_") or "batch"
    fd, path = tempfile.mkstemp(suffix=f".{ext}", prefix=f"{safe_name}_")
    with os.fdopen(fd, "w") as f:
        f.write(output)

    record_export(session["user_id"], None, f"batch_{export_type}", output)

    return send_file(path, mimetype=mimetype, as_attachment=True,
                     download_name=f"{safe_name}_batch.{ext}")


def _to_markdown(content, prompt, timestamp):
    return f"""# {prompt[:100]}

**Generated:** {timestamp}

---

{content}
"""


def _to_html(content, prompt, timestamp):
    import html
    safe_content = html.escape(content)
    safe_prompt = html.escape(prompt[:100])
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>{safe_prompt}</title>
<style>
  body {{ max-width: 800px; margin: 0 auto; padding: 2rem; font-family: system-ui, sans-serif; line-height: 1.6; }}
  pre {{ background: #f5f5f5; padding: 1rem; border-radius: 8px; white-space: pre-wrap; }}
  .meta {{ color: #666; font-size: 0.9rem; }}
</style>
</head>
<body>
  <h1>{safe_prompt}</h1>
  <p class="meta">{timestamp}</p>
  <pre>{safe_content}</pre>
</body>
</html>"""

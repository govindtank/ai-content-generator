"""Content Calendar — Schedule & manage content publishing dates."""

from datetime import datetime
from flask import Blueprint, jsonify, request, session

from app.decorators import login_required
from app.db import (
    get_calendar_events, create_calendar_event,
    update_calendar_event, delete_calendar_event,
)

calendar_bp = Blueprint("calendar", __name__, url_prefix="/api/calendar")


@calendar_bp.route("", methods=["GET"])
@login_required
def list_events():
    month = request.args.get("month")  # YYYY-MM
    start = request.args.get("start")
    end = request.args.get("end")
    events = get_calendar_events(session["user_id"], start_date=start, end_date=end, month=month)
    return jsonify({"events": [dict(e) for e in events]})


@calendar_bp.route("", methods=["POST"])
@login_required
def add_event():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    event_date = (data.get("event_date") or "").strip()
    if not title or not event_date:
        return jsonify({"error": "Title and event_date required"}), 400
    eid = create_calendar_event(
        user_id=session["user_id"],
        title=title,
        event_date=event_date,
        generation_id=data.get("generation_id"),
        description=data.get("description", ""),
        platform=data.get("platform", "blog"),
        status=data.get("status", "draft"),
    )
    return jsonify({"ok": True, "id": eid}), 201


@calendar_bp.route("/<int:event_id>", methods=["PUT"])
@login_required
def update_event(event_id):
    data = request.get_json(silent=True) or {}
    update_calendar_event(event_id, session["user_id"], **data)
    return jsonify({"ok": True})


@calendar_bp.route("/<int:event_id>", methods=["DELETE"])
@login_required
def remove_event(event_id):
    delete_calendar_event(event_id, session["user_id"])
    return jsonify({"ok": True})

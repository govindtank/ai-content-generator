"""Analytics — Usage statistics & insights."""

from flask import Blueprint, jsonify, session

from app.decorators import login_required
from app.db import get_analytics_summary

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@analytics_bp.route("/summary", methods=["GET"])
@login_required
def summary():
    data = get_analytics_summary(session["user_id"])
    return jsonify(data)

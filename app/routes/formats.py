"""Format types routes."""

from flask import Blueprint, jsonify

from app.db import get_format_types

formats_bp = Blueprint("formats", __name__, url_prefix="/api/formats")


@formats_bp.route("")
def list_formats():
    formats = get_format_types()
    return jsonify({
        "formats": [dict(f) for f in formats]
    })

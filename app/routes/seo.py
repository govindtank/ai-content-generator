"""SEO Tools — Keyword Analysis, Readability Scoring, Meta Suggestions."""

import re
from collections import Counter
from flask import Blueprint, jsonify, request, session

from app.decorators import login_required
from app.providers import router

seo_bp = Blueprint("seo", __name__, url_prefix="/api/seo")


# ─── READABILITY SCORE (Flesch Reading Ease) ────────────────────


def _syllable_count(word):
    """Simple syllable counter for English text."""
    word = word.lower().strip(".,!?;:'\"()[]{}")
    if not word:
        return 0
    vowels = "aeiouy"
    count = 0
    prev_is_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_is_vowel:
            count += 1
        prev_is_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    if word.endswith("le") and len(word) > 2 and word[-3] not in vowels:
        count += 1
    return max(1, count)


def flesch_reading_ease(text):
    """Calculate Flesch Reading Ease score (0-100)."""
    if not text.strip():
        return {"score": 0, "level": "N/A", "words": 0}

    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    words = re.findall(r"\b\w+\b", text)

    if not words:
        return {"score": 0, "level": "N/A", "words": 0}

    total_syllables = sum(_syllable_count(w) for w in words)
    word_count = len(words)
    sentence_count = max(1, len(sentences))

    score = 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (total_syllables / word_count)
    score = max(0, min(100, round(score)))

    if score >= 90:
        level = "Very Easy"
    elif score >= 80:
        level = "Easy"
    elif score >= 70:
        level = "Fairly Easy"
    elif score >= 60:
        level = "Standard"
    elif score >= 50:
        level = "Fairly Difficult"
    elif score >= 30:
        level = "Difficult"
    else:
        level = "Very Confusing"

    return {
        "score": score,
        "level": level,
        "words": word_count,
        "sentences": sentence_count,
        "syllables": total_syllables,
    }


# ─── KEYWORD ANALYSIS ───────────────────────────────────────────


def keyword_density(text, top_n=10):
    """Analyze keyword frequency and density in text."""
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    stop_words = {
        "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
        "her", "was", "one", "our", "out", "has", "have", "been", "some",
        "them", "than", "that", "this", "what", "when", "where", "which",
        "who", "will", "with", "would", "about", "also", "into", "more",
        "other", "their", "there", "these", "they", "very", "just", "from",
        "each", "make", "like", "than", "then", "many", "some", "such",
        "only", "over", "most", "even", "here", "well", "back", "after",
        "still", "before", "between", "through", "during", "because",
        "while", "since", "might", "could", "should", "would",
    }
    words = [w for w in words if w not in stop_words and len(w) > 2]
    total = len(words)
    counter = Counter(words)

    keywords = [
        {"word": word, "count": count, "density": round(count / total * 100, 1)}
        for word, count in counter.most_common(top_n)
    ]
    return {"keywords": keywords, "total_words": total}


# ─── META TAG SUGGESTIONS ───────────────────────────────────────


@seo_bp.route("/suggest-meta", methods=["POST"])
@login_required
def suggest_meta():
    """Generate SEO meta tags using AI."""
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    title = (data.get("title") or "").strip()

    if not content:
        return jsonify({"error": "Content required"}), 400

    # If no AI provider needed, use local analysis
    readability = flesch_reading_ease(content)
    kw_data = keyword_density(content)

    suggestions = {
        "meta_title": title or kw_data["keywords"][0]["word"].title() if kw_data["keywords"] else "",
        "meta_description": content[:155] + "..." if len(content) > 155 else content,
        "readability": readability,
        "keywords": [k["word"] for k in kw_data["keywords"][:5]],
        "word_count": len(re.findall(r"\b\w+\b", content)),
        "estimated_read_time": max(1, len(re.findall(r"\b\w+\b", content)) // 200),
    }

    # Use AI for enhanced suggestions if Gemini key is available
    try:
        provider_cls = router.get_provider("gemini")
        if provider_cls:
            provider = provider_cls(session["user_id"])
            ai_prompt = (
                f"Based on this content, suggest:\n"
                f"1. An SEO-optimized meta title (max 60 chars)\n"
                f"2. A meta description (max 160 chars)\n"
                f"3. 5-8 relevant tags/keywords\n"
                f"4. A focus keyphrase (single best keyword)\n\n"
                f"CONTENT (first 2000 chars):\n{content[:2000]}"
                f"\n\nReturn as JSON only: {{\"meta_title\":\"...\",\"meta_description\":\"...\",\"tags\":[...],\"focus_keyphrase\":\"...\"}}"
            )
            result = provider.generate_text(ai_prompt)
            if result:
                import json as json_mod
                try:
                    ai_suggestions = json_mod.loads(result)
                    suggestions.update(ai_suggestions)
                except (json_mod.JSONDecodeError, ValueError):
                    pass  # Fall back to local results
    except Exception:
        pass  # Fall back to local results

    return jsonify(suggestions)


# ─── READABILITY API ────────────────────────────────────────────


@seo_bp.route("/analyze", methods=["POST"])
@login_required
def analyze():
    """Full content analysis: readability + keywords."""
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()

    if not content:
        return jsonify({"error": "Content required"}), 400

    readability = flesch_reading_ease(content)
    kw_data = keyword_density(content)

    return jsonify({
        "readability": readability,
        "keywords": kw_data["keywords"],
        "total_keywords": len(kw_data["keywords"]),
        "total_words": kw_data["total_words"],
        "estimated_read_time": max(1, kw_data["total_words"] // 200),
    })

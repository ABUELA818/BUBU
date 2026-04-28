"""
Confidence / uncertainty estimation for the Virtual Try-On pipeline.

Produces a structured status dict:
  {
    "level":   "ok" | "low_confidence" | "invalid_capture",
    "score":   0-100,
    "issues":  [...],
    "message": str,
    "color":   hex,
  }
"""

from __future__ import annotations


# ── Weights for each quality dimension ───────────────────────────────────────

W_QUALITY    = 0.40   # average frame quality score
W_CONSISTENCY= 0.30   # stability between frames (low variance = good)
W_VIEWS      = 0.20   # number of views (front-only vs front+profile)
W_COVERAGE   = 0.10   # landmark coverage (key points visible)


def estimate_confidence(
    avg_quality:       float,
    consistency_score: float,
    views_used:        list[str],
    landmark_coverage: float,     # 0-1 fraction of key landmarks visible
    extra_issues:      list[dict] | None = None,
) -> dict:
    """
    avg_quality       : mean frame quality score (0-100)
    consistency_score : consistency across selected frames (0-100)
    views_used        : e.g. ['front'] or ['front', 'profile']
    landmark_coverage : fraction of the 8 key landmarks that are visible
    extra_issues      : any pre-detected issues to carry forward
    """
    extra_issues = extra_issues or []

    views_score = 100.0 if "profile" in views_used else 60.0

    overall = (
        W_QUALITY     * avg_quality       +
        W_CONSISTENCY * consistency_score +
        W_VIEWS       * views_score       +
        W_COVERAGE    * landmark_coverage * 100
    )
    overall = round(min(100.0, max(0.0, overall)), 1)

    issues = list(extra_issues)

    if avg_quality < 60:
        issues.append({
            "code":    "low_quality",
            "message": "Calidad de captura baja — mejora iluminación o posición",
        })
    if consistency_score < 65:
        issues.append({
            "code":    "high_variance",
            "message": "Alta variación entre frames — mantente más quieto/a",
        })
    if "profile" not in views_used:
        issues.append({
            "code":    "single_view",
            "message": "Sin vista de perfil — precisión reducida en profundidad",
        })
    if landmark_coverage < 0.75:
        issues.append({
            "code":    "low_coverage",
            "message": "Algunos puntos del cuerpo no son visibles con claridad",
        })

    # Determine level
    if overall >= 72 and not any(i["code"] in ("low_quality", "high_variance") for i in issues):
        level   = "ok"
        message = "Medidas obtenidas con alta confianza"
        color   = "#00FF88"
    elif overall >= 50:
        level   = "low_confidence"
        message = "Medidas aproximadas — considera repetir para mayor precisión"
        color   = "#FFAA00"
    else:
        level   = "invalid_capture"
        message = "Calidad insuficiente para medir con precisión"
        color   = "#FF4444"

    return {
        "level":   level,
        "score":   overall,
        "issues":  issues,
        "message": message,
        "color":   color,
    }
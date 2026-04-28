"""
Frame quality scoring and feedback generation.
Now orientation-aware: front and profile views are scored differently.
"""

KEY_LANDMARKS = [11, 12, 23, 24, 25, 26, 27, 28]

ISSUE_WEIGHTS = {
    "bad_pose":         25,
    "low_visibility":   20,
    "too_far":          18,
    "feet_not_visible": 12,
    "head_not_visible":  8,
    "wrong_orientation": 15,
}

FEEDBACK_MESSAGES = {
    "bad_pose":          ("Ponte completamente de frente a la cámara",   "#FF4444"),
    "low_visibility":    ("Mejora la iluminación y despeja el fondo",    "#FF4444"),
    "too_far":           ("Acércate un poco más",                        "#FF8800"),
    "feet_not_visible":  ("Aléjate para que se vean los pies",          "#FF8800"),
    "head_not_visible":  ("Sube la cámara para incluir tu cabeza",       "#FFAA00"),
    "wrong_orientation": ("Gírate de frente / de lado según la fase",   "#FF8800"),
}


def score_frame(landmarks: list, issues: list, orientation: str = "front") -> float:
    """
    Score a single frame 0-100.
    orientation: 'front' | 'profile_right' | 'profile_left' | 'oblique' | 'unknown'
    """
    visible_all  = sum(1 for lm in landmarks if lm["visibility"] > 0.65)
    visibility_score = (visible_all / 33) * 40

    # For profile views, arms may not be fully visible — adjust key landmarks
    if orientation.startswith("profile"):
        # Only check shoulder, hip, knee, ankle on the near side
        near_side = [11, 23, 25, 27] if orientation == "profile_left" else [12, 24, 26, 28]
        visible_key = sum(1 for i in near_side if landmarks[i]["visibility"] > 0.65)
        key_score   = (visible_key / len(near_side)) * 35
    else:
        visible_key = sum(1 for i in KEY_LANDMARKS if landmarks[i]["visibility"] > 0.70)
        key_score   = (visible_key / len(KEY_LANDMARKS)) * 35

    penalty    = sum(ISSUE_WEIGHTS.get(iss["code"], 10) for iss in issues)
    pose_score = max(0.0, 25.0 - penalty)

    return round(visibility_score + key_score + pose_score, 1)


def get_feedback(
    score: float,
    issues: list,
    orientation: str = "front",
    orientation_confidence: float = 1.0,
) -> dict:
    """
    Return the highest-priority feedback message for the user.
    """
    # Wrong orientation takes highest priority
    orient_issue = next(
        (iss for iss in issues if iss["code"] == "wrong_orientation"), None
    )
    if orient_issue:
        msg, color = FEEDBACK_MESSAGES["wrong_orientation"]
        return {"status": "bad", "message": orient_issue["message"], "color": color}

    # Other issues in priority order
    for code in ISSUE_WEIGHTS:
        for iss in issues:
            if iss["code"] == code and code != "wrong_orientation":
                msg, color = FEEDBACK_MESSAGES[code]
                return {"status": "bad", "message": msg, "color": color}

    if score >= 82:
        return {"status": "good", "message": "¡Perfecto! Mantén la postura", "color": "#00FF88"}
    if score >= 65:
        return {"status": "ok",   "message": "Casi listo, sigue ajustando",  "color": "#FFAA00"}
    return     {"status": "bad",  "message": "Ajusta tu posición",           "color": "#FF4444"}
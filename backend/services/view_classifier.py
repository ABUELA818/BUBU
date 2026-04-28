"""
Classifies the orientation of the person in a frame using MediaPipe world landmarks.
World landmarks are in metric space (meters), centered on the subject.
  x → subject's lateral axis (positive = subject's right)
  y → vertical axis (positive = down)
  z → depth axis (positive = toward camera)
"""


def classify_view(world_landmarks: list) -> tuple[str, float]:
    """
    Returns (orientation, confidence) where orientation is one of:
      'front'         – person facing camera (±30°)
      'profile_right' – subject's right side toward camera
      'profile_left'  – subject's left side toward camera
      'oblique'       – diagonal, not ideal for either metric
      'unknown'       – not enough data
    """
    if not world_landmarks or len(world_landmarks) < 25:
        return "unknown", 0.0

    ls = world_landmarks[11]   # left shoulder
    rs = world_landmarks[12]   # right shoulder

    if ls.get("visibility", 0) < 0.30 and rs.get("visibility", 0) < 0.30:
        return "unknown", 0.0

    # Lateral spread (x) vs depth spread (z) between shoulders
    shoulder_dx = abs(ls["x"] - rs["x"])
    shoulder_dz = abs(ls["z"] - rs["z"])

    total = shoulder_dx + shoulder_dz
    if total < 0.005:
        return "unknown", 0.0

    frontness = shoulder_dx / total   # 0.0 = pure profile, 1.0 = pure front

    if frontness >= 0.70:
        return "front", round(frontness, 2)

    if frontness <= 0.30:
        # Which side faces the camera? (smaller z in world coords = closer to camera)
        if ls["z"] < rs["z"]:
            # Left shoulder closer → subject's left side forward
            return "profile_left", round(1.0 - frontness, 2)
        else:
            return "profile_right", round(1.0 - frontness, 2)

    return "oblique", round(0.5 - abs(frontness - 0.5), 2)


def orientation_feedback(orientation: str, phase: str) -> dict | None:
    """
    Returns a feedback dict if the orientation does not match the expected phase,
    or None if everything is OK.
    """
    if phase == "front":
        if orientation in ("profile_left", "profile_right"):
            return {
                "code": "wrong_orientation",
                "message": "Gírate completamente de frente a la cámara",
                "color": "#FF8800",
            }
        if orientation == "oblique":
            return {
                "code": "oblique",
                "message": "Enderézate — ponte de frente",
                "color": "#FFAA00",
            }

    elif phase == "profile":
        if orientation == "front":
            return {
                "code": "wrong_orientation",
                "message": "Gírate 90° de lado (perfil completo)",
                "color": "#FF8800",
            }
        if orientation == "oblique":
            return {
                "code": "oblique",
                "message": "Necesitas girar más de lado",
                "color": "#FFAA00",
            }

    return None
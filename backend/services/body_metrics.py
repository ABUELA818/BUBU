import math


# ── Distance helpers ──────────────────────────────────────────────────────────

def _dist2d(p1: dict, p2: dict) -> float:
    return math.sqrt((p1["x"] - p2["x"]) ** 2 + (p1["y"] - p2["y"]) ** 2)


def _dist3d(p1: dict, p2: dict) -> float:
    return math.sqrt(
        (p1["x"] - p2["x"]) ** 2 +
        (p1["y"] - p2["y"]) ** 2 +
        (p1["z"] - p2["z"]) ** 2
    )


def _mid(a: dict, b: dict, use_z: bool = False) -> dict:
    m = {"x": (a["x"] + b["x"]) / 2, "y": (a["y"] + b["y"]) / 2}
    if use_z:
        m["z"] = (a["z"] + b["z"]) / 2
    return m


# ── 2D fallback ───────────────────────────────────────────────────────────────

def _calculate_2d(landmarks: list, real_height_cm: float | None) -> dict:
    LS, RS = landmarks[11], landmarks[12]
    LH, RH = landmarks[23], landmarks[24]
    LK, RK = landmarks[25], landmarks[26]
    LA, RA = landmarks[27], landmarks[28]

    shoulder_width = _dist2d(LS, RS)
    hip_width      = _dist2d(LH, RH)

    mid_sh  = _mid(LS, RS)
    mid_hip = _mid(LH, RH)
    mid_kn  = _mid(LK, RK)
    mid_an  = _mid(LA, RA)

    torso_height = _dist2d(mid_sh,  mid_hip)
    thigh_length = _dist2d(mid_hip, mid_kn)
    leg_length   = _dist2d(mid_kn,  mid_an)
    body_height  = _dist2d(mid_sh,  mid_an)

    ratio = shoulder_width / hip_width if hip_width != 0 else 0

    metrics = {
        "shoulder_width":     shoulder_width,
        "hip_width":          hip_width,
        "body_height":        body_height,
        "torso_height":       torso_height,
        "thigh_length":       thigh_length,
        "leg_length":         leg_length,
        "shoulder_hip_ratio": ratio,
        "source":             "2d",
    }

    if real_height_cm and body_height > 0:
        scale = (real_height_cm * 0.87) / body_height
        metrics["measurements_cm"] = {
            "shoulder_width_cm": round(shoulder_width * scale, 1),
            "hip_width_cm":      round(hip_width      * scale, 1),
            "torso_height_cm":   round(torso_height   * scale, 1),
            "thigh_length_cm":   round(thigh_length   * scale, 1),
            "leg_length_cm":     round(leg_length     * scale, 1),
        }

    return metrics


# ── 3D calculation using world landmarks ─────────────────────────────────────

def _calculate_3d(world_landmarks: list, real_height_cm: float | None) -> dict:
    LS, RS = world_landmarks[11], world_landmarks[12]
    LH, RH = world_landmarks[23], world_landmarks[24]
    LK, RK = world_landmarks[25], world_landmarks[26]
    LA, RA = world_landmarks[27], world_landmarks[28]

    shoulder_width = _dist3d(LS, RS)
    hip_width      = _dist3d(LH, RH)

    mid_sh  = _mid(LS, RS,  use_z=True)
    mid_hip = _mid(LH, RH,  use_z=True)
    mid_kn  = _mid(LK, RK,  use_z=True)
    mid_an  = _mid(LA, RA,  use_z=True)

    torso_height = _dist3d(mid_sh,  mid_hip)
    thigh_length = _dist3d(mid_hip, mid_kn)
    leg_length   = _dist3d(mid_kn,  mid_an)
    body_height  = _dist3d(mid_sh,  mid_an)

    ratio = shoulder_width / hip_width if hip_width != 0 else 0

    metrics = {
        "shoulder_width":     shoulder_width,
        "hip_width":          hip_width,
        "body_height":        body_height,
        "torso_height":       torso_height,
        "thigh_length":       thigh_length,
        "leg_length":         leg_length,
        "shoulder_hip_ratio": ratio,
        "source":             "3d",
    }

    if real_height_cm and body_height > 0:
        scale = (real_height_cm * 0.87) / body_height
        metrics["measurements_cm"] = {
            "shoulder_width_cm": round(shoulder_width * scale, 1),
            "hip_width_cm":      round(hip_width      * scale, 1),
            "torso_height_cm":   round(torso_height   * scale, 1),
            "thigh_length_cm":   round(thigh_length   * scale, 1),
            "leg_length_cm":     round(leg_length     * scale, 1),
        }

    return metrics


# ── Public API ────────────────────────────────────────────────────────────────

def calculate_body_metrics(
    landmarks:        list,
    real_height_cm:   float | None = None,
    world_landmarks:  list | None  = None,
) -> dict:
    """
    Calculate body metrics.
    Uses 3D world_landmarks when available (more accurate).
    Falls back to 2D normalized landmarks otherwise.
    """
    if world_landmarks and len(world_landmarks) >= 29:
        return _calculate_3d(world_landmarks, real_height_cm)
    return _calculate_2d(landmarks, real_height_cm)
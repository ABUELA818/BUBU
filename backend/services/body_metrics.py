import math

def distance(p1, p2):
    return math.sqrt(
        (p1["x"] - p2["x"])**2 +
        (p1["y"] - p2["y"])**2
    )

def calculate_body_metrics(landmarks, real_height_cm=None):
    LEFT_SHOULDER  = 11
    RIGHT_SHOULDER = 12
    LEFT_HIP       = 23
    RIGHT_HIP      = 24
    LEFT_KNEE      = 25
    RIGHT_KNEE     = 26
    LEFT_ANKLE     = 27
    RIGHT_ANKLE    = 28

    # Anchos normalizados
    shoulder_width = distance(landmarks[LEFT_SHOULDER],  landmarks[RIGHT_SHOULDER])
    hip_width      = distance(landmarks[LEFT_HIP],       landmarks[RIGHT_HIP])

    # Alturas de segmentos
    mid_shoulder = {
        "x": (landmarks[LEFT_SHOULDER]["x"] + landmarks[RIGHT_SHOULDER]["x"]) / 2,
        "y": (landmarks[LEFT_SHOULDER]["y"] + landmarks[RIGHT_SHOULDER]["y"]) / 2,
    }
    mid_hip = {
        "x": (landmarks[LEFT_HIP]["x"] + landmarks[RIGHT_HIP]["x"]) / 2,
        "y": (landmarks[LEFT_HIP]["y"] + landmarks[RIGHT_HIP]["y"]) / 2,
    }
    mid_knee = {
        "x": (landmarks[LEFT_KNEE]["x"] + landmarks[RIGHT_KNEE]["x"]) / 2,
        "y": (landmarks[LEFT_KNEE]["y"] + landmarks[RIGHT_KNEE]["y"]) / 2,
    }
    mid_ankle = {
        "x": (landmarks[LEFT_ANKLE]["x"] + landmarks[RIGHT_ANKLE]["x"]) / 2,
        "y": (landmarks[LEFT_ANKLE]["y"] + landmarks[RIGHT_ANKLE]["y"]) / 2,
    }

    torso_height  = distance(mid_shoulder, mid_hip)
    thigh_length  = distance(mid_hip,      mid_knee)
    leg_length    = distance(mid_knee,     mid_ankle)
    body_height   = distance(mid_shoulder, mid_ankle)

    ratio = shoulder_width / hip_width if hip_width != 0 else 0

    metrics = {
        "shoulder_width":    shoulder_width,
        "hip_width":         hip_width,
        "body_height":       body_height,
        "shoulder_hip_ratio": ratio
    }

    # ── Conversión a cm ──────────────────────────────────────────
    # Hombros a tobillos ≈ 87% de la estatura real
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
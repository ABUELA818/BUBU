import math

def distance(p1, p2):
    return math.sqrt(
        (p1["x"] - p2["x"])**2 +
        (p1["y"] - p2["y"])**2
    )

def calculate_body_metrics(landmarks):
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28

    # Anchura de hombros
    shoulder_width = distance(
        landmarks[LEFT_SHOULDER],
        landmarks[RIGHT_SHOULDER]
    )

    # Anchura de cadera
    hip_width = distance(
        landmarks[LEFT_HIP],
        landmarks[RIGHT_HIP]
    )

    # Altura aproximada
    mid_shoulder = {
        "x": (landmarks[LEFT_SHOULDER]["x"] + landmarks[RIGHT_SHOULDER]["x"]) / 2,
        "y": (landmarks[LEFT_SHOULDER]["y"] + landmarks[RIGHT_SHOULDER]["y"]) / 2,
    }

    mid_ankle = {
        "x": (landmarks[LEFT_ANKLE]["x"] + landmarks[RIGHT_ANKLE]["x"]) / 2,
        "y": (landmarks[LEFT_ANKLE]["y"] + landmarks[RIGHT_ANKLE]["y"]) / 2,
    }

    body_height = distance(mid_shoulder, mid_ankle)

    # Relación hombro/cadera
    ratio = shoulder_width / hip_width if hip_width != 0 else 0

    return {
        "shoulder_width": shoulder_width,
        "hip_width": hip_width,
        "body_height": body_height,
        "shoulder_hip_ratio": ratio
    }
def classify_body(metrics):
    ratio = metrics["shoulder_hip_ratio"]

    # rangos heurísticos
    if ratio > 1.15:
        body_type = "triangulo_invertido"
    elif ratio < 0.85:
        body_type = "triangulo"
    else:
        body_type = "rectangular"

    return {
        "body_type": body_type,
        "ratio": ratio
    }
def validate_pose(landmarks):
    # índices clave (MediaPipe)
    NOSE = 0
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28

    key_points = [
        NOSE,
        LEFT_SHOULDER, RIGHT_SHOULDER,
        LEFT_HIP, RIGHT_HIP,
        LEFT_ANKLE, RIGHT_ANKLE
    ]

    # 1. VISIBILIDAD mínima
    for idx in key_points:
        if landmarks[idx]["visibility"] < 0.5:
            return False, f"Punto clave no visible: {idx}"

    # 2. CUERPO COMPLETO (pies debajo de cadera)
    if not (landmarks[LEFT_ANKLE]["y"] > landmarks[LEFT_HIP]["y"] and
            landmarks[RIGHT_ANKLE]["y"] > landmarks[RIGHT_HIP]["y"]):
        return False, "Cuerpo incompleto (piernas no visibles)"

    # 3. ORIENTACIÓN (hombros alineados)
    shoulder_diff = abs(
        landmarks[LEFT_SHOULDER]["x"] - landmarks[RIGHT_SHOULDER]["x"]
    )

    if shoulder_diff < 0.1:
        return False, "Posible vista lateral (no frontal)"

    return True, "Pose válida"
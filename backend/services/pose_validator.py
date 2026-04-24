def validate_pose(landmarks):
    issues = []

    NOSE = 0
    LEFT_FOOT = 27
    RIGHT_FOOT = 28
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12

    # 1. Visibilidad general
    visible_points = [lm for lm in landmarks if lm["visibility"] > 0.5]

    if len(visible_points) < 20:
        issues.append({
            "code": "low_visibility",
            "message": "No se detecta bien el cuerpo",
            "suggestion": "Asegúrate de tener buena iluminación y fondo limpio"
        })

    # 2. Cabeza
    if landmarks[NOSE]["visibility"] < 0.5:
        issues.append({
            "code": "head_not_visible",
            "message": "No se ve la cabeza",
            "suggestion": "Ajusta la cámara para incluir tu cabeza completa"
        })

    # 3. Pies
    if (landmarks[LEFT_FOOT]["visibility"] < 0.5 and
        landmarks[RIGHT_FOOT]["visibility"] < 0.5):
        issues.append({
            "code": "feet_not_visible",
            "message": "No se ven los pies",
            "suggestion": "Aléjate un poco de la cámara"
        })

    # 4. Escala
    y_values = [lm["y"] for lm in visible_points]
    if y_values:
        height = max(y_values) - min(y_values)
        if height < 0.5:
            issues.append({
                "code": "too_far",
                "message": "Estás demasiado lejos",
                "suggestion": "Acércate para ocupar más espacio en la imagen"
            })

    # 5. Pose frontal
    left_shoulder = landmarks[LEFT_SHOULDER]["x"]
    right_shoulder = landmarks[RIGHT_SHOULDER]["x"]

    if abs(left_shoulder - right_shoulder) < 0.05:
        issues.append({
            "code": "bad_pose",
            "message": "La pose no es frontal",
            "suggestion": "Ponte de frente a la cámara con los brazos relajados"
        })

    return issues
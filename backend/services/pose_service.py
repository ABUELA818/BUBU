import cv2
import mediapipe as mp

mp_pose = mp.solutions.pose

def detect_pose(file_path):
    image = cv2.imread(file_path)

    if image is None:
        return False, "No se pudo leer la imagen"

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    with mp_pose.Pose(static_image_mode=True) as pose:
        results = pose.process(image_rgb)

    if not results.pose_landmarks:
        return False, "No se detectó el cuerpo"

    landmarks = []

    for lm in results.pose_landmarks.landmark:
        landmarks.append({
            "x": lm.x,
            "y": lm.y,
            "z": lm.z,
            "visibility": lm.visibility
        })

    return True, landmarks
import cv2
import mediapipe as mp

mp_pose = mp.solutions.pose


def detect_pose(file_path: str) -> tuple[bool, dict | str]:
    """
    Detects body pose in an image.

    Returns:
        (True,  { "landmarks": [...], "world_landmarks": [...] })  on success
        (False, "error message")                                   on failure

    landmarks       – 2D normalized coords  (x, y in [0,1]; z relative; visibility)
    world_landmarks – 3D metric coords      (x, y, z in meters, body-centered)
    """
    image = cv2.imread(file_path)
    if image is None:
        return False, "No se pudo leer la imagen"

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    with mp_pose.Pose(
        static_image_mode=True,
        model_complexity=1,           # 0=fast, 1=balanced, 2=accurate
        enable_segmentation=False,
        smooth_landmarks=True,
    ) as pose:
        results = pose.process(image_rgb)

    if not results.pose_landmarks:
        return False, "No se detectó el cuerpo"

    # ── 2D normalized landmarks ───────────────────────────────────────────────
    landmarks = [
        {
            "x":          lm.x,
            "y":          lm.y,
            "z":          lm.z,
            "visibility": lm.visibility,
        }
        for lm in results.pose_landmarks.landmark
    ]

    # ── 3D world landmarks (metric, body-centered) ────────────────────────────
    world_landmarks = []
    if results.pose_world_landmarks:
        world_landmarks = [
            {
                "x":          lm.x,
                "y":          lm.y,
                "z":          lm.z,
                "visibility": lm.visibility,
            }
            for lm in results.pose_world_landmarks.landmark
        ]

    return True, {
        "landmarks":       landmarks,
        "world_landmarks": world_landmarks,
    }
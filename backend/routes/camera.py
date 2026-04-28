from fastapi import APIRouter, File, Form, UploadFile
from typing import List, Optional
import os, uuid

from services.pose_service            import detect_pose
from services.body_metrics            import calculate_body_metrics
from services.body_classifier         import classify_body
from services.recommendation_service  import get_recommendations
from services.product_recommender     import recommend_products
from services.pose_validator          import validate_pose
from services.frame_quality           import score_frame, get_feedback
from services.frame_selector          import select_best_frames, select_best_by_view
from services.view_classifier         import classify_view, orientation_feedback
from services.fusion_3d               import fuse_views, extract_metrics_3d
from services.uncertainty             import estimate_confidence

router = APIRouter()
TEMP   = "backend/temp"
os.makedirs(TEMP, exist_ok=True)


# ── Helper: save upload to temp file ─────────────────────────────────────────

async def _save_temp(file: UploadFile, prefix: str = "frame") -> str:
    path = os.path.join(TEMP, f"{prefix}_{uuid.uuid4().hex}.jpg")
    with open(path, "wb") as f:
        f.write(await file.read())
    return path


# ── /evaluate-frame ───────────────────────────────────────────────────────────

@router.post("/evaluate-frame")
async def evaluate_frame(
    file:  UploadFile = File(...),
    phase: str        = Form(default="front"),   # 'front' or 'profile'
):
    """
    Real-time frame evaluation.
    Returns quality score, feedback, orientation classification, and landmarks.
    """
    path = await _save_temp(file, "eval")

    try:
        pose_ok, pose_data = detect_pose(path)

        if not pose_ok:
            return {
                "score":       0,
                "landmarks":   None,
                "orientation": "unknown",
                "orientation_confidence": 0.0,
                "feedback": {
                    "status":  "bad",
                    "message": "No se detecta el cuerpo — busca mejor iluminación",
                    "color":   "#FF4444",
                },
            }

        landmarks       = pose_data["landmarks"]
        world_landmarks = pose_data["world_landmarks"]

        # Orientation classification
        orientation, orient_conf = classify_view(world_landmarks)

        # Pose issues (standard validator)
        issues = validate_pose(landmarks)

        # Add orientation issue if mismatch
        orient_fb = orientation_feedback(orientation, phase)
        if orient_fb:
            issues.insert(0, orient_fb)

        score    = score_frame(landmarks, issues, orientation)
        feedback = get_feedback(score, issues, orientation, orient_conf)

        return {
            "score":                  score,
            "landmarks":              landmarks,
            "world_landmarks":        world_landmarks,
            "orientation":            orientation,
            "orientation_confidence": orient_conf,
            "feedback":               feedback,
        }

    finally:
        if os.path.exists(path):
            os.remove(path)


# ── /analyze-frames (legacy single-view) ─────────────────────────────────────

@router.post("/analyze-frames")
async def analyze_frames(
    files:     List[UploadFile]  = File(...),
    height_cm: Optional[float]   = Form(None),
):
    """
    Analyze a single-view burst (backward-compatible endpoint).
    Now uses 3D world landmarks when available.
    """
    temp_paths  = []
    frames_data = []

    for file in files:
        path = await _save_temp(file, "frame")
        temp_paths.append(path)

    try:
        for path in temp_paths:
            pose_ok, pose_data = detect_pose(path)
            if not pose_ok:
                continue

            landmarks       = pose_data["landmarks"]
            world_landmarks = pose_data["world_landmarks"]

            orientation, orient_conf = classify_view(world_landmarks)
            issues  = validate_pose(landmarks)
            score   = score_frame(landmarks, issues, orientation)
            metrics = calculate_body_metrics(landmarks, height_cm, world_landmarks)

            # Also store raw 3D metrics for fusion
            metrics_3d = extract_metrics_3d(world_landmarks, height_cm)

            frames_data.append({
                "score":       score,
                "landmarks":   landmarks,
                "world_landmarks": world_landmarks,
                "metrics":     metrics,
                "metrics_3d":  metrics_3d if metrics_3d else metrics,
                "orientation": orientation,
            })

        if not frames_data:
            return {"error": "No se pudo analizar ningún frame"}

        aggregated = select_best_frames(frames_data)
        if not aggregated:
            return {"error": "Calidad insuficiente en todos los frames"}

        # Scale aggregated metrics
        if height_cm and aggregated.get("body_height", 0) > 0:
            scale = (height_cm * 0.87) / aggregated["body_height"]
            aggregated["measurements_cm"] = {
                "shoulder_width_cm": round(aggregated["shoulder_width"] * scale, 1),
                "hip_width_cm":      round(aggregated["hip_width"]      * scale, 1),
            }

        best_frame     = max(frames_data, key=lambda x: x["score"])
        classification = classify_body(aggregated)

        return {
            "metrics":         aggregated,
            "measurements_cm": aggregated.get("measurements_cm"),
            "classification":  classification,
            "recommendations": get_recommendations(classification["body_type"]),
            "products":        recommend_products(classification["body_type"]),
            "landmarks":       best_frame["landmarks"],
            "frame_count":     len(frames_data),
            "frames_used":     aggregated["frame_count"],
            "quality_score":   aggregated["avg_score"],
            "confidence": {
                "level":   "low_confidence" if len(frames_data) < 4 else "ok",
                "message": "Vista frontal solamente — considera añadir perfil",
            },
        }

    finally:
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)


# ── /analyze-multiview (new two-phase endpoint) ───────────────────────────────

@router.post("/analyze-multiview")
async def analyze_multiview(
    front_files:   List[UploadFile]         = File(...),
    profile_files: Optional[List[UploadFile]] = File(default=None),
    height_cm:     Optional[float]           = Form(None),
):
    """
    Analyze front + (optional) profile frames using 3D fusion.
    Returns structured result with confidence level, fused metrics, and issues.
    """
    all_paths      = []
    front_frames   = []
    profile_frames = []

    async def process_view(files: list, expected_orientation: str) -> list:
        frames = []
        for file in files:
            path = await _save_temp(file, expected_orientation)
            all_paths.append(path)

            pose_ok, pose_data = detect_pose(path)
            if not pose_ok:
                continue

            landmarks       = pose_data["landmarks"]
            world_landmarks = pose_data["world_landmarks"]

            orientation, orient_conf = classify_view(world_landmarks)
            issues   = validate_pose(landmarks)
            score    = score_frame(landmarks, issues, orientation)
            metrics  = calculate_body_metrics(landmarks, height_cm, world_landmarks)
            metrics_3d = extract_metrics_3d(world_landmarks, height_cm)

            frames.append({
                "score":           score,
                "landmarks":       landmarks,
                "world_landmarks": world_landmarks,
                "metrics":         metrics,
                "metrics_3d":      metrics_3d if metrics_3d else metrics,
                "orientation":     orientation,
                "orient_conf":     orient_conf,
            })
        return frames

    try:
        front_frames   = await process_view(front_files,   "front")
        if profile_files:
            profile_frames = await process_view(profile_files, "profile")

        if not front_frames:
            return {
                "error":      True,
                "confidence": {"level": "invalid_capture"},
                "issues": [{"code": "no_data", "message": "No se detectó el cuerpo en ningún frame frontal"}],
            }

        # Select best frames per view
        best_front, best_profile = select_best_by_view(
            front_frames + profile_frames
        )

        # 3D fusion
        fusion = fuse_views(
            front_frames   = best_front,
            profile_frames = best_profile if best_profile else [],
            real_height_cm = height_cm,
        )

        fused_metrics  = fusion.get("metrics", {})
        measurements   = fusion.get("measurements_cm")

        # Landmark coverage (key landmarks)
        KEY_LM = [11, 12, 23, 24, 25, 26, 27, 28]
        if best_front:
            best_lms = best_front[0]["landmarks"]
            lm_cov   = sum(1 for i in KEY_LM if best_lms[i]["visibility"] > 0.65) / len(KEY_LM)
        else:
            lm_cov = 0.0

        avg_quality  = sum(f["score"] for f in best_front) / max(len(best_front), 1)
        consistency  = fusion.get("consistency_score", 70.0)
        views_used   = fusion.get("views_used", ["front"])

        uncertainty = estimate_confidence(
            avg_quality       = avg_quality,
            consistency_score = consistency,
            views_used        = views_used,
            landmark_coverage = lm_cov,
            extra_issues      = fusion.get("issues", []),
        )

        classification = classify_body(fused_metrics) if fused_metrics else {}

        best_frame_overall = max(
            front_frames + profile_frames,
            key=lambda x: x["score"],
        )

        return {
            "metrics":          fused_metrics,
            "measurements_cm":  measurements,
            "classification":   classification,
            "recommendations":  get_recommendations(classification.get("body_type", "")),
            "products":         recommend_products(classification.get("body_type", "")),
            "landmarks":        best_frame_overall["landmarks"],
            "confidence":       uncertainty,
            "consistency_score": consistency,
            "views_used":       views_used,
            "frame_count":      fusion.get("frame_count", len(front_frames)),
            "front_count":      fusion.get("front_count", len(best_front)),
            "profile_count":    fusion.get("profile_count", len(best_profile)),
            "quality_score":    round(avg_quality, 1),
        }

    finally:
        for path in all_paths:
            if os.path.exists(path):
                os.remove(path)
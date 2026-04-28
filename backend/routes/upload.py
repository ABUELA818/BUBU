from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional

from services.image_service           import validate_image
from services.pose_service            import detect_pose
from services.body_metrics            import calculate_body_metrics
from services.body_classifier         import classify_body
from services.recommendation_service  import get_recommendations
from services.product_recommender     import recommend_products
from services.pose_validator          import validate_pose
from services.view_classifier         import classify_view
from services.uncertainty             import estimate_confidence

import os

router = APIRouter()

UPLOAD_DIR = "backend/temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

KEY_LANDMARKS = [11, 12, 23, 24, 25, 26, 27, 28]


@router.post("/upload")
async def upload_image(
    file:      UploadFile        = File(...),
    height_cm: Optional[float]  = Form(None),
):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    is_valid, result = validate_image(file_path)
    if not is_valid:
        os.remove(file_path)
        return {"error": result}

    pose_ok, pose_data = detect_pose(file_path)
    if not pose_ok:
        os.remove(file_path)
        return {"error": pose_data}

    # Unpack new format
    landmarks       = pose_data["landmarks"]
    world_landmarks = pose_data["world_landmarks"]

    issues = validate_pose(landmarks)
    if issues:
        return {"error": True, "issues": issues}

    # Orientation classification
    orientation, orient_conf = classify_view(world_landmarks)

    # Metrics — prefer 3D when world_landmarks are available
    metrics        = calculate_body_metrics(landmarks, height_cm, world_landmarks)
    classification = classify_body(metrics)
    recommendations = get_recommendations(classification["body_type"])
    products        = recommend_products(classification["body_type"])

    # Confidence for single-image upload
    lm_cov = sum(1 for i in KEY_LANDMARKS if landmarks[i]["visibility"] > 0.65) / len(KEY_LANDMARKS)
    uncertainty = estimate_confidence(
        avg_quality       = 75.0,   # single image — no burst quality score
        consistency_score = 70.0,   # no multi-frame consistency
        views_used        = [orientation] if orientation != "unknown" else ["front"],
        landmark_coverage = lm_cov,
    )

    return {
        "filename":        file.filename,
        "message":         "imagen válida",
        "metrics":         metrics,
        "measurements_cm": metrics.get("measurements_cm"),
        "classification":  classification,
        "recommendations": recommendations,
        "products":        products,
        "landmarks":       landmarks,
        "orientation":     orientation,
        "confidence":      uncertainty,
    }
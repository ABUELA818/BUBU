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
from services.frame_selector          import select_best_frames

router = APIRouter()
TEMP   = "backend/temp"
os.makedirs(TEMP, exist_ok=True)


@router.post("/evaluate-frame")
async def evaluate_frame(file: UploadFile = File(...)):
    path = os.path.join(TEMP, f"eval_{uuid.uuid4().hex}.jpg")

    with open(path, "wb") as f:
        f.write(await file.read())

    try:
        pose_ok, pose_data = detect_pose(path)
        if not pose_ok:
            return {
                "score": 0,
                "landmarks": None,
                "feedback": {
                    "status": "bad",
                    "message": "No se detecta el cuerpo — busca mejor iluminación",
                    "color": "#FF4444"
                }
            }

        issues   = validate_pose(pose_data)
        score    = score_frame(pose_data, issues)
        feedback = get_feedback(score, issues)

        return {
            "score":     score,
            "landmarks": pose_data,
            "feedback":  feedback
        }

    finally:
        if os.path.exists(path):
            os.remove(path)


@router.post("/analyze-frames")
async def analyze_frames(
    files: List[UploadFile] = File(...),
    height_cm: Optional[float] = Form(None)
):
    """Analiza un lote de frames, selecciona los mejores y agrega medidas."""
    temp_paths  = []
    frames_data = []

    for file in files:
        path = os.path.join(TEMP, f"frame_{uuid.uuid4().hex}.jpg")
        temp_paths.append(path)
        with open(path, "wb") as f:
            f.write(await file.read())

    try:
        for path in temp_paths:
            pose_ok, pose_data = detect_pose(path)
            if not pose_ok:
                continue

            issues  = validate_pose(pose_data)
            score   = score_frame(pose_data, issues)
            metrics = calculate_body_metrics(pose_data, real_height_cm=height_cm)

            frames_data.append({
                "score":     score,
                "landmarks": pose_data,
                "metrics":   metrics,
            })

        if not frames_data:
            return {"error": "No se pudo analizar ningún frame"}

        aggregated = select_best_frames(frames_data)
        if not aggregated:
            return {"error": "Calidad insuficiente en todos los frames"}

        # Medidas en cm sobre métricas agregadas
        if height_cm and aggregated["body_height"] > 0:
            scale = (height_cm * 0.87) / aggregated["body_height"]
            aggregated["measurements_cm"] = {
                "shoulder_width_cm": round(aggregated["shoulder_width"] * scale, 1),
                "hip_width_cm":      round(aggregated["hip_width"]      * scale, 1),
            }
            best_frame = max(frames_data, key=lambda x: x["score"])
            if "measurements_cm" in best_frame["metrics"]:
                aggregated["measurements_cm"].update({
                    k: v for k, v in best_frame["metrics"]["measurements_cm"].items()
                    if k not in aggregated["measurements_cm"]
                })

        best_frame     = max(frames_data, key=lambda x: x["score"])
        classification = classify_body(aggregated)

        return {
            "metrics":         aggregated,
            "classification":  classification,
            "recommendations": get_recommendations(classification["body_type"]),
            "products":        recommend_products(classification["body_type"]),
            "landmarks":       best_frame["landmarks"],
            "frame_count":     len(frames_data),
            "frames_used":     aggregated["frame_count"],
            "quality_score":   aggregated["avg_score"],
        }

    finally:
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)
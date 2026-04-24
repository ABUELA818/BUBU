from fastapi import APIRouter, UploadFile, File

from services.image_service import validate_image
from services.pose_service import detect_pose
from services.body_metrics import calculate_body_metrics
from services.body_classifier import classify_body
from services.recommendation_service import get_recommendations

import os

router = APIRouter()

UPLOAD_DIR = "backend/temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # VALIDACIÓN
    is_valid, result = validate_image(file_path)

    if not is_valid:
        os.remove(file_path)
        return {
            "error": result
        }

    pose_ok, pose_data = detect_pose(file_path)

    if not pose_ok:
        os.remove(file_path)
        return {
            "error": pose_data
        }
    
    metrics = calculate_body_metrics(pose_data)
    classification = classify_body(metrics)
    recommendations = get_recommendations(classification["body_type"])

    return {
    "filename": file.filename,
    "message": "imagen válida",
    "metrics": metrics,
    "classification": classification,
    "recommendations": recommendations
}

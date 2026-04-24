from fastapi import APIRouter, UploadFile, File
from services.image_service import validate_image
from services.pose_service import detect_pose
from services.body_metrics import calculate_body_metrics
from services.body_classifier import classify_body
from services.recommendation_service import get_recommendations
from services.product_recommender import recommend_products
from services.pose_validator import validate_pose
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

    # VALIDACIÓN DE IMAGEN
    is_valid, result = validate_image(file_path)
    if not is_valid:
        os.remove(file_path)
        return {"error": result}

    # DETECCIÓN DE POSE
    pose_ok, pose_data = detect_pose(file_path)
    if not pose_ok:
        os.remove(file_path)
        return {"error": pose_data}

    # VALIDACIÓN DE POSE — con manejo defensivo
    try:
        pose_result = validate_pose(pose_data)
        if not isinstance(pose_result, (tuple, list)) or len(pose_result) != 2:
            os.remove(file_path)
            return {"error": "Error interno al validar la pose"}
        valid_pose, pose_msg = pose_result
    except (IndexError, KeyError) as e:
        os.remove(file_path)
        return {"error": f"Landmarks incompletos o con formato inesperado: {str(e)}"}

    if not valid_pose:
        os.remove(file_path)
        return {"error": pose_msg}

    # ANÁLISIS
    metrics = calculate_body_metrics(pose_data)
    classification = classify_body(metrics)
    recommendations = get_recommendations(classification["body_type"])
    products = recommend_products(classification["body_type"])

    return {
        "filename": file.filename,
        "message": "imagen válida",
        "metrics": metrics,
        "classification": classification,
        "recommendations": recommendations,
        "products": products,
        "landmarks": pose_data
    }
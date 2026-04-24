from fastapi import APIRouter, UploadFile, File
from services.image_service import validate_image

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

    return {
        "filename": file.filename,
        "message": "imagen válida",
        "info": result
    }
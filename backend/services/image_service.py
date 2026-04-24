import cv2
import numpy as np

def validate_image(file_path):
    img = cv2.imread(file_path)

    if img is None:
        return False, "No es una imagen válida"

    h, w = img.shape[:2]

    # Validación 1: resolución mínima
    if h < 720 or w < 400:
        return False, "Imagen muy pequeña"

    # Validación 2: orientación vertical
    if w > h:
        return False, "La imagen debe ser vertical"

    return True, {
        "width": w,
        "height": h
    }
from fastapi import FastAPI
from routes import upload, camera                      # ← agrega camera
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(camera.router)                      # ← agrega router

@app.get("/")
def home():
    return {"status": "API funcionando"}
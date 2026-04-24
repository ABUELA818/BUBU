from fastapi import FastAPI
from routes import upload
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.include_router(upload.router)

@app.get("/")
def home():
    return {"status": "API funcionando"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
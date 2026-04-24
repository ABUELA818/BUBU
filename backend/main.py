from fastapi import FastAPI
from routes import upload

app = FastAPI()

app.include_router(upload.router)

@app.get("/")
def home():
    return {"status": "API funcionando"}
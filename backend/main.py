from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from routes import upload

app = FastAPI()

# CORS debe agregarse ANTES de incluir routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Handler global para que los 500 no escapen del middleware CORS
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": f"Error interno: {str(exc)}"}
    )

app.include_router(upload.router)

@app.get("/")
def home():
    return {"status": "API funcionando"}
import os
import pathlib
import time
import warnings
from io import BytesIO
from typing import List

import torch
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, Security, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import APIKeyHeader
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field


if os.name == "nt":
    pathlib.PosixPath = pathlib.WindowsPath

warnings.filterwarnings("ignore", category=FutureWarning, message=".*torch.cuda.amp.autocast.*")

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(REPO_DIR, ".env"))

MODEL_PATH = os.environ.get("PROSTATE_MODEL_PATH", "runs/train/exp6/weights/best.pt")
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
BENIGN_LABELS = ("benign", "sog", "healthy", "normal")
API_KEY = os.environ.get("SINOMED_API_KEY")


def get_int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


MAX_UPLOAD_MB = get_int_env("SINOMED_MAX_UPLOAD_MB", 10)
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_IMAGE_PIXELS = get_int_env("SINOMED_MAX_IMAGE_PIXELS", 25000000)
ENABLE_DOCS = os.environ.get("SINOMED_ENABLE_DOCS", "true").lower() in {"1", "true", "yes", "on"}
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("SINOMED_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if origin.strip()
]
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class Detection(BaseModel):
    label: str = Field(..., examples=["grade3 (%)"])
    confidence: float = Field(..., ge=0, le=1, examples=[0.51])
    confidence_percent: int = Field(..., ge=0, le=100, examples=[51])
    box: List[float] = Field(..., min_length=4, max_length=4, examples=[[12.5, 18.0, 130.2, 144.8]])


class PredictionResponse(BaseModel):
    filename: str
    image_width: int
    image_height: int
    disease_probability_percent: int = Field(..., ge=0, le=100, examples=[50])
    conclusion: str = Field(..., examples=["Kasallik mavjudlik ehtimoli: taxminan 50%."])
    detections_count: int
    detections: List[Detection]
    inference_time_ms: int


class HealthResponse(BaseModel):
    status: str
    device: str
    classes: List[str]


def is_disease_label(label: str) -> bool:
    normalized = str(label).lower()
    return not any(word in normalized for word in BENIGN_LABELS)


def load_model():
    try:
        loaded_model = torch.hub.load(REPO_DIR, "custom", path=MODEL_PATH, source="local", device=DEVICE)
        loaded_model.conf = 0.25
        loaded_model.names = ["benign (%)", "grade3 (%)", "grade4 (%)", "grade5 (%)"]
        return loaded_model, None
    except Exception as exc:  # noqa: BLE001 - startup must stay alive and report degraded health.
        return None, str(exc)


model, model_load_error = load_model()

app = FastAPI(
    title="SinoMed AI Prostata API",
    description=(
        "Prostata gistologik tasvirini YOLOv5 modeli orqali tahlil qiladi. "
        "Rasm yuklanganda kasallik mavjudlik ehtimoli foizda va aniqlangan sohalar ro'yxati qaytadi."
    ),
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


async def require_api_key(x_api_key: str | None = Security(api_key_header)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yaroqsiz yoki mavjud bo'lmagan API kalit.")


async def read_limited_upload(file: UploadFile) -> bytes:
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Fayl hajmi {MAX_UPLOAD_MB} MB dan oshmasligi kerak.")
    return raw


def decode_image(raw: bytes) -> Image.Image:
    try:
        probe = Image.open(BytesIO(raw))
        probe.verify()
        image = Image.open(BytesIO(raw)).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="Rasm faylini o'qib bo'lmadi.") from exc

    if image.width * image.height > MAX_IMAGE_PIXELS:
        raise HTTPException(status_code=413, detail="Rasm o'lchami ruxsat etilgan limitdan katta.")

    return image


@app.get("/docs", include_in_schema=False, dependencies=[Depends(require_api_key)])
def custom_swagger_ui() -> HTMLResponse:
    if not ENABLE_DOCS:
        raise HTTPException(status_code=404, detail="Docs o'chirilgan.")

    return HTMLResponse(
        """
<!doctype html>
<html lang="uz">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>SinoMed AI Prostata API Docs</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
    <style>
      body { margin: 0; background: #f6f8fb; }
      .topbar { display: none; }
      .sinomed-header {
        background: #0f766e;
        color: white;
        font-family: Arial, sans-serif;
        padding: 18px 32px;
      }
      .sinomed-header h1 { margin: 0; font-size: 22px; }
      .sinomed-header p { margin: 6px 0 0; opacity: .9; }
      #swagger-ui { max-width: 1180px; margin: 0 auto; }
    </style>
  </head>
  <body>
    <div class="sinomed-header">
      <h1>SinoMed AI Prostata API</h1>
      <p>Prostata saratonini gistologik tasvir orqali tahlil qiluvchi AI microservice hujjatlari.</p>
    </div>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.ui = SwaggerUIBundle({
        url: "/openapi.json",
        dom_id: "#swagger-ui",
        deepLinking: true,
        persistAuthorization: true,
        displayRequestDuration: true,
        defaultModelsExpandDepth: -1,
        docExpansion: "none"
      });
    </script>
  </body>
</html>
        """,
        status_code=200,
    )


@app.get("/openapi.json", include_in_schema=False)
def custom_openapi_schema():
    if not ENABLE_DOCS:
        raise HTTPException(status_code=404, detail="OpenAPI schema o'chirilgan.")

    return app.openapi()


@app.get("/", response_model=HealthResponse, tags=["status"])
def root():
    return health()


@app.get("/health", response_model=HealthResponse, tags=["status"])
def health():
    class_names = []
    if model is not None:
        class_names = list(model.names) if isinstance(model.names, list) else list(model.names.values())

    return {
        "status": "ok" if model is not None else "degraded",
        "device": str(DEVICE),
        "classes": class_names,
    }


@app.post("/predict", response_model=PredictionResponse, tags=["prediction"], dependencies=[Depends(require_api_key)])
async def predict(file: UploadFile = File(..., description="Tahlil qilinadigan gistologik rasm")):
    if model is None:
        raise HTTPException(status_code=503, detail="Model yuklanmagan. Server sozlamalarini tekshiring.")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Faqat image/* turidagi fayl yuboring.")

    raw = await read_limited_upload(file)
    if not raw:
        raise HTTPException(status_code=400, detail="Fayl bo'sh.")

    image = decode_image(raw)

    started = time.perf_counter()
    try:
        results = model(image)
        predictions = results.pandas().xyxy[0]
    except Exception as exc:  # noqa: BLE001 - hide internal model details from API clients.
        raise HTTPException(status_code=500, detail="Model inference vaqtida xatolik yuz berdi.") from exc
    inference_time_ms = int((time.perf_counter() - started) * 1000)

    detections = []
    if not predictions.empty:
        for row in predictions.to_dict(orient="records"):
            confidence = float(row["confidence"])
            detections.append(
                {
                    "label": str(row["name"]),
                    "confidence": round(confidence, 4),
                    "confidence_percent": int(round(confidence * 100)),
                    "box": [
                        round(float(row["xmin"]), 2),
                        round(float(row["ymin"]), 2),
                        round(float(row["xmax"]), 2),
                        round(float(row["ymax"]), 2),
                    ],
                }
            )

    disease_detections = [d for d in detections if is_disease_label(d["label"])]
    disease_probability = 0
    if disease_detections:
        disease_probability = max(d["confidence_percent"] for d in disease_detections)

    if detections:
        conclusion = f"Kasallik mavjudlik ehtimoli: taxminan {disease_probability}%."
    else:
        conclusion = "Kasallik mavjudlik ehtimoli: taxminan 0%. Aniqlangan soha topilmadi."

    return {
        "filename": file.filename or "image",
        "image_width": image.width,
        "image_height": image.height,
        "disease_probability_percent": disease_probability,
        "conclusion": conclusion,
        "detections_count": len(detections),
        "detections": detections,
        "inference_time_ms": inference_time_ms,
    }

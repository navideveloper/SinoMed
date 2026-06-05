# SinoMed AI Prostata

SinoMed AI Prostata - prostata saratonini gistologik tasvirlar orqali aniqlash va tahlil qilish uchun tayyorlangan YOLOv5 asosidagi AI microservice. Loyiha rasm yuklanganda aniqlangan sohalarni qaytaradi va kasallik mavjudlik ehtimolini foiz ko'rinishida hisoblaydi.

> Muhim: bu dastur klinik qarorni almashtirmaydi. Natijalar shifokor/patolog xulosasi bilan birga ko'rib chiqilishi kerak.

## Tarkib

- `api.py` - FastAPI asosidagi himoyalangan REST microservice.
- `app.py` - Gradio orqali oddiy vizual interfeys.
- `train.py`, `train_2nd_day.py`, `detect.py`, `val.py` - YOLOv5 trening, validatsiya va inference skriptlari.
- `prostate.yaml` - prostata dataseti uchun YOLO klass konfiguratsiyasi.
- `models/`, `utils/`, `classify/`, `segment/` - YOLOv5 kod bazasi.
- `requirements.txt` - Python bog'liqliklari.

## Gitga kiritilmaydigan fayllar

Quyidagi fayllar lokal yoki og'ir artefakt hisoblanadi va push uchun kerak emas:

- `venv/`
- `.gradio/`
- `runs/`
- `datasetPCs/`
- `*.zip`
- `*.pt`, `*.pth`, `*.onnx`, `*.engine`, `*.tflite`
- `__pycache__/`

Model checkpointlari va datasetlar kerak bo'lsa serverga alohida joylashtiriladi.

## O'rnatish

```bash
cd ai-prostata
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

CUDA ishlatilsa, `torch` va `torchvision` versiyalarini qurilmaga moslab o'rnatish tavsiya qilinadi.

## Model fayli

API default holatda quyidagi modelni qidiradi:

```text
runs/train/exp6/weights/best.pt
```

Boshqa model ishlatish uchun `PROSTATE_MODEL_PATH` environment variable orqali yo'l bering:

```bash
set PROSTATE_MODEL_PATH=D:\models\sinomed-prostata-best.pt
uvicorn api:app --host 0.0.0.0 --port 8000
```

PowerShell:

```powershell
$env:PROSTATE_MODEL_PATH="D:\models\sinomed-prostata-best.pt"
uvicorn api:app --host 0.0.0.0 --port 8000
```

## API ishga tushirish

```bash
cd ai-prostata
uvicorn api:app --host 0.0.0.0 --port 8000
```

Endpointlar:

- `GET /health` - servis va model holatini tekshiradi.
- `POST /predict` - `image/*` fayl qabul qiladi va JSON natija qaytaradi.
- `GET /docs` - SinoMed UI template bilan tayyorlangan Swagger hujjatlari.

Misol:

```bash
curl -X POST http://127.0.0.1:8000/predict -H "X-API-Key: your-secret-key" -F "file=@sample.jpg"
```

## Xavfsizlik sozlamalari

Production muhitda quyidagi environment variablelarni sozlash tavsiya qilinadi:

```bash
set SINOMED_API_KEY=your-secret-key
set SINOMED_ALLOWED_ORIGINS=https://sinomed.uz,https://app.sinomed.uz
set SINOMED_MAX_UPLOAD_MB=10
set SINOMED_MAX_IMAGE_PIXELS=25000000
set SINOMED_ENABLE_DOCS=false
```

PowerShell:

```powershell
$env:SINOMED_API_KEY="your-secret-key"
$env:SINOMED_ALLOWED_ORIGINS="https://sinomed.uz,https://app.sinomed.uz"
$env:SINOMED_MAX_UPLOAD_MB="10"
$env:SINOMED_MAX_IMAGE_PIXELS="25000000"
$env:SINOMED_ENABLE_DOCS="false"
```

Xavfsizlik ishlari:

- `SINOMED_API_KEY` berilsa `/predict` va `/docs` endpointlari `X-API-Key` talab qiladi.
- CORS default holatda faqat lokal frontend manzillariga ruxsat beradi.
- Upload hajmi `SINOMED_MAX_UPLOAD_MB` bilan cheklanadi.
- Rasm formati `Pillow` orqali qayta tekshiriladi.
- Juda katta rasm o'lchamlari `SINOMED_MAX_IMAGE_PIXELS` orqali rad etiladi.
- Model yuklanmasa servis yiqilmaydi, `/health` `degraded` qaytaradi va `/predict` `503` beradi.
- Inference xatolari ichki tafsilotlarni tashqariga chiqarmasdan `500` javobga o'giriladi.
- Productionda `/docs`ni `SINOMED_ENABLE_DOCS=false` bilan o'chirish mumkin.

## Gradio interfeys

```bash
cd ai-prostata
python app.py
```

`app.py` hozir `runs/train/exp3/weights/best.pt` modelidan foydalanadi. Kerak bo'lsa model yo'lini fayl ichida moslang yoki API uchun `PROSTATE_MODEL_PATH` ishlating.

## Trening

Dataset `prostate.yaml` orqali belgilanadi:

```yaml
path: datasetPCs
train: images/train
val: images/val
nc: 4
names:
  0: benign
  1: grade3
  2: grade4
  3: grade5
```

Trening namunasi:

```bash
python train.py --img 640 --batch 16 --epochs 100 --data prostate.yaml --weights yolov5m.pt --name sinomed_prostata
```

Treningdan chiqqan natijalar `runs/` ichiga yoziladi va gitga qo'shilmaydi.

## Litsenziya

Loyiha YOLOv5 kod bazasiga tayangan. Ultralytics YOLOv5 AGPL-3.0 litsenziyasi ostida tarqatiladi; ichki Sinomed moslamalari va model artefaktlari alohida boshqariladi.

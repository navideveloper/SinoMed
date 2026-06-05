import gradio as gr
import torch
from PIL import Image
import os
import pathlib
import warnings

if os.name == "nt":
    pathlib.PosixPath = pathlib.WindowsPath

warnings.filterwarnings("ignore", category=FutureWarning, message=".*torch.cuda.amp.autocast.*")

# 1. Modelni yuklash
repo_dir = os.path.dirname(os.path.abspath(__file__))
model_path = 'runs/train/exp3/weights/best.pt'
model = torch.hub.load(repo_dir, 'custom', path=model_path, source='local')
print("Model yuklandi. Gradio ishga tushmoqda...")

BENIGN_LABELS = ("benign", "sog", "healthy", "normal")

def is_disease_label(label):
    label = str(label).lower()
    return not any(word in label for word in BENIGN_LABELS)

def predict(img):
    # Model rasmda aniqlash o'tkazadi
    results = model(img)
    
    # Natija chizilgan rasmni tayyorlash
    results.render()  
    output_img = Image.fromarray(results.ims[0])
    
    # Aniqlangan klasslar haqida ma'lumot olish
    predictions = results.pandas().xyxy[0]
    if predictions.empty:
        status = "Kasallik mavjudlik ehtimoli: taxminan 0%. Aniqlangan soha topilmadi."
    else:
        disease_predictions = predictions[predictions['name'].apply(is_disease_label)]
        disease_probability = 0 if disease_predictions.empty else int(round(disease_predictions['confidence'].max() * 100))
        counts = predictions['name'].value_counts().to_dict()
        areas = ", ".join([f"{v} ta {k}" for k, v in counts.items()])
        status = f"Kasallik mavjudlik ehtimoli: taxminan {disease_probability}%. Aniqlangan sohalar: {areas}"
    
    return output_img, status

# 2. Interfeys dizayni
demo = gr.Interface(
    fn=predict,
    inputs=gr.Image(type="pil", label="Prostata gistologik tasvirini yuklang"),
    outputs=[
        gr.Image(type="pil", label="Natija (YOLOv5m tahlili)"),
        gr.Textbox(label="Tashxis xulosasi")
    ],
    title="SinoMed AI Prostata",
    description="Prostata gistologik tasvirlarini YOLOv5 modeli yordamida tahlil qilish uchun Sinomed interfeysi.",
    theme="soft"
)

# 3. Ishga tushirish (Hech qanday if-shartisiz, qator boshidan yozilgan)
demo.launch(share=True)

# SinoMed AI Prostata bo'yicha ishlash tartibi

Bu repozitoriydagi asosiy maqsad - prostata gistologik tasvirlarini tahlil qiluvchi SinoMed servis kodini toza saqlash.

## Commitdan oldin

- `venv/`, `runs/`, `datasetPCs/`, zip arxivlar va model checkpointlarini commit qilmang.
- Maxfiy kalitlar, sertifikatlar va `.env` fayllarini gitga qo'shmang.
- API o'zgarishlaridan keyin kamida import/ishga tushish tekshiruvini bajaring.
- READMEdagi ishga tushirish buyruqlari koddagi real model yo'llari bilan mos bo'lishiga e'tibor bering.

## Kod uslubi

- Python fayllarida mavjud YOLOv5 tuzilmasini saqlang.
- Sinomedga tegishli servis logikasini `api.py`, `app.py`, `prostate.yaml` va zarur yordamchi modullarda aniq ajrating.
- Klinik matnlar ehtiyotkor yozilsin: model xulosasi tavsiya sifatida beriladi, yakuniy tashxis sifatida emas.

## Model va datasetlar

Model og'irliklari, datasetlar va trening natijalari gitdan tashqarida saqlanadi. Serverga chiqarishda kerakli `best.pt` faylini alohida yetkazib, `PROSTATE_MODEL_PATH` orqali ko'rsatish tavsiya qilinadi.

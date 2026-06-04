# SinoMed — Product Requirements Document (PRD)
> Version: 1.0 | Date: 2026-06-04 | Team: Fedora | Event: National AI Hackathon 2026, Andijon

---

## 1. Loyiha haqida

**SinoMed** — tibbiy AI yordamchi platforma. Shifokorlar va talabalar uchun X-ray tahlil, AI diagnoz taklifi va shifokor tasdig'i tizimi.

**Asosiy g'oya:** AI diagnoz qilmaydi — taklif qiladi. Shifokor tasdiqlaydi. Har bir qaror audit logda saqlanadi.

**Yo'nalish:** Hackathon #6 — Tibbiy ta'limda AI va xavfsizlik standarti.

---

## 2. Foydalanuvchi rollari

### 2.1 Student (Talaba)
- Universitetda o'qiyotgan tibbiyot talabalari
- Ro'yxatdan o'tishda university tanlaydi → org admin tasdiqlaydi
- X-ray yuklaydi, AI natijasini ko'radi (o'quv maqsadida)
- Balans kerak emas (subsidiyalangan)

### 2.2 Doctor (Shifokor)
- Kasalxonada ishlaydigan mutaxassislar
- Ro'yxatdan o'tishda hospital tanlaydi → org admin tasdiqlaydi
- X-ray yuklaydi, AI natijasini ko'radi, tasdiqlaydi/xato deb belgilaydi
- Balans tizimi bor (tarifga ko'ra)
- AI xato qilsa — `doctor_report` + `flagged_for_training=True`

### 2.3 Org Admin (Muassasa admini)
- Superadmin tomonidan yaratiladi (UI orqali)
- Yangi foydalanuvchi arizalarini tasdiqlaydi yoki rad etadi
- O'z muassasasi a'zolarini boshqaradi
- O'z muassasasi audit loglarini ko'radi
- 2 xil: University admin (talabalar uchun) | Hospital admin (shifokorlar uchun)

### 2.4 SuperAdmin (Tizim admini)
- Mutlaq huquq: barcha app, barcha user, barcha muassasa
- Org adminlarni yaratadi (UI: `/auth/users/create/`)
- Muassasalarni boshqaradi (Django admin orqali hozir)
- Balanslarni to'g'ridan-to'g'ri o'zgartiradi
- Barcha audit loglarni ko'radi

---

## 3. Asosiy funksiyalar

### 3.1 Registration & Approval Flow
```
Foydalanuvchi → 3-bosqich form:
  [1] Rol tanlash: Student / Doctor
  [2] Muassasa tanlash (AJAX, rol bo'yicha filter)
  [3] Ma'lumotlar: ism, username, tel, parol

→ Yaratiladi: is_active=False, approval_status=pending
→ Org admin dashboard da ko'rinadi
→ Admin: Tasdiqlash → is_active=True, approved
         Rad etish  → rejected + sabab
→ Login:  pending → "Kutilmoqda" xabari
          rejected → "Rad etildi" + sabab
```

### 3.2 AI Tahlil
```
Foydalanuvchi → model tanlaydi:
  - Suyak yoshi (qo'l rentgeni)    [bone_age]
  - Prostata saraton               [prostate]
  - O'pka yallig'lanishi           [pneumonia]

→ X-ray rasm yuklaydi
→ AJAX → api_analyze → AI FastAPI service
→ Natija: diagnosis, confidence %, Grad-CAM rasm
→ AnalysisLog yoziladi (har doim)
```

### 3.3 Shifokor Paneli
```
result_detail sahifasida:
  - AI natijasini ko'radi (diagnosis, confidence, GradCAM)
  - To'g'ri → tasdiqlaydi (doctor_confirmed=True)
  - Xato → "Xato deb belgilash" + izoh
    → doctor_verdict=False, flagged_for_training=True
    → AuditLog: DOCTOR_REPORT
```

### 3.4 Audit & Monitoring
```
AnalysisLog: har bir AI tahlil (confidence, raw output, shifokor verifikatsiyasi)
AuditLog:    tizim hodisalari (login, logout, register, payment)

Ko'rish huquqlari:
  superadmin → barcha loglar
  org_admin  → o'z muassasasi
  doctor     → o'z tahlillari
  student    → yo'q

Export: JSON, CSV, ZIP (rasm + annotations.json)
```

### 3.5 User Management (SuperAdmin UI)
```
/auth/users/          → ro'yxat (filter: rol, holat, approval_status)
/auth/users/create/   → yangi user (barcha field: rol, muassasa, balans, superuser)
/auth/users/<pk>/edit → tahrirlash (parol, rol, org, balans, approval)
/auth/users/<pk>/delete → o'chirish (hard delete, modal tasdig')
AJAX: toggle-active, update-balance
```

### 3.6 Org Admin Dashboard
```
/org/dashboard/:
  - Yangi arizalar → tasdiqlash/rad etish (AJAX + modal)
  - Stats: kutilmoqda, tasdiqlangan, rad etilgan, shifokorlar, talabalar
  - So'nggi tahlillar (o'z muassasasi)
  - Audit log (o'z muassasasi)
```

---

## 4. Muassasalar (Organizations)

**University (Oliy ta'lim):** Talabalar uchun
- ADTI — Andijon davlat tibbiyot instituti
- TTA — Toshkent tibbiyot akademiyasi
- SamDTU — Samarqand davlat tibbiyot universiteti

**Hospital (Kasalxona):** Shifokorlar uchun
- AVKTM — Andijon viloyat ko'p tarmoqli tibbiyot markazi
- RIJM — Respublika ixtisoslashtirilgan jarrohlik markazi
- TOSH-1 — Toshkent shahar 1-son shifoxonasi

*Yangi muassasalar: Django admin → Organizations → Add*

---

## 5. Billing / Tarif (hali to'liq emas)

| Tarif | Narx | Tahlillar | Foydalanuvchi |
|-------|------|-----------|--------------|
| Doctor Monthly | TBD | TBD/oy | Doctor |
| Doctor Yearly | TBD | TBD/yil | Doctor |
| University Yearly | TBD | TBD/yil | Muassasa |

*Hozir faqat model va admin bor. UI keyinchalik.*

---

## 6. Texnik arxitektura

```
[Browser]
    │
    ├── GET/POST → Django Views (DTL templates)
    └── AJAX JSON → Django API views
                        │
                        ├── SQLite DB (dev)
                        ├── Media files (X-ray rasmlar)
                        └── AI Service (FastAPI, port 8001)
                                └── PyTorch models
                                    ├── bone_age model
                                    ├── prostate model
                                    └── pneumonia model
```

**Stack:**
- Backend: Django 6.0.6, Python 3.13
- Frontend: Django Templates + Vanilla JS (AJAX), dark blue medical theme
- AI: FastAPI (Abdurasul Haydarov), PyTorch, Grad-CAM
- DB: SQLite (dev) → PostgreSQL (prod)
- Auth: Django session auth

---

## 7. AI Integratsiya (credentials kutilmoqda)

```python
# config/settings.py
AI_SERVICE_URL = os.getenv('AI_SERVICE_URL', 'http://localhost:8001')
AI_SERVICE_TIMEOUT = 30

# analysis/views.py — api_analyze
# Hozirgi endpoint: POST AI_SERVICE_URL/predict
# Payload: {model_type: "bone_age"|"prostate"|"pneumonia", image_path: "..."}
# Response: {diagnosis, confidence, diagnosis_type, gradcam_path}
```

Credentials kelgandan keyin:
1. `.env` ga `AI_SERVICE_URL=http://server:port` yozish
2. Agar har model alohida endpoint → `api_analyze` view ni update qilish
3. Auth token kerak bo'lsa → header ga qo'shish

---

## 8. Bajarilgan ishlar ✅ (2026-06-04)

- [x] Barcha Django models + migrations
- [x] Dark blue medical UI theme (base.html CSS variables)
- [x] Landing, upload, result, pricing, dashboard templates
- [x] Auth: login, 3-step register, logout, pending/rejected flow
- [x] Organizations app (University/Hospital), fixtures (6 org)
- [x] Org admin dashboard (approve/reject + modal)
- [x] AuditLog + AnalysisLog tizimi
- [x] Audit views: list, detail, export (JSON/CSV/ZIP)
- [x] SuperAdmin CRUD UI: create/edit/delete user
- [x] User management: list + filter + approval status
- [x] HANDOFF.md (har qanday LLM uchun)

---

## 9. Keyingi vazifalar 🔴

| Vazifa | Muhimlik | Bog'liqlik |
|--------|---------|-----------|
| `.env` fayl yaratish | 🔴 Yuqori | Server ishga tushishi uchun |
| AI credentials ulash | 🔴 Yuqori | Abdurasul serveri tayyor bo'lsa |
| Billing UI (org dashboard) | 🟡 O'rta | Plan/tarif tanlash |
| Organization CRUD UI | 🟡 O'rta | Hozir faqat Django admin orqali |
| Production deploy (VPS) | 🟡 O'rta | Hackathon demo uchun |
| PostgreSQL o'tish | 🟢 Past | Prod da kerak |

---

## 10. Jamoa

| Ism | Rol | Stack |
|-----|-----|-------|
| Oybek Muxtoraliyev | Frontend / UI-UX / PM | Django templates, CSS |
| Anvarov Oyatillo | Backend | Django, DB, audit |
| Abdurasul Haydarov | AI muhandisi | PyTorch, YOLO, Grad-CAM, FastAPI |
| Sharobidinov Qudratillo | Biznes / Taqdimot | Pitch, biznes model |

---

## 11. Muhim fayllar

```
HANDOFF.md                          ← Yangi LLM/ishchi uchun tez boshlanish
docs/PRD.md                         ← Bu fayl
docs/superpowers/specs/2026-06-04-audit-analysis-log-design.md
docs/superpowers/plans/2026-06-04-audit-analysis-log.md
organizations/fixtures/initial_organizations.json
```

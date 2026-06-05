# SinoMed — Project Handoff Document
> Yangi AI yoki ishchi uchun. Ish boshlashdan oldin **quyidagi tartibda** o'qi:

## 📚 O'qish tartibi (majburiy)
```
1. HANDOFF.md              ← bu fayl
2. docs/PRD.md             ← to'liq talablar, rollar, flow
3. memory/project_sinomed_hackathon.md  ← texnik holat, models, URLs
```
> memory/ : `C:\Users\Oybek\.claude\projects\C--Users-Oybek-Documents-Projects-programming-Telegram\memory\`

---

## Texnik ma'lumotlar

```bash
# Python — DOIM to'liq yo'l
C:\Python313\python.exe manage.py runserver 8002
C:\Python313\python.exe manage.py migrate
C:\Python313\python.exe manage.py check

# python.exe = Python 3.14 (paketlar yo'q) — ISHLATMA
# Branch: Oybek | git push origin Oybek
# QOIDA: commit da Co-Authored-By QO'YMA
```

---

## App struktura
```
accounts/       — User auth, 3-step register, approval flow, user CRUD
analysis/       — X-ray upload, AI call, result + doctor panel
audit/          — AuditLog + AnalysisLog
billing/        — Plan/Subscription/Payment + personal dashboard
organizations/  — Organization model + org admin dashboard
config/         — settings.py, urls.py
static/img/     — logo.png (yashil o'pka), logo-lungs.svg
templates/      — barcha HTML (DTL)
```

---

## Modellar
```python
# accounts
User: role(student|doctor|org_admin), organization(FK),
      approval_status(pending|approved|rejected), rejection_reason,
      phone, balance, is_active

# organizations
Organization: name, org_type(university|hospital), code, is_active
# 3 university + 3 hospital fixture yuklangan

# analysis
Analysis: user, model_type(bone_age|prostate|pneumonia), image, status
AnalysisResult: analysis(1:1), diagnosis, diagnosis_type(normal|warning|danger),
                confidence, note, gradcam_image, raw_output(JSON),
                doctor_confirmed, doctor_note, doctor_report, reviewed_by

# audit
AuditLog: user, action, ip_address, data(JSON), timestamp
AnalysisLog: analysis(1:1), ai_diagnosis, ai_confidence, ai_raw_output,
             error_type, doctor_verdict, flagged_for_training, institution

# billing
Plan, Subscription, Payment
```

---

## Rollar
| Rol | Dashboard | AI tahlil | Audit | User CRUD |
|-----|-----------|-----------|-------|-----------|
| superuser | `/dashboard/` | ✅ | ✅ to'liq | ✅ to'liq |
| org_admin | `/org/dashboard/` | ✅ | ✅ o'z org | ✅ cheklangan |
| doctor | `/dashboard/` | ✅ (tasdiqlash) | ❌ | ❌ |
| student | `/dashboard/` | ✅ (faqat ko'rish) | ❌ | ❌ |

---

## Registration flow
```
1. Rol tanlash (student/doctor)
2. Muassasa tanlash — AJAX: GET /auth/api/organizations/?role=...
3. Ma'lumotlar → submit
→ is_active=False, approval_status=pending
→ Org admin /org/dashboard/ da tasdiqlaydi/rad etadi
→ Login: pending → sariq xabar | rejected → qizil + sabab
```

---

## URL map
```
/                          landing
/scan/                     upload & analyze (3 model selectbox)
/analyze/<pk>/result/      natija + doctor panel + lightbox
/api/analyze/              AJAX POST → AI call

/auth/login/               login
/auth/register/            3-step registration
/auth/api/organizations/   AJAX org list
/auth/users/               user list (superadmin/org_admin)
/auth/users/create/        yangi user (superadmin)
/auth/users/<pk>/edit/     tahrirlash
/auth/users/<pk>/delete/   o'chirish

/org/dashboard/            org admin panel
/org/users/<pk>/approve/   tasdiqlash (POST)
/org/users/<pk>/reject/    rad etish (POST JSON {reason})

/dashboard/                shaxsiy kabinet
/audit/analyses/           AI tahlil loglari
/audit/log/                security audit (superuser)
/admin/                    Django admin
```

---

## AI Modellar — to'liq holat

> IP o'zgarganda: `.env` da `AI_SERVER_IP=yangi.ip` — boshqa hech narsa tegmaydi

```python
# config/settings.py
AI_SERVER_IP = os.getenv('AI_SERVER_IP', '10.49.158.145')
AI_ENDPOINTS = {
    'pneumonia': f'http://{AI_SERVER_IP}:8001/api/',
    'bone_age':  f'http://{AI_SERVER_IP}:8002/api/predict-bone-age',
    'prostate':  f'http://{AI_SERVER_IP}:8003/predict',
}
PROSTATE_API_KEY = os.getenv('PROSTATE_API_KEY', '')
AI_SERVICE_TIMEOUT = 30
```

| Model | Port | Param | Javob |
|-------|------|-------|-------|
| `pneumonia` | 8001 | `image` | `{status, probability, heatmap_image(base64)}` |
| `bone_age` | 8002 | `image` + `is_female` | `{formatlangan_yosh, jami_oylik, jinsi, yosh_yil}` |
| `prostate` | 8003 | **`file`** + `X-API-Key` | `{disease_probability_percent, conclusion, detections[]}` |

### Bone age — tug'ilgan sana taqqoslash
- UI da oy/yil kiritilsa → AI `jami_oylik` vs haqiqiy oylar → farq ko'rsatiladi
- `≤3 oy` 🎯 Juda aniq | `≤6` ✅ | `≤12` ⚠️ | `>12` ❌

### Prostate — detection drawing
- `_draw_prostate_detections()` — Pillow bilan box chizadi → `gradcam_image` ga saqlaydi
- grade3→ko'k, grade4→sariq, grade5→qizil
- `result.html`: annotated rasm + har detection `label + %`

### views.py arxitektura
```
_call_ai(model_type, image_path, extra_data)  — requests multipart POST
_parse_ai_response(model_type, ai_resp)        — har model uchun parser
_save_heatmap(result, b64)                     — base64 → media/gradcam/
_draw_prostate_detections(result, detections)  — Pillow box drawing
_result_to_dict(result)                        — JSON response (+ jami_oylik bone_age uchun)
```

---

## UI xususiyatlari
- **Lightbox**: barcha rasmlarga bosish → modal, zoom (+/-/wheel), drag, pinch (mobil), Esc/dblclick reset
  - ⚠️ Qoida: lightbox `<div id="lightbox">` `{% block content %}` **ichida** (endblock dan oldin) bo'lishi shart
  - Django template inheritance da blokdan tashqari HTML render bo'lmaydi → `getElementById` null qaytaradi
- **Ikonlar**: emoji yo'q — barcha UI elementlari **Font Awesome 6.4** (`fas fa-*`) ishlatadi
  - CDN: `base.html` `<head>` da `font-awesome/6.4.0/css/all.min.css`
  - `fa-graduation-cap` talaba | `fa-stethoscope` shifokor | `fa-university` muassasa | `fa-hospital` kasalxona
  - `fa-check` / `fa-times` tasdiqlash/rad | `fa-triangle-exclamation` ogohlantirish | `fa-clock` kutish
  - `fa-bullseye` / `fa-circle-check` / `fa-circle-xmark` bone age aniqligi (JS `innerHTML` orqali)
  - `fa-mars` / `fa-venus` jins radio tugmalar
- **Scan sahifasi**: model selectbox → bone_age tanlanganda tug'ilgan sana + jins fieldlari chiqadi
- **Logo**:
  - `static/img/logo-lungs.png` — faqat o'pka (navbar + auth sahifasida, yonida "SinoMed" text bor)
  - `static/img/logo.png` — ichida "SinoMed" text bor (mustaqil ko'rsatiladigan joylar uchun)
  - `.logo-mark` konteynerida oq background olib tashlangan — yangi logo o'z foniga ega
- **v1.0** badge — footer da

---

## Database
```
Engine: PostgreSQL 17.2, sinomed_db, localhost:5432
User: postgres
.env: DB_PASSWORD=1234 (lokal)
```

## .env (loyiha root da, gitga ketmaydi)
```env
AI_SERVER_IP=10.49.158.145
DB_NAME=sinomed_db
DB_USER=postgres
DB_PASSWORD=1234
DB_HOST=localhost
DB_PORT=5432
DEBUG=True
SECRET_KEY=django-insecure-sinomed-hackathon-2026-fedora-team
# PROSTATE_API_KEY=...
```

## Superuser
```
username: oybek | password: 123456
```

## CSS Variables (dark blue medical theme)
```css
--bg-dark:#0a0f1f  --bg-card:#121a2e  --bg-hover:#1a2541
--border-color:rgba(0,183,214,0.15)
--fg-primary:#e3f2fd  --fg-secondary:#90caf9  --fg-muted:#5d7fa3
--primary:#0077b6  --primary-light:#00b4d8  --accent:#00d4ff
```

---

## So'nggi bugfixlar va featurelar (2026-06-05)

### Bugfixlar
- **Rol "Talaba" superuser uchun** — `user_detail.html` + `users.html`: `is_superuser` tekshiruvi, oltin `badge-superuser` qo'shildi
- **Balans tugmasi overflow** — `balance-form` column direction, button 100% width
- **ROL dropdown duplikat** — `user_form.html`: hardcoded `<option org_admin>` olib tashlandi
- **Raw AI output** — `analysis_log_detail.html` dan olib tashlandi (DB + eksportda bor)
- **Balans JS error handling** — `user_detail.html`: success/error toast, `type="button"`, `toLocaleString('uz-UZ')`

### Yangi featurelar
- **Org Admin user yaratish** — `user_create_view`: org_admin o'z muassasasiga talaba/shifokor yarata oladi
  - Muassasa: lock (faqat o'z org), rol: faqat talaba/shifokor, auto-approved
  - Backend da POST validation ham bor (role abuse bloklangan)
- **Shaxsiy CSV eksport** — `/audit/export/my/` URL, barcha login bo'lgan userlar o'z tahlillarini yuklab oladi
  - Dashboard da "Oxirgi tahlillar" yonida `CSV yuklab olish` tugmasi
- **Shifokor ko'rish navbati** — `result_detail` view: shifokor o'z muassasasidagi BARCHA tahlillarni ko'ra oladi
  - Dashboard da "Ko'rilmagan tahlillar" kartasi (faqat shifokorga, pending_reviews)
  - `result.html` da bemor ismi ko'rinadi (shifokor boshqaning tahlilini ko'rganda)
  - Audit da "Ko'rilmagan" → shifokor tasdiqlasa/rad etsa → "Ko'rilgan" bo'ladi

### UI/UX
- **Theme toggle** — Chiqish tugmasi yoniga ko'chirildi (action buttons yonida)
- **Audit nav linki** — Shifokor uchun ham ko'rinadi (o'z tahlillari)
- **Export tugmalari** — Audit sahifasida faqat superuser/org_admin ko'radi
- **Emoji → Font Awesome 6.4** — 11 template, barcha ikonlar FA6

## Rollar va ruxsatlar (to'liq)

| URL | Talaba | Shifokor | Org Admin | SuperAdmin |
|-----|--------|----------|-----------|------------|
| `/auth/users/` | redirect | redirect | o'z org | hammasi |
| `/auth/users/create/` | redirect | redirect | o'z org (talaba/shifokor) | hammasi |
| `/audit/analyses/` | 403 | o'z tahlillari | o'z org | hammasi |
| `/audit/export/my/` | o'z CSV | o'z CSV | o'z CSV | o'z CSV |
| `/audit/export/json/` | 403 | 403 | o'z org | hammasi |
| `/analyze/<pk>/result/` | faqat o'zi | **o'z org hammasi** | faqat o'zi | hammasi |

## Keyingi vazifalar
1. **Production deploy** — VPS, Nginx, PostgreSQL prod
2. **Prostate API key** — agar kerak bo'lsa `.env` ga `PROSTATE_API_KEY=...`
3. **Payment/plan UI** — org admin dashboard da

## Barcha docs
```
HANDOFF.md                 ← bu fayl
README.md                  ← o'zbek tilida, taqdimot PDF linki bilan
docs/PRD.md                ← product requirements
taqdimot/taqdimot.pdf      ← loyiha taqdimoti (GitHub da ko'rish mumkin)
taqdimot/taqdimot.pptx     ← taqdimot manba fayli
organizations/fixtures/initial_organizations.json
```

---
*Last updated: 2026-06-05 | Branch: Oybek | feat: doctor review queue + balance fix*

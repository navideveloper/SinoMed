# SinoMed — Project Handoff Document
> Bu fayl yangi AI yoki ishchi uchun loyihani tez tushunib olish uchun yozilgan.
> **Ish boshlashdan oldin QUYIDAGI TARTIBDA o'qi:**

---

## 📚 O'qish tartibi (majburiy)

Yangi sessiya yoki yangi LLM boshlanganda — bu fayllarni quyidagi tartibda o'qi:

```
1. HANDOFF.md              ← bu fayl (hozir o'qiyapsan)
2. docs/PRD.md             ← to'liq product requirements, rollar, flow, backlog
3. memory/project_sinomed_hackathon.md  ← texnik holat, models, URLs, templates
```

> `memory/` papkasi: `C:\Users\Oybek\.claude\projects\C--Users-Oybek-Documents-Projects-programming-Telegram\memory\`

Uch faylni o'qigandan so'ng loyiha to'liq tushuniladi — qo'shimcha savol berma.

---

## Loyiha haqida
**SinoMed** — tibbiy AI platforma (National AI Hackathon 2026, Andijon, Fedora jamoasi).
- AI tahlil qiladi → shifokor tasdiqlaydi → audit log saqlanadi
- 3 ta model: suyak yoshi (qo'l rentgeni), prostata saraton, o'pka yallig'lanishi

---

## Muhim texnik ma'lumotlar

```bash
# Python — DOIM to'liq yo'l bilan
C:\Python313\python.exe manage.py runserver 8002
C:\Python313\python.exe manage.py migrate
C:\Python313\python.exe manage.py check

# python.exe = Python 3.14 (paketlar yo'q) — ISHLATMA

# Branch
git checkout Oybek   # barcha ish shu yerda
git push origin Oybek

# QOIDA: commit message ga "Co-Authored-By" yoki AI belgisi QO'YMA
```

---

## App struktura

```
sinomed/
├── accounts/       # User auth, registration, user management CRUD
├── analysis/       # X-ray upload, AI call, result view
├── audit/          # AuditLog (security) + AnalysisLog (AI results)
├── billing/        # Plan/Subscription/Payment + personal dashboard
├── organizations/  # Organization model + org admin dashboard
├── config/         # settings.py, urls.py
├── static/
│   └── img/
│       ├── logo.png        ← asosiy logo (yashil o'pka, oq fon)
│       └── logo-lungs.svg  ← fallback SVG
└── templates/      # Barcha HTML (DTL)
```

---

## Modellar (soddalashtirilgan)

```python
# accounts
User: username, role(student|doctor|org_admin), organization(FK),
      approval_status(pending|approved|rejected), rejection_reason,
      phone, balance, institution(legacy), is_active

# organizations
Organization: name, org_type(university|hospital), code, is_active
# Fixture: 3 university + 3 hospital (loaded)

# analysis
Analysis: user, model_type(bone_age|prostate|pneumonia), image, status
AnalysisResult: analysis(1:1), diagnosis, diagnosis_type, confidence,
                gradcam_image, raw_output, doctor_confirmed, doctor_note

# audit
AuditLog: user, action, ip_address, data(JSON), timestamp
AnalysisLog: analysis(1:1), ai_diagnosis, ai_confidence, ai_raw_output,
             error_type, doctor_verdict, flagged_for_training, institution

# billing
Plan, Subscription, Payment
```

---

## Rollar va ko'rinish

| Rol | Dashboard | Audit | Org Admin | User CRUD |
|-----|-----------|-------|-----------|-----------|
| superuser | `/dashboard/` | ✅ to'liq | ✅ barcha org | ✅ to'liq |
| org_admin | `/org/dashboard/` | ✅ o'z org | ✅ o'z org | ✅ cheklangan |
| doctor | `/dashboard/` | ❌ | ❌ | ❌ |
| student | `/dashboard/` | ❌ | ❌ | ❌ |

---

## Registration flow
```
1. Rol tanlash (student/doctor)
2. Muassasa tanlash — AJAX: GET /auth/api/organizations/?role=student
3. Ma'lumotlar → submit
→ User yaratiladi: is_active=False, approval_status=pending
→ Org admin /org/dashboard/ da ko'radi → Tasdiqlaydi/Rad etadi
→ Tasdiqlangach user login qila oladi
```

---

## URL map (asosiy)
```
/                          landing
/scan/                     upload & analyze
/result/<pk>/              natija + doctor panel
/api/analyze/              AJAX POST → AI call

/auth/login/               login (pending/rejected xabarlari bor)
/auth/register/            3-step registration
/auth/api/organizations/   AJAX org list
/auth/users/               user list (admin/org_admin)
/auth/users/create/        yangi user (superadmin)
/auth/users/<pk>/edit/     tahrirlash
/auth/users/<pk>/delete/   o'chirish (POST)

/org/dashboard/            org admin panel
/org/users/<pk>/approve/   tasdiqlash (POST)
/org/users/<pk>/reject/    rad etish (POST JSON {reason})

/dashboard/                shaxsiy kabinet
/audit/analyses/           AI tahlil loglari
/audit/log/                security audit (superuser)

/admin/                    Django admin
```

---

## AI Service integratsiya

### AI modellari — to'liq holat (2026-06-05)

| Model | Server | Port | Holat |
|-------|--------|------|-------|
| `pneumonia` | `172.20.10.4` | `8001` | ✅ Ulangan |
| `bone_age`  | `172.20.10.4` | `8002` | ✅ Ulangan |
| `prostate`  | `172.20.10.4` | `8003` | ✅ Ulangan |

> Bitta tarmoqda bo'lish shart (Wi-Fi/kabel).

### API formatlar

```
# Pnevmoniya — POST http://172.20.10.4:8001/api/
param: image (file)
javob: {status, probability, heatmap_image (base64)}

# Bone Age — POST http://172.20.10.4:8002/api/predict-bone-age
params: image (file) + is_female (text, ixtiyoriy)
javob:  {formatlangan_yosh, jami_oylik, jinsi, yosh_yil}
UI: tug'ilgan oy/yil kiritilsa → AI oylar vs haqiqiy oylar taqqoslanadi

# Prostate — POST http://172.20.10.4:8003/predict
param: file (file) — NB: "file", "image" emas!
header: X-API-Key (ixtiyoriy, .env: PROSTATE_API_KEY)
javob: {disease_probability_percent, conclusion, detections_count, detections[]}
```

### settings.py
```python
AI_ENDPOINTS = {
    'pneumonia': os.getenv('PNEUMONIA_AI_URL', 'http://172.20.10.4:8001/api/'),
    'bone_age':  os.getenv('BONE_AGE_AI_URL',  'http://172.20.10.4:8002/api/predict-bone-age'),
    'prostate':  os.getenv('PROSTATE_AI_URL',  'http://172.20.10.4:8003/predict'),
}
PROSTATE_API_KEY = os.getenv('PROSTATE_API_KEY', '')
AI_SERVICE_TIMEOUT = 30
```

### IP o'zgarsa — .env ga yozing:
```env
PNEUMONIA_AI_URL=http://yangi-ip:8001/api/
BONE_AGE_AI_URL=http://yangi-ip:8002/api/predict-bone-age
PROSTATE_AI_URL=http://yangi-ip:8003/predict
PROSTATE_API_KEY=secret-key-value
```

---

## Database
- **Engine**: PostgreSQL 17.2 (local: `localhost:5432`)
- **DB name**: `sinomed_db`
- **User**: `postgres` / **Password**: env orqali (`DB_PASSWORD`)
- `settings.py` DATABASES `os.getenv()` bilan — prod da `.env` orqali o'zgartiriladi
- SQLite (`db.sqlite3`) + `db_backup.json` → `.gitignore` da, GitHubga ketmaydi

## .env (hali yo'q, yaratish kerak)
```env
SECRET_KEY=django-insecure-...
AI_SERVICE_URL=http://server-ip:8001
DEBUG=True
DB_PASSWORD=1234
```

---

## Superuser
```
username: oybek
password: 123456
```

---

## CSS Variables (dark blue medical theme)
```css
--bg-dark: #0a0f1f
--bg-card: #121a2e
--bg-hover: #1a2541
--border-color: rgba(0,183,214,0.15)
--fg-primary: #e3f2fd
--fg-secondary: #90caf9
--fg-muted: #5d7fa3
--primary: #0077b6
--primary-light: #00b4d8
--accent: #00d4ff
```

---

## Logo
- **Asosiy PNG**: `static/img/logo.png` — yashil o'pka, oq fon
- **Fallback SVG**: `static/img/logo-lungs.svg`
- **Navbar** (`base.html`): `.logo-mark 2.55rem` → `<img logo.png>`, matn yashil gradient `#34d399 → #0d9488`
- **Auth** (`accounts/auth.html`): `.logo-mark` → `<img logo.png>`
- Logo oq fondagi PNG — navbar da `background: #fff; padding: 2px` konteynerda ko'rsatiladi
- `"v1.0"` badge navbar dan footer ga ko'chirildi

---

## Keyingi vazifalar
1. `.env` fayl yaratish (SECRET_KEY + AI_SERVICE_URL)
2. AI credentials kelganda `analysis/views.py` → `api_analyze` ni ulash
3. Payment/plan UI (org admin dashboard da)
4. Production deploy (VPS, Nginx)

---

## Barcha docs

```
HANDOFF.md                                              ← bu fayl
docs/PRD.md                                             ← product requirements
docs/superpowers/specs/2026-06-04-audit-analysis-log-design.md
docs/superpowers/plans/2026-06-04-audit-analysis-log.md
organizations/fixtures/initial_organizations.json       ← 6 ta org seed data
```

---

*Last updated: 2026-06-05 | Branch: Oybek | Last commit: see git log*

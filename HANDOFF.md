# SinoMed — Project Handoff Document
> Bu fayl yangi AI yoki ishchi uchun loyihani tez tushunib olish uchun yozilgan.
> Har doim ish boshlashdan oldin bu faylni o'qi.

---

## Loyiha haqida
**SinoMed** — tibbiy AI platforma (National AI Hackathon 2026, Andijon, Fedora jamoasi).
- AI tahlil qiladi → shifokor tasdiqlaydi → audit log saqlanadi
- 3 ta model: suyak yoshi (qo'l rentgeni), prostata saraton, o'pka yallig'lanishi

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

## App struktura

```
sinomed/
├── accounts/       # User auth, registration, user management CRUD
├── analysis/       # X-ray upload, AI call, result view
├── audit/          # AuditLog (security) + AnalysisLog (AI results)
├── billing/        # Plan/Subscription/Payment + personal dashboard
├── organizations/  # Organization model + org admin dashboard
├── config/         # settings.py, urls.py
└── templates/      # Barcha HTML (DTL)
```

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

## Rollar va ko'rinish

| Rol | Dashboard | Audit | Org Admin | User CRUD |
|-----|-----------|-------|-----------|-----------|
| superuser | `/dashboard/` | ✅ to'liq | ✅ barcha org | ✅ to'liq |
| org_admin | `/org/dashboard/` | ✅ o'z org | ✅ o'z org | ✅ cheklangan |
| doctor | `/dashboard/` | ❌ | ❌ | ❌ |
| student | `/dashboard/` | ❌ | ❌ | ❌ |

## Registration flow
```
1. Rol tanlash (student/doctor)
2. Muassasa tanlash — AJAX: GET /auth/api/organizations/?role=student
3. Ma'lumotlar → submit
→ User yaratiladi: is_active=False, approval_status=pending
→ Org admin /org/dashboard/ da ko'radi → Tasdiqlaydi/Rad etadi
→ Tasdiqlangach user login qila oladi
```

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

## AI Service integratsiya
```python
# config/settings.py
AI_SERVICE_URL = os.getenv('AI_SERVICE_URL', 'http://localhost:8001')

# analysis/views.py — api_analyze view
# POST: AI_SERVICE_URL/predict
# Payload: {model_type, image_path}
# Credentials .env ga yoziladi — hali kelmagan (2026-06-04)
```

## .env (hali yo'q, yaratish kerak)
```env
SECRET_KEY=django-insecure-...
AI_SERVICE_URL=http://server-ip:8001
DEBUG=True
```

## Superuser
```
username: oybek
password: 123456
```

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

## Keyingi vazifalar
1. `.env` fayl yaratish (SECRET_KEY + AI_SERVICE_URL)
2. AI credentials kelganda `analysis/views.py` → `api_analyze` ni ulash
3. Payment/plan UI (org admin dashboard da)
4. Production deploy (VPS, Nginx)

## Docs
```
docs/superpowers/specs/2026-06-04-audit-analysis-log-design.md
docs/superpowers/plans/2026-06-04-audit-analysis-log.md
```

---
*Last updated: 2026-06-04 | Branch: Oybek | Commits: f75943a*

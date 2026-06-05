<div align="center">

<img src="static/img/logo-lungs.png" alt="SinoMed Logo" width="100" height="100"/>

# SinoMed

**AI-powered Medical Imaging & Diagnosis Platform**

*National AI Hackathon 2026 · Andijon viloyati · Fedora jamoasi*

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-6.0.6-092E20?logo=django&logoColor=white)](https://djangoproject.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17.2-336791?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Branch](https://img.shields.io/badge/branch-Oybek-blue?logo=git&logoColor=white)](.)
[![License](https://img.shields.io/badge/license-MIT-green)](.)

</div>

---

## Overview

SinoMed is a full-stack clinical AI platform that enables **medical institutions** to upload radiological images and receive instant AI-generated diagnoses across three specialties. Doctors can review, confirm, or flag AI results — creating a feedback loop for continuous model improvement. All activity is audit-logged for compliance and training data collection.

Built for the **National AI Hackathon 2026** under time constraints, production-ready in architecture.

---

## Features

| Module | Capability |
|--------|-----------|
| **AI Analysis** | Pneumonia (chest X-ray), Bone Age (hand X-ray), Prostate Cancer (histology) |
| **Doctor Panel** | Confirm AI result or report error with notes |
| **Org Admin Dashboard** | Approve / reject user registrations from own institution |
| **Audit & Logs** | Full security audit log + per-analysis AI log with export (JSON / CSV / ZIP) |
| **Lightbox Viewer** | Click-to-zoom image modal — zoom, drag, pinch, Esc / double-click reset |
| **Billing** | Plan / Subscription / Payment models (UI in progress) |
| **3-Step Registration** | Role → Institution → Credentials flow, no auto-login |
| **Role-Based Access** | `superuser`, `org_admin`, `doctor`, `student` — granular per-page |

---

## Tech Stack

```
Backend       Django 6.0.6 · Python 3.13
Database      PostgreSQL 17.2
Image proc.   Pillow 11.3.0  (prostate bounding-box drawing)
AI calls      requests       (multipart/form-data POST to FastAPI microservices)
Frontend      Vanilla JS · CSS variables · Font Awesome 6.4.0
Templates     Django Template Language (DTL)
Env           python-dotenv
```

---

## AI Models

Three independent microservices — only `AI_SERVER_IP` in `.env` needs changing if the server moves.

| Model | Port | Input param | Response |
|-------|------|-------------|----------|
| `pneumonia` | `8001` | `image` | `{ status, probability, heatmap_image (base64) }` |
| `bone_age` | `8002` | `image`, `is_female` | `{ formatlangan_yosh, jami_oylik, jinsi, yosh_yil }` |
| `prostate` | `8003` | **`file`**, `X-API-Key` | `{ disease_probability_percent, conclusion, detections[] }` |

**Prostate detection** — YOLOv5-based; bounding boxes drawn server-side with Pillow:
- `grade3` blue · `grade4` yellow · `grade5` red

**Bone age accuracy** — compares AI months vs actual age entered by user:

| Difference | Rating |
|-----------|--------|
| <= 3 months | Very accurate |
| <= 6 months | Good |
| <= 12 months | Average |
| > 12 months | Large gap |

---

## Project Structure

```
SinoMed/
├── accounts/          # User model, 3-step registration, approval flow, user CRUD
├── analysis/          # Upload, AI call, result page, doctor review panel
├── audit/             # AuditLog (security) + AnalysisLog (AI feedback)
├── billing/           # Plan / Subscription / Payment
├── organizations/     # Organization model, org admin dashboard
├── config/            # settings.py, urls.py
├── templates/         # All HTML (DTL), dark blue medical theme
├── static/
│   └── img/
│       ├── logo-lungs.png   # Lung-only logo (used beside "SinoMed" text)
│       └── logo.png         # Logo with built-in text (standalone use)
├── media/             # Uploaded X-rays, gradcam heatmaps
├── docs/              # PRD, design specs
├── HANDOFF.md         # Developer onboarding guide
└── requirements.txt
```

---

## Roles & Permissions

| Role | Dashboard | AI Analysis | Doctor Panel | Audit | User CRUD |
|------|-----------|-------------|--------------|-------|-----------|
| `superuser` | `/dashboard/` | All models | View only | Full | Full |
| `org_admin` | `/org/dashboard/` | All models | View only | Own org | Own org members |
| `doctor` | `/dashboard/` | All models | Confirm / flag | - | - |
| `student` | `/dashboard/` | All models | View only | - | - |

---

## Installation

### 1. Clone & create virtual environment

```bash
git clone https://github.com/navideveloper/SinoMed.git
cd SinoMed
git checkout Oybek

# Windows
C:\Python313\python.exe -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3.13 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Create `.env` in the project root (never commit this file):

```env
AI_SERVER_IP=10.49.158.145
DB_NAME=sinomed_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DEBUG=True
SECRET_KEY=your-secret-key-here
# PROSTATE_API_KEY=your_key_if_required
```

### 4. Database setup

```bash
# Create the database first
psql -U postgres -c "CREATE DATABASE sinomed_db;"

# Run migrations
python manage.py migrate

# Load institution fixtures (6 orgs: 3 university + 3 hospital)
python manage.py loaddata organizations/fixtures/initial_organizations.json

# Create superuser
python manage.py createsuperuser
```

### 5. Run

```bash
python manage.py runserver 8002
```

Open [http://localhost:8002](http://localhost:8002)

> **Windows note:** use `C:\Python313\python.exe` — `python.exe` may point to Python 3.14 which lacks installed packages.

---

## URL Map

```
/                          Landing page
/scan/                     Upload & analyze (select model)
/analyze/<pk>/result/      Result detail + doctor review panel
/api/analyze/              AJAX POST -> AI call (JSON response)
/pricing/                  Pricing page

/auth/login/               Login
/auth/register/            3-step registration
/auth/logout/              Logout
/auth/api/organizations/   AJAX org list (used in registration)
/auth/users/               User list (superuser / org_admin)
/auth/users/create/        Create user (superuser)
/auth/users/<pk>/edit/     Edit user
/auth/users/<pk>/delete/   Delete user

/org/dashboard/            Org admin panel
/org/users/<pk>/approve/   Approve user (POST)
/org/users/<pk>/reject/    Reject user (POST JSON)

/dashboard/                Personal cabinet
/audit/analyses/           AI analysis log (filterable, exportable)
/audit/log/                Security audit log (superuser only)
/admin/                    Django admin
```

---

## Registration Flow

```
Step 1  Role selection       (student / doctor)
Step 2  Institution select   (AJAX filtered by role)
Step 3  Personal details     submit

  -> Account created: is_active=False, approval_status=pending
  -> Org admin reviews at /org/dashboard/
  -> Approve  user can log in
  -> Reject   user sees rejection reason at login screen
```

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_SERVER_IP` | `10.49.158.145` | IP of the AI microservices server |
| `DB_NAME` | - | PostgreSQL database name |
| `DB_USER` | - | PostgreSQL username |
| `DB_PASSWORD` | - | PostgreSQL password |
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DEBUG` | `True` | Set `False` in production |
| `SECRET_KEY` | - | Django secret key (min 50 chars) |
| `PROSTATE_API_KEY` | *(optional)* | API key for prostate model if required |

> **Changing AI server:** update only `AI_SERVER_IP` — all three endpoint URLs are derived from it automatically.

---

## CSS Design System

Dark blue medical theme — CSS variables in `base.html`:

```css
--bg-dark:      #0a0f1f   /* page background  */
--bg-card:      #121a2e   /* card background  */
--bg-hover:     #1a2541   /* hover state      */
--border-color: rgba(0,183,214,0.15)
--fg-primary:   #e3f2fd   /* primary text     */
--fg-secondary: #90caf9   /* secondary text   */
--fg-muted:     #5d7fa3   /* muted / labels   */
--primary:      #0077b6
--primary-light:#00b4d8
--accent:       #00d4ff
```

Icons: **Font Awesome 6.4.0** (`fas fa-*`) — CDN loaded in `base.html <head>`.

---

## Developer Notes

- **Lightbox:** `<div id="lightbox">` must be **inside** `{% block content %}` — Django template inheritance silently discards HTML outside blocks.
- **Logo logic:** `logo-lungs.png` (lung only) where "SinoMed" text is shown beside it; `logo.png` (with built-in text) for standalone use.
- **Prostate API param** is `file` — all other models use `image`.
- **Soft-delete:** not implemented; use Django admin or superuser CRUD for deletions.

For detailed technical state, model internals, and developer onboarding see [HANDOFF.md](HANDOFF.md).

---

## Team

**Fedora jamoasi** — National AI Hackathon 2026, Andijon viloyati

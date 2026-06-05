<div align="center">

<img src="static/img/logo-lungs.png" alt="SinoMed Logo" width="100" height="100"/>

# SinoMed

**Sun'iy intellekt asosida tibbiy tasvirlarni tahlil qilish platformasi**

*National AI Hackathon 2026 · Andijon viloyati · Fedora jamoasi*

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-6.0.6-092E20?logo=django&logoColor=white)](https://djangoproject.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17.2-336791?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Branch](https://img.shields.io/badge/branch-Oybek-blue?logo=git&logoColor=white)](.)
[![License](https://img.shields.io/badge/license-MIT-green)](.)

<br/>

### <a href="taqdimot/taqdimot.pdf" target="_blank">📄 Loyiha taqdimotini ko'rish (PDF)</a>

</div>

---

## Umumiy tavsif

SinoMed — tibbiy muassasalarga rentgen va gistologik tasvirlarni yuklash hamda uch yo'nalish bo'yicha AI tashxisini bir zumda olish imkonini beruvchi to'liq full-stack platforma. Shifokorlar AI natijalarini tasdiqlash yoki xato sifatida belgilash orqali modelni uzluksiz takomillashtirishga hissa qo'shadi. Barcha faoliyat muvofiqlik va trening ma'lumotlar to'plash maqsadida audit jurnalida saqlanadi.

**National AI Hackathon 2026** uchun qisqa muddatda ishlab chiqilgan — arxitektura jihatidan production-ready.

---

## Funksiyalar

| Modul | Imkoniyat |
|-------|-----------|
| **AI Tahlil** | Pnevmoniya (ko'krak rentgeni), Suyak yoshi (qo'l rentgeni), Prostata saratoni (gistologiya) |
| **Shifokor paneli** | AI natijasini tasdiqlash yoki izoh bilan xato sifatida qaytarish |
| **Muassasa admin paneli** | O'z muassasasi foydalanuvchilarini tasdiqlash / rad etish |
| **Audit va jurnallar** | To'liq xavfsizlik jurnali + AI tahlil logi (JSON / CSV / ZIP eksport) |
| **Lightbox ko'rinish** | Rasmni kattalashtirish modali — zoom, drag, pinch, Esc / ikki marta bosish |
| **Billing** | Tarif / Obuna / To'lov modellari (UI ishlanmoqda) |
| **3 bosqichli ro'yxatdan o'tish** | Rol → Muassasa → Ma'lumotlar oqimi, avtomatik kirishsiz |
| **Rol asosidagi ruxsat** | `superuser`, `org_admin`, `doctor`, `student` — sahifa darajasida boshqaruv |

---

## Texnologiyalar

```
Backend       Django 6.0.6 · Python 3.13
Ma'lumotlar   PostgreSQL 17.2
Tasvir        Pillow 11.3.0  (prostata aniqlash chegaralarini chizish)
AI so'rovlar  requests       (multipart/form-data POST → FastAPI mikroservislar)
Frontend      Vanilla JS · CSS o'zgaruvchilar · Font Awesome 6.4.0
Shablonlar    Django Template Language (DTL)
Muhit         python-dotenv
```

---

## AI Modellar

Uchta mustaqil mikroservis — server o'zgarganda faqat `.env` dagi `AI_SERVER_IP` yangilanadi.

| Model | Port | Parametr | Javob |
|-------|------|----------|-------|
| `pneumonia` | `8001` | `image` | `{ status, probability, heatmap_image (base64) }` |
| `bone_age` | `8002` | `image`, `is_female` | `{ formatlangan_yosh, jami_oylik, jinsi, yosh_yil }` |
| `prostate` | `8003` | **`file`**, `X-API-Key` | `{ disease_probability_percent, conclusion, detections[] }` |

**Prostata aniqlash** — YOLOv5 asosida; chegaralar Pillow orqali server tomonida chiziladi:
- `grade3` ko'k · `grade4` sariq · `grade5` qizil

**Suyak yoshi aniqligi** — AI hisoblagani bilan foydalanuvchi kiritgan haqiqiy yosh taqqoslanadi:

| Farq | Baho |
|------|------|
| <= 3 oy | Juda aniq |
| <= 6 oy | Yaxshi |
| <= 12 oy | O'rtacha |
| > 12 oy | Katta farq |

---

## Loyiha tuzilmasi

```
SinoMed/
├── accounts/          # Foydalanuvchi modeli, 3 bosqichli ro'yxat, tasdiqlash oqimi, CRUD
├── analysis/          # Yuklash, AI so'rov, natija sahifasi, shifokor paneli
├── audit/             # AuditLog (xavfsizlik) + AnalysisLog (AI fikr-mulohaza)
├── billing/           # Tarif / Obuna / To'lov
├── organizations/     # Muassasa modeli, muassasa admin paneli
├── config/            # settings.py, urls.py
├── templates/         # Barcha HTML (DTL), to'q ko'k tibbiy mavzu
├── static/
│   └── img/
│       ├── logo-lungs.png   # Faqat o'pka logosi ("SinoMed" text yonida)
│       └── logo.png         # Ichida text bor logo (mustaqil foydalanish uchun)
├── media/             # Yuklangan rentgenlar, gradcam issiqlik xaritalari
├── taqdimot/          # Loyiha taqdimoti (PDF, PPTX)
├── docs/              # PRD, dizayn spesifikatsiyalari
├── HANDOFF.md         # Ishlab chiquvchi uchun qo'llanma
└── requirements.txt
```

---

## Rollar va Ruxsatlar

| Rol | Dashboard | AI Tahlil | Shifokor paneli | Audit | Foydalanuvchi CRUD |
|-----|-----------|-----------|-----------------|-------|--------------------|
| `superuser` | `/dashboard/` | Barcha | Ko'rish | To'liq | To'liq |
| `org_admin` | `/org/dashboard/` | Barcha | Ko'rish | O'z muassasasi | O'z a'zolari |
| `doctor` | `/dashboard/` | Barcha | Tasdiqlash / Xato | - | - |
| `student` | `/dashboard/` | Barcha | Ko'rish | - | - |

---

## O'rnatish

### 1. Klonlash va virtual muhit

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

### 2. Kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

### 3. Muhit sozlash

Loyiha ildizida `.env` fayl yarating (hech qachon git ga yuklamang):

```env
AI_SERVER_IP=10.49.158.145
DB_NAME=sinomed_db
DB_USER=postgres
DB_PASSWORD=parolingiz
DB_HOST=localhost
DB_PORT=5432
DEBUG=True
SECRET_KEY=uzun-va-murakkab-kalit
# PROSTATE_API_KEY=kerak_bolsa_kiriting
```

### 4. Ma'lumotlar bazasini sozlash

```bash
# Avval bazani yarating
psql -U postgres -c "CREATE DATABASE sinomed_db;"

# Migratsiyalarni ishga tushiring
python manage.py migrate

# Muassasalar fixturasini yuklang (3 universitet + 3 kasalxona)
python manage.py loaddata organizations/fixtures/initial_organizations.json

# Superuser yarating
python manage.py createsuperuser
```

### 5. Ishga tushirish

```bash
python manage.py runserver 8002
```

[http://localhost:8002](http://localhost:8002) da oching

> **Windows eslatma:** `C:\Python313\python.exe` ishlating — `python.exe` Python 3.14 ga ishora qilishi mumkin (paketlar o'rnatilmagan).

---

## URL Xaritasi

```
/                          Asosiy sahifa
/scan/                     Yuklash va tahlil qilish (model tanlash)
/analyze/<pk>/result/      Natija + shifokor ko'rib chiqish paneli
/api/analyze/              AJAX POST -> AI so'rov (JSON javob)
/pricing/                  Narxlar sahifasi

/auth/login/               Kirish
/auth/register/            3 bosqichli ro'yxatdan o'tish
/auth/logout/              Chiqish
/auth/api/organizations/   AJAX muassasalar ro'yxati (ro'yxatdan o'tishda)
/auth/users/               Foydalanuvchilar (superuser / org_admin)
/auth/users/create/        Foydalanuvchi yaratish (superuser)
/auth/users/<pk>/edit/     Tahrirlash
/auth/users/<pk>/delete/   O'chirish

/org/dashboard/            Muassasa admin paneli
/org/users/<pk>/approve/   Tasdiqlash (POST)
/org/users/<pk>/reject/    Rad etish (POST JSON)

/dashboard/                Shaxsiy kabinet
/audit/analyses/           AI tahlil jurnali (filtr, eksport)
/audit/log/                Xavfsizlik jurnali (faqat superuser)
/admin/                    Django admin
```

---

## Ro'yxatdan O'tish Oqimi

```
1-qadam   Rol tanlash        (talaba / shifokor)
2-qadam   Muassasa tanlash   (AJAX, rolga qarab filtrlanadi)
3-qadam   Shaxsiy ma'lumotlar -> yuborish

  -> Hisob yaratildi: is_active=False, approval_status=pending
  -> Muassasa admin /org/dashboard/ da ko'rib chiqadi
  -> Tasdiqlandi  -> foydalanuvchi tizimga kirishi mumkin
  -> Rad etildi   -> login sahifasida sabab ko'rsatiladi
```

---

## Muhit O'zgaruvchilari

| O'zgaruvchi | Standart | Tavsif |
|-------------|----------|--------|
| `AI_SERVER_IP` | `10.49.158.145` | AI mikroservislar serveri IP manzili |
| `DB_NAME` | - | PostgreSQL baza nomi |
| `DB_USER` | - | PostgreSQL foydalanuvchi |
| `DB_PASSWORD` | - | PostgreSQL paroli |
| `DB_HOST` | `localhost` | PostgreSQL xost |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DEBUG` | `True` | Production da `False` qiling |
| `SECRET_KEY` | - | Django maxfiy kalit (min 50 belgi) |
| `PROSTATE_API_KEY` | *(ixtiyoriy)* | Prostata modeli uchun API kalit |

> **AI server manzili o'zgarganda:** faqat `AI_SERVER_IP` ni yangilang — uchala endpoint URL avtomatik yangilanadi.

---

## CSS Dizayn Tizimi

To'q ko'k tibbiy mavzu — `base.html` da CSS o'zgaruvchilar:

```css
--bg-dark:      #0a0f1f   /* sahifa foni      */
--bg-card:      #121a2e   /* karta foni       */
--bg-hover:     #1a2541   /* hover holati     */
--border-color: rgba(0,183,214,0.15)
--fg-primary:   #e3f2fd   /* asosiy matn      */
--fg-secondary: #90caf9   /* ikkilamchi matn  */
--fg-muted:     #5d7fa3   /* o'chirilgan matn */
--primary:      #0077b6
--primary-light:#00b4d8
--accent:       #00d4ff
```

Ikonlar: **Font Awesome 6.4.0** (`fas fa-*`) — `base.html <head>` da CDN orqali yuklanadi.

---

## Ishlab Chiquvchilar Uchun Eslatmalar

- **Lightbox:** `<div id="lightbox">` **`{% block content %}` ichida** bo'lishi shart — Django shablon meros qilishda blokdan tashqari HTML render qilinmaydi.
- **Logo mantiq:** `logo-lungs.png` (faqat o'pka) — "SinoMed" text yonida ishlatilganda; `logo.png` (ichida text bor) — mustaqil foydalanish uchun.
- **Prostata API parametri** `file` — boshqa barcha modellarda `image` ishlatiladi.
- **Soft-delete:** hozircha yo'q; o'chirishlar Django admin yoki superuser CRUD orqali amalga oshiriladi.

Batafsil texnik holat, model ichki tuzilmasi va yangi ishlab chiquvchi uchun qo'llanma: [HANDOFF.md](HANDOFF.md)

---

## Jamoa

**Fedora jamoasi** — National AI Hackathon 2026, Andijon viloyati

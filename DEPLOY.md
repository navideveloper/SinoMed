# SinoMed — VPS Deploy Yo'riqnomasi

Ubuntu + aaPanel o'rnatilgan server uchun.

---

## Talablar

- Ubuntu 20.04+
- SSH root kirish huquqi
- PostgreSQL (skript o'zi o'rnatadi)
- Python 3.11+

---

## 1. Serverga kirish

```bash
ssh root@SERVER_IP
```

---

## 2. Loyihani yuklab olish

```bash
git clone -b Oybek https://github.com/navideveloper/SinoMed.git /www/wwwroot/sinomed
cd /www/wwwroot/sinomed
```

---

## 3. `.env` faylini yaratish

```bash
cp .env.example .env
nano .env
```

Quyidagilarni to'ldiring:

```env
SECRET_KEY=tasodifiy-uzun-string-bu-yerga   # o'zgartiring!
DEBUG=False
ALLOWED_HOSTS=server-ip-yoki-domen,www.domen.uz

DB_NAME=sinomed_db
DB_USER=sinomed_user
DB_PASSWORD=kuchli-parol
DB_HOST=localhost
DB_PORT=5432

# AI model serverining IP manzili
AI_SERVER_IP=ai-server-ip

# Prostate model alohida URL'da ishlaydi
PROSTATE_AI_URL=https://prostataapi.starify.uz/predict
```

> **Eslatma:** `AI_SERVER_IP` ga faqat IP yoki domen yozing (http:// emas).
> Misol: `AI_SERVER_IP=192.168.1.100` ✓ | `AI_SERVER_IP=http://192.168.1.100` ✗

---

## 4. Avtomatik deploy

```bash
bash deploy.sh
```

Skript quyidagilarni bajaradi:
1. Tizim paketlarini o'rnatadi (python3, nginx, postgresql)
2. Virtual muhit yaratadi, paketlarni o'rnatadi
3. PostgreSQL foydalanuvchi va bazasini yaratadi
4. `migrate` va `collectstatic` buyruqlarini bajaradi
5. Systemd servis sifatida ishga tushiradi
6. Nginx konfiguratsiyasini o'rnatadi

---

## 5. Tekshirish

```bash
# Servis holati
systemctl status sinomed

# Saytni tekshirish
curl http://localhost

# Loglarni ko'rish
tail -f /var/log/sinomed/error.log
```

---

## Qo'shimcha buyruqlar

```bash
# Servisni qayta ishga tushirish
systemctl restart sinomed

# Yangi commit tortib olish
cd /www/wwwroot/sinomed
git pull origin Oybek
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
systemctl restart sinomed

# Superadmin yaratish
cd /www/wwwroot/sinomed
source venv/bin/activate
python manage.py createsuperuser
```

---

## AI Modellar

AI modellari serverda zip holatda saqlanadi. Portlar:

| Model | Port | URL |
|-------|------|-----|
| Pnevmoniya | 8001 | `http://AI_SERVER_IP:8001/api/` |
| Suyak yoshi | 8002 | `http://AI_SERVER_IP:8002/api/predict-bone-age` |
| Prostata | — | `https://prostataapi.starify.uz/predict` |

---

## Muammo yechish

| Muammo | Yechim |
|--------|--------|
| `502 Bad Gateway` | `systemctl restart sinomed` |
| `Static files ko'rinmayapti` | `python manage.py collectstatic` |
| `DB connection error` | `.env` dagi parolni tekshiring |
| `Permission denied` | `chown -R www-data:www-data /www/wwwroot/sinomed` |

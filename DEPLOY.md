# SinoMed — VPS Deploy Yo'riqnomasi (ZIP)

Ubuntu + aaPanel o'rnatilgan server uchun. Loyiha ZIP fayl orqali yuklanadi.

---

## Talablar

- Ubuntu 20.04+
- SSH root kirish huquqi
- aaPanel o'rnatilgan

---

## 1-qadam: ZIP faylni serverga yuklash

aaPanel → File Manager → `/www/wwwroot/` papkasiga `sinomed.zip` ni yuklang, keyin:

```bash
cd /www/wwwroot
unzip sinomed.zip -d sinomed
cd sinomed
```

> **Eslatma:** ZIP ni ochganingizda papka nomi `sinomed` bo'lishi kerak.
> Agar boshqacha bo'lsa: `mv sinomed-main sinomed`

---

## 2-qadam: Skriptni ishga tushirish

```bash
cd /www/wwwroot/sinomed
bash server_setup.sh
```

Skript davomida `.env` fayl to'ldirish so'raladi:

```env
SECRET_KEY=uzoq-tasodifiy-string-bu-yerga    # o'zgartiring!
DEBUG=False
ALLOWED_HOSTS=46.224.219.146,yourdomain.uz

DB_NAME=sinomed_db
DB_USER=sinomed_user
DB_PASSWORD=kuchli-parol
DB_HOST=localhost
DB_PORT=5432

# AI model serveri — barcha 3 model shu URL orqali, port bilan farqlanadi
# http:// yoki https:// bilan yozing, trailing slash bo'lmaydi
AI_SERVER_BASE=https://prostataapi.starify.uz
```

> **AI URL haqida:** Portlar: pnevmoniya `:8001`, suyak yoshi `:8002`, prostata `:8003`
> Skript ularni avtomatik qo'shadi.

---

## 3-qadam: Superadmin yaratish

```bash
source /www/wwwroot/sinomed/venv/bin/activate
python manage.py createsuperuser
```

---

## 4-qadam: Tekshirish

```bash
# Servis ishlayaptimi?
systemctl status sinomed

# Sayt ochilayaptimi?
curl http://localhost

# Xatolarni ko'rish
tail -f /var/log/sinomed/error.log
```

---

## Yangilanish (keyingi ZIP yuklanganida)

```bash
cd /www/wwwroot
unzip -o sinomed_new.zip -d sinomed_update
cp -r sinomed_update/. sinomed/
cd sinomed

source venv/bin/activate
pip install -r requirements.txt -q
python manage.py migrate --noinput
python manage.py collectstatic --noinput
systemctl restart sinomed
```

---

## AI Modellar

Barcha AI modellari `AI_SERVER_BASE` URL orqali, faqat port bilan farqlanadi:

| Model | Port | To'liq URL |
|-------|------|------------|
| Pnevmoniya | 8001 | `AI_SERVER_BASE:8001/` |
| Suyak yoshi | 8002 | `AI_SERVER_BASE:8002/` |
| Prostata | 8003 | `AI_SERVER_BASE:8003/` |

---

## Muammo yechish

| Muammo | Yechim |
|--------|--------|
| `502 Bad Gateway` | `systemctl restart sinomed` |
| `Static files ko'rinmayapti` | `python manage.py collectstatic` |
| `DB connection error` | `.env` dagi DB parolni tekshiring |
| `Permission denied` | `chown -R www-data:www-data /www/wwwroot/sinomed` |
| `AI modeli javob bermaydi` | `.env` dagi `AI_SERVER_BASE` ni tekshiring |

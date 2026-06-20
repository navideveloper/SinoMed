#!/bin/bash
# ============================================================
# SinoMed — ZIP-deploy skripti (Ubuntu + aaPanel)
# Loyiha /www/wwwroot/sinomed ga AVVAL chiqarilgan bo'lishi kerak
# Ishlatish: cd /www/wwwroot/sinomed && bash server_setup.sh
# ============================================================

set -e

PROJECT_DIR="/www/wwwroot/sinomed"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="/var/log/sinomed"
SERVICE_NAME="sinomed"

# Skript loyiha papkasidan ishga tushirilganini tekshir
if [ ! -f "$PROJECT_DIR/manage.py" ]; then
    echo "XATO: manage.py topilmadi. Skriptni loyiha papkasidan ishlating:"
    echo "  cd /www/wwwroot/sinomed && bash server_setup.sh"
    exit 1
fi

echo "=== [1/7] Tizim paketlari ==="
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx

echo "=== [2/7] Log papkasi ==="
mkdir -p $LOG_DIR

echo "=== [3/7] Virtual muhit ==="
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
fi
source $VENV_DIR/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "=== [4/7] .env fayli ==="
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp .env.example .env
    echo ""
    echo "=============================================="
    echo " MUHIM: .env faylini to'ldiring!"
    echo " nano $PROJECT_DIR/.env"
    echo ""
    echo " Kamida quyidagilarni o'zgartiring:"
    echo "   SECRET_KEY=... (uzoq tasodifiy string)"
    echo "   DEBUG=False"
    echo "   ALLOWED_HOSTS=server-ip-yoki-domen"
    echo "   DB_USER=sinomed_user"
    echo "   DB_PASSWORD=kuchli-parol"
    echo "   AI_SERVER_BASE=http://... yoki https://..."
    echo "=============================================="
    echo ""
    read -p ".env ni to'ldirib bo'ldingizmi? (Enter bosing davom etish uchun)" _
fi

echo "=== [5/7] PostgreSQL database ==="
DB_NAME=$(grep "^DB_NAME" .env | cut -d= -f2)
DB_USER=$(grep "^DB_USER" .env | cut -d= -f2)
DB_PASS=$(grep "^DB_PASSWORD" .env | cut -d= -f2)

sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename = '$DB_USER'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

echo "=== [6/7] Django migrate + collectstatic ==="
source $VENV_DIR/bin/activate
python manage.py migrate --noinput
python manage.py collectstatic --noinput

chown -R www-data:www-data $PROJECT_DIR
chown -R www-data:www-data $LOG_DIR

echo "=== [7/7] Systemd + Nginx ==="
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=SinoMed Django (Gunicorn)
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_DIR/bin/gunicorn -c gunicorn.conf.py config.wsgi:application
Restart=always
RestartSec=5
EnvironmentFile=$PROJECT_DIR/.env

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

cat > /etc/nginx/sites-available/sinomed << 'EOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 20M;

    location /static/ {
        alias /www/wwwroot/sinomed/staticfiles/;
    }

    location /media/ {
        alias /www/wwwroot/sinomed/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120;
    }
}
EOF

ln -sf /etc/nginx/sites-available/sinomed /etc/nginx/sites-enabled/sinomed
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ""
echo "=============================="
echo " SinoMed deploy TAYYOR!"
echo " http://$(curl -s ifconfig.me 2>/dev/null || echo 'SERVER_IP')"
echo ""
echo " Superadmin yaratish uchun:"
echo "   source $VENV_DIR/bin/activate"
echo "   python manage.py createsuperuser"
echo "=============================="

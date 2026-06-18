#!/bin/bash
# ============================================================
# SinoMed — VPS Deploy Script (Ubuntu + aaPanel)
# Ishlatish: bash deploy.sh
# ============================================================

set -e  # xato bo'lsa to'xta

PROJECT_DIR="/www/wwwroot/sinomed"
REPO_URL="https://github.com/navideveloper/SinoMed.git"
BRANCH="Oybek"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="/var/log/sinomed"
SERVICE_NAME="sinomed"

echo "=== [1/8] Tizim paketlari ==="
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx git

echo "=== [2/8] Loyiha papkasi ==="
mkdir -p $PROJECT_DIR
mkdir -p $LOG_DIR

if [ -d "$PROJECT_DIR/.git" ]; then
    echo "Mavjud repo — yangilanmoqda..."
    cd $PROJECT_DIR
    git fetch origin
    git checkout $BRANCH
    git pull origin $BRANCH
else
    echo "GitHub dan clone qilinmoqda..."
    git clone -b $BRANCH $REPO_URL $PROJECT_DIR
    cd $PROJECT_DIR
fi

echo "=== [3/8] Virtual muhit ==="
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
fi
source $VENV_DIR/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "=== [4/8] .env fayli ==="
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp .env.example .env
    echo ""
    echo "!!! MUHIM: .env faylini to'ldiring !!!"
    echo "    nano $PROJECT_DIR/.env"
    echo ""
    read -p "To'ldirib bo'ldingizmi? (Enter bosing)" _
fi

echo "=== [5/8] PostgreSQL database ==="
DB_NAME=$(grep DB_NAME .env | cut -d= -f2)
DB_USER=$(grep DB_USER .env | cut -d= -f2)
DB_PASS=$(grep DB_PASSWORD .env | cut -d= -f2)

sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename = '$DB_USER'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

echo "=== [6/8] Django setup ==="
source $VENV_DIR/bin/activate
python manage.py migrate --noinput
python manage.py collectstatic --noinput

echo "=== [7/8] Systemd servis ==="
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

chown -R www-data:www-data $PROJECT_DIR
chown -R www-data:www-data $LOG_DIR

systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

echo "=== [8/8] Nginx config ==="
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
        proxy_pass http://127.0.0.1:8000;
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
echo " http://$(curl -s ifconfig.me)"
echo "=============================="

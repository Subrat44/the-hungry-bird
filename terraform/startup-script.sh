#!/usr/bin/env bash
set -euo pipefail

apt-get update
apt-get install -y nginx python3 python3-venv

id -u restro >/dev/null 2>&1 || useradd --system --home /opt/restro-finder --shell /usr/sbin/nologin restro
install -d -o restro -g restro /opt/restro-finder

cat >/etc/systemd/system/restro-finder.service <<'UNIT'
[Unit]
Description=Restro Finder FastAPI service
After=network.target

[Service]
Type=simple
User=restro
Group=restro
WorkingDirectory=/opt/restro-finder
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-/etc/restro-finder.env
ExecStart=/opt/restro-finder/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

cat >/etc/nginx/sites-available/restro-finder <<'NGINX'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/restro-finder /etc/nginx/sites-enabled/restro-finder
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx
systemctl daemon-reload

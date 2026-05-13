#!/bin/bash
# Manual setup script for elbilspriser server (Debian 12 Bookworm)
# Run as root: bash setup.sh
set -e

DB_PASSWORD='xuOLFT26GQoBIaMJVgVxR01sphDAChAR'
REPO_URL='https://github.com/Europeanonion/-elbilspriser.git'
SSH_KEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIH50ByoQQKvvFvn9mXbQxJYvzFbftr7LOh2G8lLIGatH simon@elbilspriser'

echo "==> Installing base packages"
apt-get update -y
apt-get install -y curl git nginx build-essential gnupg lsb-release

echo "==> Adding TimescaleDB repository"
rm -f /etc/apt/trusted.gpg.d/timescaledb.gpg
curl -fsSL https://packagecloud.io/timescale/timescaledb/gpgkey | gpg --batch --no-tty --dearmor > /etc/apt/trusted.gpg.d/timescaledb.gpg
echo "deb https://packagecloud.io/timescale/timescaledb/debian/ bookworm main" > /etc/apt/sources.list.d/timescaledb.list

echo "==> Adding PostgreSQL repository"
rm -f /etc/apt/trusted.gpg.d/postgresql.gpg
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --batch --no-tty --dearmor > /etc/apt/trusted.gpg.d/postgresql.gpg
echo "deb https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list

echo "==> Installing PostgreSQL 15, PostGIS, TimescaleDB"
apt-get update -y
apt-get install -y postgresql-15 postgresql-15-postgis-3 timescaledb-2-postgresql-15

echo "==> Configuring TimescaleDB"
echo "shared_preload_libraries = 'timescaledb'" >> /etc/postgresql/15/main/postgresql.conf
systemctl restart postgresql

echo "==> Creating database role and extensions"
sudo -u postgres psql <<SQL
CREATE ROLE elbil WITH LOGIN PASSWORD '$DB_PASSWORD';
CREATE DATABASE elbilspriser OWNER elbil;
\c elbilspriser
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS postgis;
SQL

echo "==> Creating service user"
id elbil &>/dev/null || useradd -m -s /bin/bash elbil
usermod -aG sudo elbil
mkdir -p /home/elbil/.ssh
echo "$SSH_KEY" > /home/elbil/.ssh/authorized_keys
chown -R elbil:elbil /home/elbil/.ssh
chmod 700 /home/elbil/.ssh
chmod 600 /home/elbil/.ssh/authorized_keys

echo "==> Installing uv"
curl -LsSf https://astral.sh/uv/install.sh | sudo -u elbil sh

echo "==> Creating app directory"
install -d -o elbil -g elbil /opt/elbilspriser

echo "==> Cloning repository"
sudo -u elbil git clone "$REPO_URL" /opt/elbilspriser

echo "==> Installing Python 3.12 and dependencies (uv downloads Python automatically)"
cd /opt/elbilspriser/backend
sudo -u elbil /home/elbil/.local/bin/uv python install 3.12
sudo -u elbil /home/elbil/.local/bin/uv sync

echo "==> Installing Playwright Chromium"
sudo -u elbil /home/elbil/.local/bin/uv run playwright install chromium || true
/home/elbil/.local/bin/uv tool run --from playwright playwright install-deps chromium || true

echo "==> Configuring nginx"
cat > /etc/nginx/sites-available/elbilspriser <<'NGINX'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
    }
}
NGINX
ln -sf /etc/nginx/sites-available/elbilspriser /etc/nginx/sites-enabled/elbilspriser
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl enable --now nginx && systemctl reload nginx

echo "==> Installing systemd services"
cp /opt/elbilspriser/backend/systemd/*.service /etc/systemd/system/
cp /opt/elbilspriser/backend/systemd/*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable elbilspriser-api.service

echo ""
echo "==> Setup complete."
echo "    Next: create /opt/elbilspriser/.env then run: systemctl start elbilspriser-api"

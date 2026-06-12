#!/usr/bin/env bash

# ############################################################################
# AI_HEADER: MODULE_SCRIPTS_BOOTSTRAP_VDS
# ROLE: Tooling script
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-GUARDRAILS-TOOLING
# #########################################// START_MODULE_CONTRACT
# purpose: Tool: bootstrap-vds
# owns:
#   - scripts/bootstrap-vds.sh
# inputs: Function args
# outputs: Return values
# dependencies: local modules
# side_effects: n/a (pure)
# emitted_logs: n/a (pure)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# Первичная подготовка VDS под Astro Mini App.
# Папка проекта: /opt/solarsage-astro (владелец: пользователь astro).
# nginx у тебя УЖЕ установлен и настроен — этот скрипт его НЕ трогает.
# Запуск: bash bootstrap-vds.sh    (от root)
set -euo pipefail

USER_NAME=astro
APP_DIR=/opt/solarsage-astro

echo "[1/7] apt update + базовые пакеты (nginx НЕ ставим, certbot — опц.)"
apt-get update -y
apt-get install -y \
  build-essential git curl wget unzip ufw sudo \
  software-properties-common ca-certificates gnupg \
  python3.12 python3.12-venv python3-pip \
  postgresql-16 postgresql-contrib-16 \
  redis-server

echo "[2/7] Node 20 + pnpm"
if ! command -v node >/dev/null || [ "$(node -v | cut -dv -f2 | cut -d. -f1)" -lt 20 ]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi
npm i -g pnpm@9

echo "[3/7] Пользователь $USER_NAME + права на $APP_DIR"
if ! id -u $USER_NAME >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" $USER_NAME
  usermod -aG sudo $USER_NAME
fi
mkdir -p /home/$USER_NAME/.ssh
cp -n /root/.ssh/authorized_keys /home/$USER_NAME/.ssh/authorized_keys 2>/dev/null || true
chown -R $USER_NAME:$USER_NAME /home/$USER_NAME/.ssh
chmod 700 /home/$USER_NAME/.ssh
chmod 600 /home/$USER_NAME/.ssh/authorized_keys 2>/dev/null || true

mkdir -p $APP_DIR
chown -R $USER_NAME:$USER_NAME $APP_DIR

echo "[4/7] Swap 2G (если ещё нет)"
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "[5/7] UFW (22/80/443) — без перетряхивания, добавляем правила и enable если выключен"
ufw allow OpenSSH || true
ufw allow 80/tcp  || true
ufw allow 443/tcp || true
yes | ufw enable || true

echo "[6/7] Postgres + Redis: автозапуск (nginx не трогаем — он у тебя свой)"
systemctl enable --now postgresql
systemctl enable --now redis-server

if systemctl is-active --quiet nginx; then
  echo "      nginx уже запущен — ок."
else
  echo "      ВНИМАНИЕ: nginx не активен. Я его НЕ ставлю и НЕ запускаю."
  echo "      Подними его сам или запусти: systemctl enable --now nginx"
fi

echo "[7/7] Запретить root-логин по SSH"
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl reload ssh || systemctl reload sshd || true

echo
echo "Готово. Дальше:"
echo "  sudo -iu $USER_NAME"
echo "  git clone <repo> $APP_DIR    # или скопируй исходники в $APP_DIR"
echo "  cd $APP_DIR && cp .env.example .env && \$EDITOR .env"
echo "  make db-create && make migrate"
echo "  далее — docs/DEPLOY.md шаги 4–10"

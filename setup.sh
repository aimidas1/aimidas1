#!/bin/bash
set -e

REPO_DIR="${1:-$HOME/aimidas1}"
REPO_URL="https://github.com/aimidas1/aimidas1.git"

echo "=== Setup Advanced Stats Sync ==="
echo "Diretorio: $REPO_DIR"

if ! command -v python3 &>/dev/null; then
    echo "A instalar Python3..."
    sudo apt update && sudo apt install -y python3 python3-pip
fi

if ! command -v git &>/dev/null; then
    echo "A instalar Git..."
    sudo apt update && sudo apt install -y git
fi

if [ ! -d "$REPO_DIR" ]; then
    echo "A clonar repositorio..."
    git clone "$REPO_URL" "$REPO_DIR"
else
    echo "Repositorio ja existe. A fazer pull..."
    cd "$REPO_DIR" && git pull origin HEAD || true
fi

cd "$REPO_DIR"

echo "A instalar dependencias Python..."
pip3 install -r requirements.txt

if [ ! -f ".env" ]; then
    echo "ERRO: Ficheiro .env nao encontrado."
    echo "Copia .env.example para .env e preenche os valores:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

mkdir -p "advanced stats"

echo "A executar sincronizacao inicial..."
python3 sync_stats.py

CRON_CMD="cd $REPO_DIR && /usr/bin/python3 sync_stats.py >> $REPO_DIR/sync.log 2>&1"
CRON_SCHEDULE="0 0 */2 * *"

(crontab -l 2>/dev/null | grep -v "sync_stats"; echo "$CRON_SCHEDULE $CRON_CMD") | crontab -

echo ""
echo "=== Setup completo! ==="
echo "Cron: a cada 48 horas a meia-noite"
echo "Sync manual: cd $REPO_DIR && python3 sync_stats.py"
echo "Logs: cat $REPO_DIR/sync.log"
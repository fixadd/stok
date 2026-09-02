#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/backup_postgres.sh [retention_days]
# Creates a compressed logical backup from the docker-compose PostgreSQL service.

RETENTION_DAYS="${1:-7}"
BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT="${BACKUP_DIR}/stok_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"

echo "PostgreSQL yedeği oluşturuluyor: ${OUTPUT}"
docker compose exec -T db pg_dump \
  -U "${POSTGRES_USER:-stok}" \
  -d "${POSTGRES_DB:-stok}" \
  -Fc > "${OUTPUT}"

if [[ ! -s "${OUTPUT}" ]]; then
  echo "HATA: Yedek dosyası oluşturulamadı veya boş." >&2
  rm -f "${OUTPUT}"
  exit 1
fi

find "${BACKUP_DIR}" -type f -name 'stok_*.dump' -mtime "+${RETENTION_DAYS}" -delete

echo "Yedek tamamlandı. Saklama süresi: ${RETENTION_DAYS} gün."
ls -lh "${OUTPUT}"

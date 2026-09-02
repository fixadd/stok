#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/restore_postgres.sh backups/postgres/stok_YYYYMMDD_HHMMSS.dump
# WARNING: pg_restore with --clean --if-exists replaces existing objects in the target DB.

BACKUP_FILE="${1:-}"
if [[ -z "${BACKUP_FILE}" ]]; then
  echo "Kullanım: $0 <backup.dump>" >&2
  exit 2
fi

if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "HATA: Yedek dosyası bulunamadı: ${BACKUP_FILE}" >&2
  exit 1
fi

read -r -p "DİKKAT: Mevcut veritabanı üzerine geri yükleme yapılacak. Devam? (yes/no): " CONFIRM
if [[ "${CONFIRM}" != "yes" ]]; then
  echo "İşlem iptal edildi."
  exit 0
fi

echo "PostgreSQL geri yükleniyor..."
cat "${BACKUP_FILE}" | docker compose exec -T db pg_restore \
  -U "${POSTGRES_USER:-stok}" \
  -d "${POSTGRES_DB:-stok}" \
  --clean \
  --if-exists \
  --no-owner \
  --exit-on-error

echo "Geri yükleme tamamlandı."

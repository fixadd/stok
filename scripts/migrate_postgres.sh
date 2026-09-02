#!/usr/bin/env bash
set -euo pipefail

# Production-safe migration helper for the existing PostgreSQL installation.
# It never drops the database or removes application data.

POSTGRES_DB="${POSTGRES_DB:-stok}"
POSTGRES_USER="${POSTGRES_USER:-stok}"

if ! docker compose ps db >/dev/null 2>&1; then
  echo "HATA: docker compose servisi bulunamadı." >&2
  exit 1
fi

if ! docker compose exec -T db pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
  echo "HATA: PostgreSQL hazır değil." >&2
  exit 1
fi

BASE_TABLE="$(docker compose exec -T db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc "SELECT to_regclass('public.inventory_items');" | tr -d '[:space:]')"
if [[ "${BASE_TABLE}" != "inventory_items" ]]; then
  echo "HATA: inventory_items tablosu bulunamadı." >&2
  echo "Önce mevcut uygulama şemasının oluşturulduğundan emin olun; bu script boş veritabanı bootstrap işlemi yapmaz." >&2
  exit 1
fi

HAS_VERSION_TABLE="$(docker compose exec -T db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc "SELECT to_regclass('public.alembic_version');" | tr -d '[:space:]')"

if [[ -z "${HAS_VERSION_TABLE}" ]]; then
  echo "Migration geçmişi bulunamadı. Mevcut şema 0001_baseline olarak işaretleniyor..."
  docker compose exec -T web alembic stamp 0001_baseline
else
  echo "alembic_version mevcut; baseline stamp atlanıyor."
fi

echo "Migration'lar uygulanıyor..."
docker compose exec -T web alembic upgrade head

echo "Migration durumu:"
docker compose exec -T web alembic current

echo "PostgreSQL migration tamamlandı."

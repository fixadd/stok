# Büyük Dosya Denetimi

Generated from the current `main` tree. Files are prioritized by size and responsibility, not size alone.

| Boyut | Satır | Dosya | Öneri |
|---:|---:|---|---|
| 208.2 KB | 6251 | `app/legacy.py` | Domain servisleri, query katmanı ve seed/demo koduna ayır. |
| 101.3 KB | 3094 | `app/templates/inventory_tracking.html` | Partial + modal + page-specific JS/CSS olarak ayır. |
| 81.9 KB | 4243 | `app/templates/talep_takip.html` | Partial + modal + page-specific JS/CSS olarak ayır. |
| 64.3 KB | 1589 | `app/templates/stock_tracking.html` | Partial + modal + page-specific JS/CSS olarak ayır. |
| 62.2 KB | 1638 | `app/templates/admin_panel.html` | Partial + modal + page-specific JS/CSS olarak ayır. |
| 41.1 KB | 2642 | `app/static/css/style.css` | Kullanılan ortak/component kurallarını ayır; eski tema kurallarını kaldır. |
| 32.4 KB | 860 | `app/static/js/pages/license_tracking-1.js` | Fonksiyon sorumluluklarına göre böl; sırf boyut için bölme. |
| 27.4 KB | 860 | `app/models.py` | Domain model modüllerine ayır; ortak db/base tek yerde kalsın. |
| 21.0 KB | 429 | `app/templates/license_tracking.html` | Partial + modal + page-specific JS/CSS olarak ayır. |
| 19.5 KB | 33 | `app/templates/maintenance_tracking.html` | Partial + modal + page-specific JS/CSS olarak ayır. |
| 17.9 KB | 341 | `app/templates/admin_panel_modals.html` | Partial + modal + page-specific JS/CSS olarak ayır. |
| 15.9 KB | 464 | `app/personnel_lifecycle.py` | Fonksiyon sorumluluklarına göre böl; sırf boyut için bölme. |

## Kural

Yeni kod büyük monolitik dosyalara eklenmemeli. Refactor adımları küçük commitler halinde yapılmalı ve her adım PostgreSQL CI ile doğrulanmalı.

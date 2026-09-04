# STOK Refactoring Status

This document tracks the migration away from `app/legacy.py` and the enterprise feature roadmap.

## Phase 1 — Core architecture

- [x] Route domains split into blueprints/modules (auth, inventory, maintenance, stock, admin, requests, information, profile, settings, custom fields).
- [x] Inventory payload/query/service layers extracted.
- [x] Maintenance/request/stock/user query services extracted.
- [x] Settings/custom-field service layer extracted.
- [x] Custom fields support inventory, stock, maintenance, request, license and user entity types through the shared configuration layer.
- [x] Conditional custom-field dependencies and hidden-field save protection implemented.
- [x] Core legacy helpers extracted to `app/services/core_helpers.py` and runtime compatibility bindings updated.
- [ ] Physically remove migrated definitions from `legacy.py` after compatibility callers are eliminated.

## Phase 2 — UX and operations

- [x] Dashboard widget model/service foundation exists.
- [x] Notification dispatch API foundation exists.
- [x] Conditional field settings UI exists.
- [x] QR/SKU helper foundation exists.
- [ ] Complete dashboard drag/drop builder and persistent per-user layouts.
- [ ] Complete centralized filter UI with saved filters.
- [ ] Complete notification inbox, preferences and scheduled rules.
- [ ] Complete QR/barcode print/batch screens.

## Phase 3 — Enterprise

- [x] Report data API foundation exists.
- [x] Portable report/filter specification service added in `enterprise_service.py`.
- [x] Secure API-token hashing/expiry primitives added.
- [ ] Persisted report definitions and saved reports.
- [ ] Excel/CSV/PDF report export UI and background jobs.
- [ ] Persisted API token model, scopes, revocation, rate limits and audit logs.
- [ ] Central configuration/audit log UI.

## Phase 4 — Technical cleanup

- [ ] Complete template inheritance cleanup.
- [ ] Finish JavaScript module split, especially license tracking.
- [ ] Remove obsolete CSS and make `redesign.css` the single application stylesheet.
- [ ] Personnel lifecycle service completion.
- [ ] Repair service cleanup.
- [ ] Delete `legacy.py` after all compatibility seams are gone.

## Phase 5 — Production hardening

- [ ] Migration/schema consistency audit.
- [ ] Authentication and authorization audit.
- [ ] Input validation/security audit.
- [ ] Database index/query performance audit.
- [ ] Docker production configuration audit.
- [ ] Full CI/test verification.
- [ ] Deployment and administrator documentation.

## Current migration rule

New business logic belongs in `app/services/` or `app/routes/`. `legacy.py` is a temporary compatibility layer only. During the transition, runtime bindings in `app/__init__.py` may redirect legacy names to the new service implementation so existing routes remain stable.

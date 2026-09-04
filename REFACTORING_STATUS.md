# STOK Refactoring Status

This document tracks the migration away from `app/legacy.py`, the enterprise feature roadmap, and the UI modernization.

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
- [x] Enterprise dark UI foundation implemented with Bootstrap/Tabler-compatible design tokens.
- [x] Shared sidebar/topbar/navigation shell standardized.
- [x] Dashboard, inventory, stock, license and maintenance surfaces standardized.
- [x] Personnel, information and admin surfaces standardized.
- [x] Responsive table, form, modal, toolbar and status patterns standardized.
- [x] Legacy Bootstrap icon classes normalized at runtime to Tabler icons.
- [x] Inventory search/filter compatibility fixed without changing backend behavior.
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
- [ ] Remove obsolete CSS and consolidate the stylesheet stack after page-specific dependencies are verified.
- [ ] Personnel lifecycle service completion.
- [ ] Repair service cleanup.
- [ ] Delete `legacy.py` after all compatibility seams are gone.

### Legacy compatibility audit

`app/__init__.py` still imports `app.legacy` and deliberately installs runtime compatibility bindings for extracted services. Therefore `legacy.py` must **not** be deleted yet. The safe migration order is: move remaining route/business definitions out of `legacy.py` → update direct callers/imports → remove compatibility bindings → run compile/tests/migrations → delete `legacy.py`.

The current application already has dedicated route modules under `app/routes/` for auth, inventory, maintenance, admin, requests, information, profile, settings and stock, while `legacy.py` remains the compatibility/bootstrap seam. This is an intentional incremental migration rather than a big-bang deletion.

### CSS cleanup rule

The application currently uses a layered stylesheet strategy so that the new enterprise design can override legacy page-specific rules without breaking functionality. `redesign.css` contains legacy global styling and is therefore not being blindly deleted. It will be retired only after its selectors are checked against templates and page scripts. The current final override layers are `design-system.css` and `enterprise-pages.css`.

## Phase 5 — Production hardening

- [ ] Migration/schema consistency audit.
- [ ] Authentication and authorization audit.
- [ ] Input validation/security audit.
- [ ] Database index/query performance audit.
- [ ] Docker production configuration audit.
- [x] CI verification for the latest UI standardization commit.
- [ ] Deployment and administrator documentation.

## Current migration rule

New business logic belongs in `app/services/` or `app/routes/`. `legacy.py` is a temporary compatibility layer only. During the transition, runtime bindings in `app/__init__.py` may redirect legacy names to the new service implementation so existing routes remain stable.

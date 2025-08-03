# PlasmaProject v1-1-7 — Folder Structure Reference

This document is a living reference for the folder and file structure of the PlasmaProject e-commerce MVP. Update this file whenever you add, remove, or reorganize files/folders, so Grok and Cascade remain in sync and the team never loses track of what’s being built.

---

## Logging
- **Backend**: Uses `logging.info` and `logging.error` for requests, payloads, and exceptions.
- **Frontend**: Uses `console.log` for upload payloads and raw responses.
- These logs are essential for debugging upload and API issues.

## Asset Scan
- The backend dynamically scans for built React assets using:
  `os.path.join(current_app.static_folder, 'react-build', 'assets')`
- This ensures Flask finds the correct JS and CSS files and prevents blank UI or asset 500 errors.

## Root Directory

- `.env` — Environment variables (DO NOT COMMIT SENSITIVE VALUES)
- `.env.example` — Example/template for environment variables
- `.git/` — Git repository data (hidden)
- `.gitignore` — Patterns for files/folders to exclude from version control
- `alembic.ini` — Alembic migration config
- `app/` — Main Flask application code (see below)
- `archive/` — Legacy or backup files
- `config.py` — App configuration
- `docs/` — Documentation (this file, plans, etc.)
- `instance/` — Instance-specific files (e.g., SQLite DB, configs)
- `migrations/` — Database migration scripts
- `orders/`, `production_orders/`, `temp_orders/` — Order data
- `requirements.txt` — Python dependencies
- `run.py` — App entry point
- `scripts/` — Utility scripts
- `static/` — Static files (see below)
- `tests/` — Automated tests
- `uploads/` — Uploaded files
- *(other files: logs, reports, CSVs, etc.)*

---

## app/
- `__init__.py` — App factory/init
- `models/` — Database models
- `parser_app.py` — DXF parsing logic
- `routes/` — Flask route definitions
- `static/` — Static assets (images, logos, etc.)
- `templates/` — Jinja2 HTML templates
- `uploads/` — Upload endpoints/data
- `utils/` — Utility modules (e.g., costing, DXF parsing)

### app/models/
- `customer.py`, `order.py`, `order_item.py`, `upload.py`, `user.py` — Model definitions

### app/routes/
- `main.py` — Main route handlers

### app/static/
    favicon.ico   # Site favicon used in all templates for browser tab icon
- `assets/` — Images, icons, etc.
- `logos/` — Logo images
- `favicon.ico` — Site favicon
- `react-build/` — Production React build output (hashed JS/CSS, favicon, manifest.json). Flask serves React from here at / in production.

### app/templates/
- `.keep` — Keeps folder in Git
- `checkout.html`, `login.html`, `landing.html`, etc. — HTML templates

### app/uploads/
- `.keep` — Keeps folder in Git
- `parser_uploads/` — Uploaded files for parsing

### app/utils/
- `costing.py`, `dxf_parser.py` — Utility logic
- `cascade_dxf_parser_update_report*.txt` — Parser update logs

### React UI
- The React UI (in `app/static/react-build/`) should replicate the features and layout of `customer_index.html`: drag-and-drop DXF upload, cart table, calculate/buy buttons, and modal dialogs for login/signup/checkout. This ensures the MVP user experience matches the intended quoting interface.

---

## docs/
- `folder_structure.md` — This file
- *(Add future documentation here, e.g., `ecommerce_mvp_plan.md`)*

---

## Conventions
- Update this file whenever you add/remove/rename files or folders.
- Use `.keep` files to track empty directories in Git.
- Sensitive data should only be in `.env` (never commit secrets).

---

_Last updated: 2025-07-12_

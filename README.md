# master_thesis_nabodita — Excel → MariaDB ETL

End-to-end, reproducible ETL pipeline to ingest the provided `.xlsm` templates into a MariaDB schema using SQLAlchemy, Pydantic, and Alembic. It includes validators, a human-readable “plan” preview, a safe **dry-run** load, and optional material upsert/matching via a YAML config.

---

## ✨ Features

- Parse three sheets from the workbook:
  - **Process** → `process` + `process_material_flow` (+ process KPIs)
  - **MFA&Material_quality_Template** → `flow_sample`, `collection_flow_kpi`, `flow_sample_component`
  - **Material_Table** (optional, one-time) → `material`
- Robust parsing (position-independent, label-driven).
- Validation with helpful flags/messages.
- **Plan** mode prints a tree of what would be inserted.
- **Load** mode supports:
  - **dry-run** (no writes, but full SQL emitted with `--echo-sql`)
  - **replace existing process by name**
  - **material upsert** from `Material_Table`
  - alias/synonym/hardcoded material mapping (+ fuzzy fallback)
- Production-ready packaging: Poetry, pre-commit (black/ruff/mypy), Alembic migrations, Jupyter kernel support.

---

## 🧰 Prerequisites

- **Python 3.12**
- **MariaDB** reachable from your environment (local or via VPN)
- (Windows) **PowerShell**; (macOS/Linux) a modern shell (zsh/bash)
- Git

---

## 🚀 Install `pipx` and Poetry

### Windows (PowerShell)

    # pipx
    python -m pip install --user pipx
    python -m pipx ensurepath
    # Close & re-open PowerShell (or refresh env)

    # Poetry via pipx
    pipx install poetry

### macOS / Linux

    # pipx
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    # Re-open your shell

    # Poetry via pipx
    pipx install poetry

> Why `pipx`? It isolates CLI tools (like Poetry) from your project virtualenv.

---

## 📦 Clone & install dependencies

    git clone <your-repo-url>.git
    cd master_thesis_nabodita

    # Create the virtualenv and install dependencies
    poetry install --with dev

> If you prefer keeping Poetry’s venv **inside** the repo:
>
>     poetry config virtualenvs.in-project true
>     poetry install --with dev

---

## 🔐 Environment configuration

1) Copy `.env.example` to `.env` and **edit for your environment**:

    cp .env.example .env

- **Do not** put secrets in `.env.example`.
- `.env` is git-ignored; never commit real credentials.

You can configure the DB two ways—pick one:

**A) Single URL**

    # .env
    DATABASE_URL="mariadb+pymysql://user:password@localhost:3306/yourdb"

**B) Discrete parts (auto-composed by the app)**

    # .env
    DB_USER="user"
    DB_PASSWORD="password"
    DB_HOST="localhost"
    DB_PORT=3306
    DB_NAME="yourdb"
    # Optional (defaults to mariadb+pymysql):
    # DB_DRIVER="mariadb+pymysql"

At runtime we read `.env` and build a SQLAlchemy engine accordingly.

---

## 📓 (Optional) Jupyter kernel for this venv

    poetry run python -m ipykernel install --user --name "mfa-ingest" --display-name "Python (mfa-ingest)"

Open JupyterLab and choose the **Python (mfa-ingest)** kernel.

---

## 🧭 Repository structure

```
master_thesis_nabodita
├── .env
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── alembic.ini
├── poetry.lock
├── pyproject.toml
├── README.md
├── .github
│   └── workflows
│       └── ci.yml
├── alembic
│   ├── alembic.ini
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions
│       └── 001_nabodita_baseline_schema.py
├── config
│   ├── default.yaml
│   └── logging.ini
├── data
└── mfa_ingest
    ├── cli.py
    ├── __init__.py
    ├── core
    │   ├── db.py
    │   ├── settings.py
    │   └── __init__.py
    ├── db
    │   └── session.py
    ├── db_models
    │   ├── base.py
    │   ├── flows.py
    │   ├── material.py
    │   ├── process.py
    │   ├── process_kpis.py
    │   └── __init__.py
    ├── extract
    │   ├── excel_reader.py
    │   ├── material_sheet_parser.py
    │   ├── mfa_sheet_parser.py
    │   ├── process_sheet_parser.py
    │   └── __init__.py
    ├── load
    │   ├── loader.py
    │   └── __init__.py
    ├── schemas
    │   ├── flow.py
    │   ├── material.py
    │   ├── process.py
    │   └── __init__.py
    └── transform
        ├── mappers.py
        ├── material_matcher.py
        ├── merge_mfa_with_process.py
        ├── process_sheet_builder.py
        ├── validators.py
        └── __init__.py


```

---

## ⚙️ Configuration (`config/default.yaml`)

This file drives parsing and matching:

- **`sheets`**: sheet names.
- **`process_sheet`**: titles, header maps, and KPI row patterns.
- **`mfa_sheet`**:
  - sections (Generic Data, Elementary, Process Specific Data, Material Composition)
  - row label maps (e.g., mapping “Moisture condition” to `moisture_condition`)
  - **`map_collection_kpi_rows`**
- **`material_sheet`**:
  - `header_map` for Material_Table
  - `synonyms`: canonical → [aliases]
  - `hardcode_map`: incoming name → canonical name
- **`etl.dry_run`**: default dry-run behavior (the CLI `--dry-run` flag overrides).

You can provide a different config via `--config path/to/config.yaml`.

---

## 🖥️ CLI commands

All commands run through Poetry (so they use the project venv).

### 1) Validate

    poetry run mfa-ingest validate "path/to/workbook.xlsm" --config config/default.yaml

- Parses the workbook using the YAML rules.
- Checks required fields, types, and “flags” (e.g., numeric text in text-only rows).
- Exits non-zero on hard errors. Use `--strict` if you want flags to hard-fail.
- Optionally verify the **Material_Table** too:

    poetry run mfa-ingest validate "path/to/workbook.xlsm" --check-materials

### 2) Plan

    poetry run mfa-ingest plan "path/to/workbook.xlsm" --config config/default.yaml --materials

- Shows exactly what would be inserted (by table), including nested flow/sample/components and counts.
- `--materials`: also parses `Material_Table` (just for printing/plan).
- Good for sanity-checking the sheet without touching the DB.

### 3) Load

    poetry run mfa-ingest load "path/to/workbook.xlsm" \
      --config config/default.yaml \
      --materials \
      --replace-process-by-name \
      --dry-run \
      --echo-sql

Options:

- `--materials`
  Upsert materials from `Material_Table` (insert/update by `polymer_type`).

- `--replace-process-by-name`
  If the same `process_name` already exists, delete it (cascade) before inserting the new one.
  Great for iterative local testing; use caution in shared/prod DBs.

- `--auto-create-materials`
  If a component doesn’t match any existing/hardcoded/synonym material, create a bare `material` row on the fly.

- `--dry-run`
  Run everything but **roll back** at the end (no DB writes).
  Use with `--echo-sql` to see SQL emitted.

- `--database-url "mariadb+pymysql://user:pass@host:port/db"`
  Override `.env` connection for a single run.

- `--echo-sql`
  Print all SQL (via SQLAlchemy). Excellent for debugging.

**Examples**

- Minimal load to local DB using `.env`:

      poetry run mfa-ingest load "file.xlsm"

- Load with materials and safe replacement, real commit:

      poetry run mfa-ingest load "file.xlsm" --materials --replace-process-by-name

- Dry-run against a remote DB URL:

      poetry run mfa-ingest load "file.xlsm" --dry-run --database-url "mariadb+pymysql://user:pass@10.0.0.5:3306/prod"

---

## 🗄️ Alembic migrations (local & production)

> ⚠ **Strong warning:** Whenever possible, practice the full migration locally (or on a staging DB clone) **before** touching production. Always back up.

### Baseline vs. Head

This repo contains migrations such as:
- **Baseline** (e.g., `cbbf78965a17_baseline_existing_schema_pre_alembic.py`) – represents the pre-alembic schema.
- Later migrations (e.g., triggers, schema changes like the `material` table updates).

### First-time setup on a DB that already has the schema (prod)

1) Point to the production DB (via `.env` or `--database-url`).

2) **Stamp** the DB with the baseline revision (no DDL executed; just records the version):

       poetry run alembic stamp cbbf78965a17

   This creates the `alembic_version` table (if missing) and sets it to the baseline.

3) **Upgrade** to the latest:

       poetry run alembic upgrade head

If your production schema already diverged (e.g., manual changes), test locally and adjust migrations accordingly (e.g., drop/rename constraints in the right order for MariaDB).

### Typical local flow

    # Create a new migration after editing ORM models (if applicable)
    poetry run alembic revision -m "explain what changed"

    # Apply locally
    poetry run alembic upgrade head

    # If you created a baseline revision to “adopt” an existing DB, stamp it:
    poetry run alembic stamp <baseline_revision_id>

---

## 🧪 Development & quality

Install and enable pre-commit hooks:

    poetry run pre-commit install
    poetry run pre-commit run --all-files

- **black**: formatting
- **ruff**: linting
- **mypy**: static typing

Run unit tests (if/when you add them):

    poetry run pytest -q

---

## 🔍 Troubleshooting

- **`Can't load plugin: sqlalchemy.dialects:driver`**
  Ensure your URL uses `mariadb+pymysql://...` and `pymysql` is installed (it is in `pyproject.toml`).

- **Validation passes but plan shows missing data**
  Check your `config/default.yaml` section label spellings and case (labels are normalized, but headers must be mapped).

- **Components keep `material_id=None`**
  - Confirm you ran with `--materials` so the Material_Table is upserted.
  - Ensure your `material_sheet.hardcode_map` and `synonyms` include the incoming names.
  - Try `--auto-create-materials` (last resort).
  - Use `--echo-sql --dry-run` to observe insert/select ordering.

- **VPN/Prod connection**
  Prefer `--dry-run` first. Use `--database-url` to override `.env` without changing local config.

---

## 🔒 Data & secrets

- Store secrets only in `.env`. Never commit secrets or modify `.env.example` to include them.
- `.env` is in `.gitignore` by default.

---

## 🧭 ETL overview (high-level)

1) **Extract**
   Parsers (`extract/`) read sheets via OpenPyXL and produce normalized dicts/dataframes.

2) **Transform**
   Pydantic schemas + transformation (`transform/`) validate/merge into `ProcessPacket`(s) and `FlowPacket`(s).
   Material suggestions and flags are added here.

3) **Load**
   The loader (`load/loader.py`) writes to DB in a safe order, within a transaction, honoring triggers and constraints.
   Options control replacement, material upsert, auto-create, and dry-run.

---

## 📄 License

Add your preferred license here.

---

## 🤝 Contributing

- Use feature branches and PRs.
- Keep migrations small and tested locally.
- Update `config/default.yaml` if you introduce new labels/columns.
- Add/adjust `hardcode_map`/`synonyms` when onboarding new workbooks.

---

## 🧷 Quick command reference

    # Install deps
    poetry install --with dev

    # Validate workbook
    poetry run mfa-ingest validate "file.xlsm"

    # Plan inserts (no DB writes)
    poetry run mfa-ingest plan "file.xlsm" --materials

    # Load (dry-run: safe)
    poetry run mfa-ingest load "file.xlsm" --materials --replace-process-by-name --dry-run --echo-sql

    # Load (commit)
    poetry run mfa-ingest load "file.xlsm" --materials --replace-process-by-name

    # Alembic: stamp prod at baseline (creates alembic_version), then upgrade
    poetry run alembic stamp cbbf78965a17
    poetry run alembic upgrade head

If you get stuck, open an issue with:
- the command you ran,
- console output (with `--echo-sql` if possible),
- and a redacted snippet of your workbook (or fictitious sample mimicking the structure).

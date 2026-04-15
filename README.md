# Company8 - SAR Platform

> A Django-based Staff Annual Reporting platform for the Department of Computing and Information Technology (DCIT) at the University of the West Indies.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Local Development Setup](#local-development-setup)
- [Environment Variables](#environment-variables)
- [Running Tests](#running-tests)
- [Deployment](#deployment)
  - [Neon PostgreSQL](#neon-postgresql)
  - [Cloudinary](#cloudinary)
  - [Render](#render)

---

## Overview

The **Staff Annual Reporting (SAR) Platform** facilitates the creation, management, and viewing of annual reports submitted by staff members within DCIT. Administrators can manage accounts, bulk-import reports via CSV, and export branded PDF reports.

---

## Key Features

- **User Authentication & Profiles** - Secure sign-in for staff members, with profile pages displaying reports, profile pictures, and basic information.
- **Report Management (CRUD)** - Authenticated users can create, view, edit, and soft-delete their own reports.
- **Structured Reporting** - Reports include a title, description, date, category (Publication, Award, Initiative, Activity), assigned committees, and participants.
- **Participant Tracking** - Reports link participants to staff accounts via a reactive autocomplete input.
- **Advanced Filtering & Search** - Keyword search and active filter pills for period, category, committee, and participant.
- **PDF Export** - Download branded annual reports (calendar year, academic year, or custom range) and personal report PDFs.
- **Admin Dashboard** - Manage user accounts (activate/deactivate), soft-delete reports, and bulk-import via CSV.
- **Data Scraping** - Built-in utilities to sync staff profiles and publications from the UWI DCIT website.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Django 6.0.2 |
| Frontend | HTML5, Tailwind CSS v4, JavaScript |
| Database (dev) | SQLite3 |
| Database (prod) | Neon PostgreSQL (serverless) |
| Media Storage | Cloudinary |
| Static Files | WhiteNoise |
| Web Server | Gunicorn |
| Deployment | Render.com |

---

## Project Structure

```
Company8-SAR-Platform/
│
├── Annual_Reporting_Platform/       # Django project root
│   ├── Annual_Reporting_Platform/   # Project config (settings, urls, wsgi)
│   ├── reports/                     # Public report listing, filtering, PDF, models
│   ├── users/                       # Auth, profiles, report CRUD
│   ├── administration/              # Admin dashboard, CSV import, web scraping
│   ├── templates/                   # Global base template
│   ├── static/                      # Static assets
│   ├── test_runner.py               # Custom SAR test runner
│   ├── manage.py
│   ├── requirements.txt
│   ├── build.sh                     # Render build script
│   └── render.yaml                  # Render deployment config
│
└── HTML_CSS_JAVASCRIPT/             # UI mockups and reference views
```

---

## Local Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Company8-SAR-Platform/Annual_Reporting_Platform
```

### 2. Create and Activate a Virtual Environment

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (Git Bash)**
```bash
python -m venv .venv
source .venv/Scripts/activate
```

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create the Environment File

Create a file called `.env` inside `Annual_Reporting_Platform/` (next to `manage.py`):

```env
# Leave DATABASE_URL blank to use local SQLite (recommended for development)
DATABASE_URL=

# Cloudinary - leave blank to skip media uploads during local dev
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
```

> See [Environment Variables](#environment-variables) for how to fill these in for production.

### 5. Apply Database Migrations

```bash
python manage.py migrate
```

### 6. Create a Superuser

Grants admin access to the SAR admin dashboard and the Django `/admin/` panel.

```bash
python manage.py createsuperuser
```

### 7. Run the Development Server

```bash
python manage.py runserver
```

Open your browser and navigate to:

```
http://127.0.0.1:8000/
```

---

## Environment Variables

All secrets are loaded from a `.env` file (never committed to git). The following variables are supported:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Production only | Full PostgreSQL connection string from Neon. Leave blank to use local SQLite. |
| `CLOUDINARY_CLOUD_NAME` | Production only | Your Cloudinary cloud name |
| `CLOUDINARY_API_KEY` | Production only | Your Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Production only | Your Cloudinary API secret |
| `SECRET_KEY` | Production only | Django secret key. Auto-generated by Render in production. |
| `RENDER` | Set by Render | When this variable is present, `DEBUG` is set to `False` automatically. |

> `.env` is listed in `.gitignore` and will never be pushed to the repository.

---

## Running Tests

The project uses a custom test runner (`SARTestRunner`) that separates tests into **Unit** and **Integration** sections and prints human-readable output with pass/fail per test.

All commands must be run from inside `Annual_Reporting_Platform/` (where `manage.py` lives).

### Run All Tests

```bash
python manage.py test users.tests reports.tests administration.tests \
    --testrunner=test_runner.SARTestRunner
```

### Run Tests for a Specific App

```bash
# Reports app only
python manage.py test reports.tests --testrunner=test_runner.SARTestRunner

# Users app only
python manage.py test users.tests --testrunner=test_runner.SARTestRunner

# Administration app only
python manage.py test administration.tests --testrunner=test_runner.SARTestRunner
```

### Run Only Unit or Integration Tests

```bash
# Unit tests only (models, properties, isolated logic)
python manage.py test reports.tests.unit users.tests.unit administration.tests.unit \
    --testrunner=test_runner.SARTestRunner

# Integration tests only (HTTP requests, views, database)
python manage.py test reports.tests.integration users.tests.integration administration.tests.integration \
    --testrunner=test_runner.SARTestRunner
```

### Expected Output

```
======================================================================
  UNIT TESTS  -  models, properties, isolated logic
======================================================================
  35 test(s) found

  Report __str__ format is username and title          [0.01s]  PASS
  Default isActive is True                             [0.01s]  PASS
  ...

  UNIT TESTS    35 passed  0 failed  (35 total)

======================================================================
  INTEGRATION TESTS  -  HTTP requests, views, database
======================================================================
  105 test(s) found

  GET /reports/ returns HTTP 200                       [0.21s]  PASS
  Active reports appear on the public index page       [0.18s]  PASS
  ...

  INTEGRATION TESTS    105 passed  0 failed  (105 total)

======================================================================
  ALL TESTS PASSED
======================================================================
```

> **Note:** Tests always run against a temporary SQLite database regardless of the `DATABASE_URL` setting. The production Neon database is never touched during testing.

---

## Deployment

The platform is deployed on **Render** using **Neon PostgreSQL** as the database and **Cloudinary** for media storage.

---

### Neon PostgreSQL

Neon is a serverless PostgreSQL service with a permanent free tier (no 90-day expiry).

1. Go to [neon.tech](https://neon.tech) and create a free account.
2. Create a new **Project** and a database (the default `neondb` is fine).
3. From the project dashboard, copy the **Connection String**. It looks like:
   ```
   postgresql://neondb_owner:<password>@<host>.neon.tech/neondb?sslmode=require
   ```
4. Add it to your `.env` file as `DATABASE_URL`:
   ```env
   DATABASE_URL=postgresql://neondb_owner:<password>@<host>.neon.tech/neondb?sslmode=require
   ```
5. Run migrations against Neon to create all tables:
   ```bash
   python manage.py migrate
   ```

#### Migrating Existing Data from SQLite to Neon

If you have existing data in your local SQLite database, export and import it:

```bash
# 1. Export from SQLite (temporarily ignore DATABASE_URL so it reads from SQLite)
DATABASE_URL="" python manage.py dumpdata \
    --natural-foreign --natural-primary \
    --exclude=contenttypes --exclude=auth.permission \
    -o db_backup.json

# 2. Import into Neon (DATABASE_URL must point to Neon)
python manage.py loaddata db_backup.json
```

> `db_backup.json` is listed in `.gitignore` and will not be committed.

---

### Cloudinary

Cloudinary stores all user-uploaded media (profile pictures and report feature images).

1. Go to [cloudinary.com](https://cloudinary.com) and create a free account.
2. From the **Dashboard**, copy your **Cloud Name**, **API Key**, and **API Secret**.
3. Add them to your `.env` file:
   ```env
   CLOUDINARY_CLOUD_NAME=your_cloud_name
   CLOUDINARY_API_KEY=your_api_key
   CLOUDINARY_API_SECRET=your_api_secret
   ```
4. In **Render**, add the same three values as environment variables (see below).

---

### Render

1. Push your code to a GitHub repository.
2. Go to [render.com](https://render.com), create a free account, and click **New → Web Service**.
3. Connect your GitHub repository and select the branch to deploy.
4. Set the following in the Render service settings:

   | Setting | Value |
   |---|---|
   | **Root Directory** | `Annual_Reporting_Platform` |
   | **Build Command** | `./build.sh` |
   | **Start Command** | `gunicorn Annual_Reporting_Platform.wsgi:application` |

5. Under **Environment Variables**, add:

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | Your Neon connection string |
   | `CLOUDINARY_CLOUD_NAME` | Your Cloudinary cloud name |
   | `CLOUDINARY_API_KEY` | Your Cloudinary API key |
   | `CLOUDINARY_API_SECRET` | Your Cloudinary API secret |
   | `SECRET_KEY` | Click **Generate** - Render creates a secure random key |
   | `RENDER` | `true` (this flag disables DEBUG automatically) |

6. Click **Create Web Service**. Render will run `build.sh` on every deploy, which:
   - Installs Python dependencies (`pip install -r requirements.txt`)
   - Collects static files (`python manage.py collectstatic --noinput`)
   - Applies any pending migrations (`python manage.py migrate`)

7. Once deployed, your app will be live at:
   ```
   https://<your-service-name>.onrender.com
   ```

#### Creating an Admin Account on Render

Render doesn't provide an interactive terminal for `createsuperuser`. Instead, use the Render **Shell** tab in your service dashboard:

```bash
python manage.py createsuperuser
```

---

## Data Scraping

The administration dashboard includes built-in tools to sync staff and publication data from the UWI DCIT website. These are accessible at `/administration/generate-reports/` when logged in as an admin.

Alternatively, the raw scraping logic lives in `administration/report_generation_helpers.py` and can be triggered programmatically via `generate_staff_accounts()` and `generate_publication_reports()`.

# Company8 — SAR Platform

> A Django-based Staff Annual Reporting platform for the Department of Computing and Information Technology (DCIT) at the University of the West Indies.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Local Development Setup](#local-development-setup)
- [Data Scraping](#data-scraping)
- [Deployment](#deployment)

---

## Overview

The **Staff Annual Reporting (SAR) Platform** facilitates the creation, management, and viewing of annual reports submitted by staff members within DCIT.

---

## Key Features

- **User Authentication & Profiles** — Secure sign-in for staff members, with profile pages displaying reports, profile pictures, and basic information.
- **Report Management (CRUD)** — Authenticated users can create, view, edit, and delete their own reports through a user-friendly interface.
- **Structured Reporting** — Reports are organised with a title, description, date, category (e.g. Publication, Award, Initiative), and assigned committee.
- **Participant Tracking** — Reports can include multiple participants, linking staff members to various activities and publications.
- **Advanced Filtering & Search** — The main reports page supports keyword search and filtering by period (week, month, year), category, and committee.
- **Admin Dashboard** — Dedicated dashboard for administrators to manage user account approvals and review, approve, or decline pending staff reports.
- **Data Scraping Utilities** — Python scripts to populate the database by scraping staff profiles and publications directly from the UWI website.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python, Django |
| Frontend | HTML, Tailwind CSS, JavaScript |
| Database | SQLite |
| Web Server | Gunicorn |
| Deployment | Render.com |

---

## Project Structure

```
Company8-SAR-Platform/
│
├── Annual_Reporting_Platform/       # Main Django project folder
│   ├── reports/                     # Public-facing report listings, filtering, and data models
│   │   └── models.py                # Report, Category, Committee, Participant
│   ├── users/                       # Authentication, profiles, and report CRUD views
│   ├── templates/                   # Base HTML templates and layouts
│   └── static/                      # Static assets (images, etc.)
│
├── HTML_CSS_JAVASCRIPT/             # Initial mockups and data scraping scripts
│   ├── scrape_staff.py
│   └── scrape_publications.py
│
├── render.yaml                      # Render.com deployment configuration
├── build.sh                         # Production build script
└── requirements.txt
```

---

## Local Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Company8-SAR-Platform
```

### 2. Create and Activate a Virtual Environment

**macOS / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Apply Database Migrations

This creates the `db.sqlite3` file and sets up the database schema.

```bash
python manage.py migrate
```

### 5. Create a Superuser *(Optional)*

Grants access to the Django admin panel at `/admin/`.

```bash
python manage.py createsuperuser
```

### 6. Run the Development Server

```bash
python manage.py runserver
```

### 7. Access the Application

Open your browser and navigate to:
```
http://127.0.0.1:8000/reports/
```

---

## Data Scraping

The repository includes scripts to populate the database with initial data from the UWI website.

| Script | Description |
|---|---|
| `scrape_staff.py` | Scrapes the DCIT staff directory to create User accounts and profiles |
| `scrape_publications.py` | Scrapes the DCIT publications page to create Report objects categorised as *Publication* |

Ensure your virtual environment is active, then run from the project root:

```bash
python ../HTML_CSS_JAVASCRIPT/scrape_staff.py
python ../HTML_CSS_JAVASCRIPT/scrape_publications.py
```

---

## Deployment

This project is configured for deployment on **[Render.com](https://render.com)**.

- **`render.yaml`** — Defines the web service configuration.
- **`build.sh`** — Automates the production setup by:
  - Installing Python dependencies
  - Collecting all static files
  - Applying database migrations

The application is served via **Gunicorn**, a production-ready WSGI HTTP server. The `SECRET_KEY` and other sensitive environment variables are managed through Render's secret management system.

# DataGuard — Intelligent Data Quality & EDA Platform

DataGuard is a Flask-based Progressive Web App that helps users upload CSV/Excel datasets, automatically profile data quality, explore EDA insights, identify common data issues, apply smart cleaning rules, and generate professional reports. It also includes a role-based admin portal with user, dataset and audit-log management.

## ✨ Highlights

- CSV and XLSX upload (up to 10 MB)
- Automated dataset profiling
- Data quality score with completeness, uniqueness, outlier safety, validity and structure indicators
- Missing-value, duplicate and outlier detection
- Column Explorer with detailed statistics
- Automatic EDA summaries
- Automatic distribution, categorical and relationship charts
- Correlation matrix for numeric features
- Dataset preview
- Smart cleaning: duplicate removal, missing-value treatment and IQR-based outlier clipping
- Download cleaned datasets
- Professional quality report + printable report view
- Analysis history and quality timeline
- User registration/login with hashed passwords
- Role-based admin portal
- Admin dataset and user management
- Audit activity log
- Progressive Web App manifest + service worker
- Vercel-friendly Flask entry point

## 🧰 Tech Stack

- Python 3.12+
- Flask
- Pandas
- OpenPyXL
- HTML5 / CSS3
- JavaScript
- Chart.js
- SQLite (local/demo persistence)
- PWA APIs

## 📁 Project Structure

```text
DataGuard/
├── app.py
├── database.py
├── requirements.txt
├── sample_dataset.csv
├── templates/
│   ├── dashboard.html
│   ├── datasets.html
│   ├── dataset_details.html
│   ├── report.html
│   ├── login.html
│   ├── register.html
│   ├── profile.html
│   └── admin/
│       ├── dashboard.html
│       ├── users.html
│       ├── datasets.html
│       └── activity.html
└── static/
    ├── css/style.css
    ├── js/app.js
    ├── manifest.json
    ├── service-worker.js
    └── icons/
```

## 🚀 Run Locally

### 1. Create a virtual environment

```powershell
python -m venv .venv
```

### 2. Activate it on Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Start the app

```powershell
python app.py
```

Open `http://127.0.0.1:5000`.

## 🔐 Admin Configuration

For local development, DataGuard creates an administrator if no admin exists. The defaults are intended for local development only:

- Username: `admin`
- Email: `admin@dataguard.local`
- Password: `Admin@12345`

**Do not use these defaults on a public deployment.** Set these environment variables instead:

```text
DATAGUARD_SECRET_KEY=<long-random-secret>
DATAGUARD_ADMIN_USERNAME=<admin-username>
DATAGUARD_ADMIN_EMAIL=<admin-email>
DATAGUARD_ADMIN_PASSWORD=<strong-password>
```

## 🔎 How Analysis Works

### Quality Score

The quality score combines:

- Completeness — 35%
- Uniqueness — 20%
- Outlier safety — 20%
- Validity — 15%
- Structure — 10%

### Outlier Detection

Numeric columns use the IQR rule:

```text
Lower bound = Q1 - 1.5 × IQR
Upper bound = Q3 + 1.5 × IQR
```

### Smart Cleaning

DataGuard can create a cleaned CSV by:

1. Removing exact duplicate rows
2. Filling numeric missing values with the median
3. Filling text missing values with the most frequent value
4. Clipping numeric IQR outliers to the calculated bounds

The original dataset is not overwritten.

## 📊 EDA

The analysis workspace can show:

- Dataset statistics
- Numeric distributions
- Top categorical values
- Scatter relationships between the first two numeric columns
- Correlation matrix
- Column-level statistics
- First-record preview

## 🌐 Deployment

The application can be deployed to a Python-compatible host. Vercel can run the Flask application using its Python runtime.

For the current demo architecture, Vercel uses temporary filesystem storage for SQLite/uploads. This is suitable for demonstrations but **not production-grade persistence**. For a production release, replace local SQLite/file storage with a managed database and persistent object storage.

## 🔒 Security Notes

- Passwords are hashed with Werkzeug's password hashing utilities.
- Admin routes use role-based authorization.
- Uploaded filenames are sanitized with `secure_filename`.
- `.env`, database files and uploaded/generated files are excluded from Git.
- Set a strong `DATAGUARD_SECRET_KEY` in deployment.

## 📌 Future Enhancements

Possible future additions include managed cloud database storage, persistent object storage, scheduled analyses, richer report exports, configurable cleaning rules and team workspaces.

## 👨‍💻 Project

**DataGuard — Intelligent Data Quality & EDA Platform**

Built with Flask, Python, Pandas, JavaScript and PWA technologies.

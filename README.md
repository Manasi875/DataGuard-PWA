# 🛡️ DataGuard

### Advanced Data Quality, Cleaning & Exploratory Data Analysis Platform

DataGuard is a web-based data analysis platform that helps users upload datasets, automatically evaluate their quality, identify data problems, clean the data, and understand their datasets through interactive analysis and visualizations.

It is designed to make data preprocessing and exploratory data analysis easier without requiring users to write complex Python code.

---

## 🚀 Features

### 📂 Dataset Upload

Upload datasets directly through the dashboard.

- CSV files
- Excel XLSX files
- Automatic dataset profiling
- Dataset preview
- File information and statistics

---

### 📊 Advanced Exploratory Data Analysis

DataGuard automatically analyzes uploaded datasets and provides useful insights such as:

- Number of rows and columns
- Data types
- Missing values
- Duplicate records
- Unique values
- Numeric statistics
- Categorical analysis
- Outlier detection
- Column-level insights
- Statistical summaries

---

### 📈 Automatic Data Visualization

DataGuard generates visualizations to help understand the dataset.

Supported analysis includes:

- Histograms
- Categorical bar charts
- Scatter plots
- Correlation analysis
- Numeric distributions
- Category distributions

Charts are generated automatically based on the structure of the uploaded dataset.

---

### 🔍 Column Explorer

Explore individual dataset columns and understand:

- Data type
- Missing values
- Unique values
- Statistical information
- Outliers
- Value distributions

This makes it easier to identify problematic columns and understand the structure of the data.

---

### 🧹 Smart Data Cleaning

DataGuard provides automated data-cleaning operations including:

- Duplicate removal
- Missing-value treatment
- Outlier handling
- IQR-based outlier clipping
- Data quality improvement

The goal is to make datasets cleaner and more suitable for further analysis or machine-learning workflows.

---

### 🎯 Data Quality Score

Each dataset receives an overall quality score based on detected data-quality problems.

The platform evaluates factors such as:

- Missing data
- Duplicate records
- Outliers
- Dataset structure

The dashboard provides a quick overview of the dataset's health.

---

### 💡 Smart Recommendations

DataGuard provides recommendations based on detected problems in the dataset.

For example:

- Remove duplicate records
- Investigate missing values
- Review columns containing outliers
- Check inconsistent data types
- Examine suspicious values

This helps users understand what should be fixed before using the dataset.

---

### 📄 Data Analysis Reports

Generate analysis reports containing important information about the dataset.

Reports can include:

- Dataset statistics
- Data-quality metrics
- Missing-value information
- Duplicate information
- Outlier information
- Column details
- Cleaning results

---

### 👤 User Authentication

DataGuard supports user accounts with:

- Registration
- Login
- Logout
- User profiles
- User-specific datasets
- Analysis history

---

### 🛠️ Admin Portal

Administrators can manage the platform through a dedicated admin portal.

Admin functionality includes:

- User management
- Dataset management
- User roles
- Dataset deletion
- Activity monitoring
- Analysis history
- Audit logs

---

### 📜 Analysis History

DataGuard keeps track of dataset analysis activities.

Users can review previous analysis operations and quality information associated with their datasets.

---

### 📱 Progressive Web App

DataGuard is built as a Progressive Web App.

It includes:

- Responsive interface
- Mobile-friendly design
- PWA manifest
- Service worker
- Installable web application

---

## 🏗️ Technology Stack

### Frontend

- HTML5
- CSS3
- JavaScript
- Chart.js
- Responsive UI
- Progressive Web App technologies

### Backend

- Python
- Flask
- Pandas
- OpenPyXL

### Database

- SQLite

### Deployment

- Vercel

---

## 📁 Project Structure

DataGuard-PWA/
│
├── app.py
├── database.py
├── requirements.txt
├── vercel.json
│
├── templates/
│   ├── dashboard.html
│   ├── dataset_details.html
│   ├── login.html
│   ├── register.html
│   ├── profile.html
│   └── admin/
│
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   ├── icons/
│   ├── manifest.json
│   └── sw.js
│
├── uploads/
├── reports/
│
└── README.md

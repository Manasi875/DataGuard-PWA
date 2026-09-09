import json
import os
import uuid
from functools import wraps
from pathlib import Path

import pandas as pd
from flask import Flask, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from database import get_connection, init_db

BASE_DIR = Path(__file__).resolve().parent
if os.environ.get('VERCEL'):
    UPLOAD_FOLDER = Path('/tmp/uploads')
    REPORT_FOLDER = Path('/tmp/reports')
else:
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    REPORT_FOLDER = BASE_DIR / 'reports'
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
REPORT_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
MAX_FILE_SIZE = 10 * 1024 * 1024

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('DATAGUARD_SECRET_KEY', 'dataguard-development-secret-change-this')
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Administrator access is required.', 'danger')
            return redirect(url_for('dashboard'))
        return view(*args, **kwargs)
    return wrapped


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def load_dataframe(file_path):
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f'Dataset file not found: {file_path}')
    extension = file_path.suffix.lower()
    if extension == '.csv':
        try:
            return pd.read_csv(file_path)
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding='latin-1')
    if extension == '.xlsx':
        return pd.read_excel(file_path)
    raise ValueError('Unsupported file format. Only CSV and XLSX are supported.')


def get_dataset_file_path(dataset):
    """Resolve dataset files across current and legacy local upload paths."""
    stored_name = str(dataset['stored_name'] or '').strip()
    original_name = str(dataset['original_name'] or '').strip()
    candidates = []

    if stored_name:
        stored = Path(stored_name)
        if stored.is_absolute():
            candidates.append(stored)
        else:
            candidates.extend([
                UPLOAD_FOLDER / stored,
                BASE_DIR / stored,
                BASE_DIR / 'uploads' / stored.name,
            ])

    if original_name:
        original = Path(original_name)
        if original.is_absolute():
            candidates.append(original)
        else:
            candidates.extend([
                UPLOAD_FOLDER / original.name,
                BASE_DIR / 'uploads' / original.name,
            ])

    seen = set()
    for candidate in candidates:
        candidate = Path(candidate)
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists() and candidate.is_file():
            return candidate

    if stored_name:
        return UPLOAD_FOLDER / Path(stored_name).name
    if original_name:
        return UPLOAD_FOLDER / Path(original_name).name
    return None


def calculate_outlier_bounds(series):
    numeric = pd.to_numeric(series, errors='coerce').dropna()
    if len(numeric) < 4:
        return None
    q1, q3 = numeric.quantile(0.25), numeric.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return None
    return float(q1 - 1.5 * iqr), float(q3 + 1.5 * iqr)


def calculate_outliers(series):
    bounds = calculate_outlier_bounds(series)
    if not bounds:
        return 0
    numeric = pd.to_numeric(series, errors='coerce')
    return int(((numeric < bounds[0]) | (numeric > bounds[1])).sum())


def detect_data_type(series):
    if pd.api.types.is_numeric_dtype(series):
        return 'Numeric'
    if pd.api.types.is_datetime64_any_dtype(series):
        return 'Date / Time'
    # Detect date-like text without changing the source dataframe.
    if series.dtype == 'object' and len(series.dropna()) >= 3:
        converted = pd.to_datetime(series.dropna(), errors='coerce')
        if converted.notna().mean() >= 0.9:
            return 'Date / Time'
    return 'Text'


def _safe_number(value):
    try:
        value = float(value)
        if pd.isna(value) or value in (float('inf'), float('-inf')):
            return None
        return round(value, 4)
    except Exception:
        return None


def profile_dataframe(df):
    rows, columns = len(df), len(df.columns)
    total_cells = rows * columns
    missing_count = int(df.isna().sum().sum())
    duplicate_count = int(df.duplicated().sum())
    column_profiles = []
    total_outliers = 0
    numeric_cells = 0
    mixed_type_columns = 0

    for column in df.columns:
        series = df[column]
        missing = int(series.isna().sum())
        unique = int(series.nunique(dropna=True))
        data_type = detect_data_type(series)
        outliers = calculate_outliers(series) if data_type == 'Numeric' else 0
        if data_type == 'Numeric':
            numeric_cells += int(series.notna().sum())
        elif series.dtype == 'object' and len(series.dropna()) > 0:
            numeric_ratio = pd.to_numeric(series, errors='coerce').notna().mean()
            if 0.15 < numeric_ratio < 0.9:
                mixed_type_columns += 1
        total_outliers += outliers
        column_profiles.append({
            'name': str(column), 'data_type': data_type, 'missing': missing,
            'unique': unique, 'outliers': outliers,
            'missing_pct': round((missing / rows * 100) if rows else 0, 2),
        })

    completeness = 100 if total_cells == 0 else 100 * (1 - missing_count / total_cells)
    uniqueness = 100 if rows == 0 else 100 * (1 - duplicate_count / rows)
    outlier_score = 100 if numeric_cells == 0 else 100 * (1 - min(total_outliers / numeric_cells, 1))
    validity = 100 if columns == 0 else max(0, 100 - (mixed_type_columns / columns * 100))
    structure_score = 100 if rows > 0 and columns > 0 else 0
    quality_score = round(max(0, min(completeness * .35 + uniqueness * .20 + outlier_score * .20 + validity * .15 + structure_score * .10, 100)), 1)

    return {
        'rows': rows, 'columns': columns, 'missing': missing_count, 'duplicates': duplicate_count,
        'outliers': total_outliers, 'quality': quality_score,
        'completeness': round(completeness, 1), 'uniqueness': round(uniqueness, 1),
        'outlier_score': round(outlier_score, 1), 'validity': round(validity, 1),
        'structure_score': round(structure_score, 1), 'mixed_type_columns': mixed_type_columns,
        'column_profiles': column_profiles,
    }


def quality_label(score):
    if score >= 90:
        return 'Excellent'
    if score >= 75:
        return 'Good'
    if score >= 60:
        return 'Needs Attention'
    return 'Critical'


def recommendations(profile):
    items = []
    if profile['missing']:
        items.append({'level': 'warning', 'title': f"{profile['missing']:,} missing cells detected", 'text': 'Fill numeric gaps with median values and categorical gaps with the most frequent value.'})
    if profile['duplicates']:
        items.append({'level': 'danger', 'title': f"{profile['duplicates']:,} duplicate rows found", 'text': 'Remove exact duplicates before downstream analysis to avoid biased results.'})
    if profile['outliers']:
        items.append({'level': 'warning', 'title': f"{profile['outliers']:,} potential outlier flags", 'text': 'Review extreme numeric values and clip or investigate them before reporting.'})
    if profile['mixed_type_columns']:
        items.append({'level': 'danger', 'title': f"{profile['mixed_type_columns']} mixed-type columns", 'text': 'Standardize inconsistent values so each column has a predictable data type.'})
    if not items:
        items.append({'level': 'success', 'title': 'No major quality issues detected', 'text': 'The dataset is ready for analysis based on DataGuard quality rules.'})
    return items


def build_eda(df):
    numeric_cols = [str(c) for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    categorical_cols = [str(c) for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
    summary = []
    for col in df.columns:
        s = df[col]
        row = {
            'name': str(col), 'type': detect_data_type(s), 'count': int(s.notna().sum()),
            'missing': int(s.isna().sum()), 'unique': int(s.nunique(dropna=True))
        }
        if pd.api.types.is_numeric_dtype(s):
            row.update({'mean': _safe_number(s.mean()), 'median': _safe_number(s.median()), 'std': _safe_number(s.std()), 'min': _safe_number(s.min()), 'max': _safe_number(s.max())})
        else:
            mode = s.mode(dropna=True)
            row.update({'top': str(mode.iloc[0]) if not mode.empty else '—'})
        summary.append(row)

    corr = []
    if len(numeric_cols) >= 2:
        matrix = df[numeric_cols].corr(numeric_only=True).round(2).fillna(0)
        for r in numeric_cols:
            corr.append({'name': r, 'values': [float(matrix.loc[r, c]) for c in numeric_cols]})

    charts = []
    # Distribution chart for the first numeric column.
    if numeric_cols:
        col = numeric_cols[0]
        values = pd.to_numeric(df[col], errors='coerce').dropna()
        if not values.empty:
            counts, edges = pd.cut(values, bins=min(8, max(3, values.nunique())), retbins=True, duplicates='drop')
            hist = values.groupby(counts, observed=False).size()
            labels = [f'{_safe_number(edges[i])}–{_safe_number(edges[i+1])}' for i in range(len(edges)-1)]
            charts.append({'kind': 'bar', 'title': f'{col} distribution', 'labels': labels, 'values': [int(x) for x in hist.tolist()]})
    if categorical_cols:
        col = categorical_cols[0]
        counts = df[col].fillna('Missing').astype(str).value_counts().head(8)
        charts.append({'kind': 'bar', 'title': f'{col} — top values', 'labels': counts.index.tolist(), 'values': [int(x) for x in counts.tolist()]})
    if len(numeric_cols) >= 2:
        x, y = numeric_cols[:2]
        points = df[[x, y]].dropna().head(250)
        charts.append({'kind': 'scatter', 'title': f'{x} vs {y}', 'x': [_safe_number(v) for v in points[x]], 'y': [_safe_number(v) for v in points[y]]})
    return {'numeric_cols': numeric_cols, 'categorical_cols': categorical_cols, 'summary': summary, 'correlation_columns': numeric_cols, 'correlation': corr, 'charts': charts}


def column_insights(df):
    result = {}
    for col in df.columns:
        s = df[col]
        dtype = detect_data_type(s)
        item = {'name': str(col), 'type': dtype, 'missing': int(s.isna().sum()), 'unique': int(s.nunique(dropna=True)), 'outliers': calculate_outliers(s) if dtype == 'Numeric' else 0}
        if dtype == 'Numeric':
            item.update({'mean': _safe_number(s.mean()), 'median': _safe_number(s.median()), 'min': _safe_number(s.min()), 'max': _safe_number(s.max()), 'std': _safe_number(s.std())})
        else:
            mode = s.mode(dropna=True)
            item['top'] = str(mode.iloc[0]) if not mode.empty else '—'
        result[str(col)] = item
    return result


def log_action(user_id, action, details=''):
    conn = get_connection()
    conn.execute('INSERT INTO audit_logs(user_id, action, details) VALUES(?,?,?)', (user_id, action, details))
    conn.commit()
    conn.close()


def record_history(dataset_id, action, profile):
    conn = get_connection()
    conn.execute('INSERT INTO analysis_history(dataset_id, action, quality_score, missing_count, duplicate_count, outlier_count) VALUES(?,?,?,?,?,?)', (dataset_id, action, profile['quality'], profile['missing'], profile['duplicates'], profile['outliers']))
    conn.commit()
    conn.close()


@app.context_processor
def inject_globals():
    return {'quality_label': quality_label}


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard' if session.get('role') == 'admin' else 'dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        if len(password) < 6:
            flash('Password must contain at least 6 characters.', 'danger')
            return render_template('register.html')
        conn = get_connection()
        try:
            conn.execute('INSERT INTO users(username,email,password_hash) VALUES(?,?,?)', (username, email, generate_password_hash(password)))
            conn.commit()
            flash('Account created successfully. You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception:
            flash('Username or email already exists.', 'danger')
        finally:
            conn.close()
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        identity = request.form.get('identity', '').strip().lower()
        password = request.form.get('password', '')
        conn = get_connection()
        user = conn.execute('SELECT * FROM users WHERE lower(username)=? OR lower(email)=?', (identity, identity)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session.clear(); session['user_id'] = user['id']; session['username'] = user['username']; session['role'] = user['role']
            log_action(user['id'], 'LOGIN', 'Successful sign-in')
            return redirect(url_for('admin_dashboard' if user['role'] == 'admin' else 'dashboard'))
        flash('Invalid username/email or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        log_action(user_id, 'LOGOUT', 'User signed out')
    session.clear(); flash('You have been logged out.', 'success'); return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    conn = get_connection()
    datasets = conn.execute('SELECT * FROM datasets WHERE user_id=? ORDER BY id DESC', (session['user_id'],)).fetchall()
    stats = conn.execute('''SELECT COUNT(*) dataset_count, COALESCE(SUM(rows_count),0) record_count, COALESCE(SUM(missing_count),0) missing_count, COALESCE(SUM(duplicate_count),0) duplicate_count, COALESCE(SUM(outlier_count),0) outlier_count, COALESCE(AVG(quality_score),0) avg_quality FROM datasets WHERE user_id=?''', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('dashboard.html', stats=stats, datasets=datasets, recent=datasets[:6])


@app.route('/upload', methods=['POST'])
@login_required
def upload():
    uploaded_file = request.files.get('dataset')
    if not uploaded_file or not uploaded_file.filename:
        flash('Please choose a CSV or XLSX file.', 'danger'); return redirect(url_for('dashboard'))
    if not allowed_file(uploaded_file.filename):
        flash('Only CSV and XLSX files are supported.', 'danger'); return redirect(url_for('dashboard'))
    original_name = secure_filename(uploaded_file.filename)
    unique_name = f'{uuid.uuid4().hex}_{original_name}'
    save_path = UPLOAD_FOLDER / unique_name
    uploaded_file.save(save_path)
    try:
        df = load_dataframe(save_path)
        if df.empty or len(df.columns) == 0:
            raise ValueError('The dataset is empty.')
        profile = profile_dataframe(df)
    except Exception as error:
        save_path.unlink(missing_ok=True); flash(f'Could not analyze dataset: {error}', 'danger'); return redirect(url_for('dashboard'))
    conn = get_connection()
    cursor = conn.execute('''INSERT INTO datasets(user_id,original_name,stored_name,rows_count,columns_count,missing_count,duplicate_count,outlier_count,quality_score) VALUES(?,?,?,?,?,?,?,?,?)''', (session['user_id'], original_name, unique_name, profile['rows'], profile['columns'], profile['missing'], profile['duplicates'], profile['outliers'], profile['quality']))
    dataset_id = cursor.lastrowid
    for c in profile['column_profiles']:
        conn.execute('INSERT INTO columns_profile(dataset_id,column_name,data_type,missing_count,unique_count,outlier_count) VALUES(?,?,?,?,?,?)', (dataset_id, c['name'], c['data_type'], c['missing'], c['unique'], c['outliers']))
    conn.commit(); conn.close()
    record_history(dataset_id, 'Initial analysis', profile)
    log_action(session['user_id'], 'DATASET_ANALYZED', original_name)
    flash(f'{original_name} analyzed successfully. Quality score: {profile["quality"]}%.', 'success')
    return redirect(url_for('dataset_details', dataset_id=dataset_id))


@app.route('/datasets')
@login_required
def datasets():
    conn = get_connection(); rows = conn.execute('SELECT * FROM datasets WHERE user_id=? ORDER BY id DESC', (session['user_id'],)).fetchall(); conn.close()
    return render_template('datasets.html', datasets=rows)


def get_owned_dataset(dataset_id):
    conn = get_connection(); dataset = conn.execute('SELECT * FROM datasets WHERE id=? AND user_id=?', (dataset_id, session['user_id'])).fetchone(); conn.close(); return dataset


@app.route('/dataset/<int:dataset_id>')
@login_required
def dataset_details(dataset_id):
    dataset = get_owned_dataset(dataset_id)
    if not dataset:
        flash('Dataset not found.', 'danger')
        return redirect(url_for('datasets'))

    conn = get_connection()
    columns = conn.execute(
        'SELECT * FROM columns_profile WHERE dataset_id=? ORDER BY id',
        (dataset_id,)
    ).fetchall()
    history = conn.execute(
        'SELECT * FROM analysis_history WHERE dataset_id=? ORDER BY id DESC LIMIT 10',
        (dataset_id,)
    ).fetchall()
    conn.close()

    path = get_dataset_file_path(dataset)
    eda = {
        'summary': [], 'numeric_cols': [], 'categorical_cols': [],
        'correlation_columns': [], 'correlation': [], 'charts': []
    }
    preview = []
    column_insight = {}
    available = bool(path and path.exists())

    if available:
        try:
            df = load_dataframe(path)
            if df.empty or len(df.columns) == 0:
                raise ValueError('The dataset is empty.')
            eda = build_eda(df)
            preview = json.loads(
                df.head(8).fillna('').to_json(orient='records', date_format='iso')
            )
            column_insight = column_insights(df)
        except Exception as error:
            print(f'[DataGuard] Dataset {dataset_id} analysis error: {error}')
            available = False

    recommendation_profile = {
        'missing': dataset['missing_count'],
        'duplicates': dataset['duplicate_count'],
        'outliers': dataset['outlier_count'],
        'mixed_type_columns': 0
    }

    return render_template(
        'dataset_details.html', dataset=dataset, columns=columns,
        history=history, recommendations=recommendations(recommendation_profile),
        eda=eda, preview=preview, column_insight=column_insight,
        file_available=available
    )


@app.route('/dataset/<int:dataset_id>/eda-data')
@login_required
def eda_data(dataset_id):
    dataset = get_owned_dataset(dataset_id)
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404
    path = get_dataset_file_path(dataset)
    if not path or not path.exists():
        return jsonify({'error': 'Dataset file is unavailable.'}), 404
    try:
        df = load_dataframe(path)
        return jsonify({
            'success': True,
            'eda': build_eda(df),
            'preview': json.loads(df.head(8).fillna('').to_json(orient='records', date_format='iso')),
            'column_insight': column_insights(df)
        })
    except Exception as error:
        return jsonify({'error': str(error)}), 400


@app.route('/dataset/<int:dataset_id>/download')
@login_required
def download_dataset(dataset_id):
    dataset = get_owned_dataset(dataset_id)
    if not dataset: flash('Dataset not found.', 'danger'); return redirect(url_for('datasets'))
    path = get_dataset_file_path(dataset)
    if not path.exists():
        flash('Original dataset file is missing from the temporary storage.', 'danger'); return redirect(url_for('dataset_details', dataset_id=dataset_id))
    return send_file(path, as_attachment=True, download_name=dataset['original_name'])


@app.route('/dataset/<int:dataset_id>/clean', methods=['POST'])
@login_required
def clean_dataset(dataset_id):
    dataset = get_owned_dataset(dataset_id)
    if not dataset: flash('Dataset not found.', 'danger'); return redirect(url_for('datasets'))
    original_path = get_dataset_file_path(dataset)
    if not original_path.exists():
        flash('Original dataset file is unavailable.', 'danger'); return redirect(url_for('dataset_details', dataset_id=dataset_id))
    try:
        df = load_dataframe(original_path)
        before_rows = len(df); before_missing = int(df.isna().sum().sum()); before_duplicates = int(df.duplicated().sum()); outlier_changes = 0
        df = df.drop_duplicates().copy()
        for column in df.columns:
            s = df[column]
            if s.isna().any():
                if pd.api.types.is_numeric_dtype(s):
                    value = s.median()
                    if pd.notna(value): df[column] = s.fillna(value)
                else:
                    mode = s.mode(dropna=True)
                    if not mode.empty: df[column] = s.fillna(mode.iloc[0])
        for column in df.select_dtypes(include='number').columns:
            bounds = calculate_outlier_bounds(df[column])
            if bounds:
                original = df[column].copy()
                df[column] = df[column].clip(lower=bounds[0], upper=bounds[1])
                outlier_changes += int((original != df[column]).sum())
        cleaned_name = f'cleaned_{Path(dataset["original_name"]).stem}.csv'
        cleaned_path = REPORT_FOLDER / f'{uuid.uuid4().hex}_{cleaned_name}'
        df.to_csv(cleaned_path, index=False)
        log_action(session['user_id'], 'DATASET_CLEANED', f'{dataset["original_name"]}: {before_duplicates} duplicates removed, {outlier_changes} outliers clipped')
        flash(f'Cleaned dataset ready: {before_rows-len(df):,} duplicate rows removed, {before_missing:,} missing cells treated, {outlier_changes:,} outlier values clipped.', 'success')
        return send_file(cleaned_path, as_attachment=True, download_name=cleaned_name)
    except Exception as error:
        flash(f'Cleaning failed: {error}', 'danger'); return redirect(url_for('dataset_details', dataset_id=dataset_id))


@app.route('/dataset/<int:dataset_id>/report')
@login_required
def report(dataset_id):
    dataset = get_owned_dataset(dataset_id)
    if not dataset: flash('Dataset not found.', 'danger'); return redirect(url_for('datasets'))
    conn = get_connection(); columns = conn.execute('SELECT * FROM columns_profile WHERE dataset_id=? ORDER BY id', (dataset_id,)).fetchall(); history = conn.execute('SELECT * FROM analysis_history WHERE dataset_id=? ORDER BY id DESC', (dataset_id,)).fetchall(); conn.close()
    return render_template('report.html', dataset=dataset, columns=columns, history=history)


@app.route('/dataset/<int:dataset_id>/report/download')
@login_required
def download_report(dataset_id):
    dataset = get_owned_dataset(dataset_id)
    if not dataset: flash('Dataset not found.', 'danger'); return redirect(url_for('datasets'))
    conn = get_connection(); columns = conn.execute('SELECT * FROM columns_profile WHERE dataset_id=? ORDER BY id', (dataset_id,)).fetchall(); conn.close()
    lines = ['DATAGUARD — DATA QUALITY REPORT', '=' * 55, f'Dataset: {dataset["original_name"]}', f'Quality score: {dataset["quality_score"]}%', f'Rating: {quality_label(dataset["quality_score"])}', f'Rows: {dataset["rows_count"]:,}', f'Columns: {dataset["columns_count"]}', f'Missing cells: {dataset["missing_count"]:,}', f'Duplicates: {dataset["duplicate_count"]:,}', f'Outlier flags: {dataset["outlier_count"]:,}', '', 'COLUMN PROFILE', '-' * 55]
    for c in columns: lines += [f'Column: {c["column_name"]}', f'  Type: {c["data_type"]}', f'  Missing: {c["missing_count"]}', f'  Unique: {c["unique_count"]}', f'  Outliers: {c["outlier_count"]}', '']
    path = REPORT_FOLDER / f'report_{dataset_id}.txt'; path.write_text('\n'.join(lines), encoding='utf-8')
    return send_file(path, as_attachment=True, download_name=f'DataGuard_Report_{dataset_id}.txt')


# ---------------- ADMIN ----------------
@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_connection()
    stats = conn.execute('''SELECT (SELECT COUNT(*) FROM users) user_count, (SELECT COUNT(*) FROM datasets) dataset_count, (SELECT COALESCE(SUM(rows_count),0) FROM datasets) record_count, (SELECT COALESCE(AVG(quality_score),0) FROM datasets) avg_quality, (SELECT COUNT(*) FROM analysis_history) analysis_count, (SELECT COUNT(*) FROM audit_logs) activity_count''').fetchone()
    recent_users = conn.execute('SELECT id,username,email,role,created_at FROM users ORDER BY id DESC LIMIT 8').fetchall()
    recent_datasets = conn.execute('SELECT d.*,u.username FROM datasets d JOIN users u ON u.id=d.user_id ORDER BY d.id DESC LIMIT 8').fetchall()
    quality_bands = conn.execute('SELECT SUM(CASE WHEN quality_score>=90 THEN 1 ELSE 0 END) excellent, SUM(CASE WHEN quality_score>=75 AND quality_score<90 THEN 1 ELSE 0 END) good, SUM(CASE WHEN quality_score>=60 AND quality_score<75 THEN 1 ELSE 0 END) attention, SUM(CASE WHEN quality_score<60 THEN 1 ELSE 0 END) critical FROM datasets').fetchone()
    conn.close()
    return render_template('admin/dashboard.html', stats=stats, recent_users=recent_users, recent_datasets=recent_datasets, quality_bands=quality_bands)


@app.route('/admin/users')
@admin_required
def admin_users():
    conn = get_connection(); users = conn.execute('SELECT u.id,u.username,u.email,u.role,u.created_at,COUNT(d.id) dataset_count FROM users u LEFT JOIN datasets d ON d.user_id=u.id GROUP BY u.id ORDER BY u.id DESC').fetchall(); conn.close(); return render_template('admin/users.html', users=users)


@app.route('/admin/users/<int:user_id>/role', methods=['POST'])
@admin_required
def admin_change_role(user_id):
    if user_id == session['user_id']:
        flash('You cannot change your own administrator role.', 'warning'); return redirect(url_for('admin_users'))
    role = request.form.get('role', 'user')
    if role not in {'user', 'admin'}:
        flash('Invalid role.', 'danger'); return redirect(url_for('admin_users'))
    conn = get_connection(); cursor = conn.execute('UPDATE users SET role=? WHERE id=?', (role, user_id)); conn.commit(); conn.close(); log_action(session['user_id'], 'ROLE_CHANGED', f'User {user_id} -> {role}'); flash('User role updated.' if cursor.rowcount else 'User not found.', 'success' if cursor.rowcount else 'danger'); return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    if user_id == session['user_id']:
        flash('You cannot delete your own administrator account.', 'warning'); return redirect(url_for('admin_users'))
    conn = get_connection(); datasets = conn.execute('SELECT stored_name FROM datasets WHERE user_id=?', (user_id,)).fetchall(); cursor = conn.execute('DELETE FROM users WHERE id=?', (user_id,)); conn.commit(); conn.close()
    for d in datasets: (UPLOAD_FOLDER / d['stored_name']).unlink(missing_ok=True)
    log_action(session['user_id'], 'USER_DELETED', f'User {user_id}')
    flash('User deleted successfully.' if cursor.rowcount else 'User not found.', 'success' if cursor.rowcount else 'danger'); return redirect(url_for('admin_users'))


@app.route('/admin/datasets')
@admin_required
def admin_datasets():
    conn = get_connection(); rows = conn.execute('SELECT d.*,u.username,u.email FROM datasets d JOIN users u ON u.id=d.user_id ORDER BY d.id DESC').fetchall(); conn.close(); return render_template('admin/datasets.html', datasets=rows)


@app.route('/admin/datasets/<int:dataset_id>/delete', methods=['POST'])
@admin_required
def admin_delete_dataset(dataset_id):
    conn = get_connection(); dataset = conn.execute('SELECT stored_name,original_name FROM datasets WHERE id=?', (dataset_id,)).fetchone()
    if not dataset: conn.close(); flash('Dataset not found.', 'danger'); return redirect(url_for('admin_datasets'))
    conn.execute('DELETE FROM datasets WHERE id=?', (dataset_id,)); conn.commit(); conn.close(); (UPLOAD_FOLDER / dataset['stored_name']).unlink(missing_ok=True); log_action(session['user_id'], 'DATASET_DELETED', dataset['original_name']); flash('Dataset deleted successfully.', 'success'); return redirect(url_for('admin_datasets'))


@app.route('/admin/activity')
@admin_required
def admin_activity():
    conn = get_connection(); logs = conn.execute('SELECT a.*,u.username FROM audit_logs a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 200').fetchall(); conn.close(); return render_template('admin/activity.html', logs=logs)


@app.route('/profile')
@login_required
def profile():
    conn = get_connection(); user = conn.execute('SELECT id,username,email,role,created_at FROM users WHERE id=?', (session['user_id'],)).fetchone(); conn.close(); return render_template('profile.html', user=user)


@app.route('/service-worker.js')
def service_worker():
    return send_file(BASE_DIR / 'static' / 'service-worker.js', mimetype='application/javascript')


# Import-time initialization is required for Vercel's Flask runtime.
init_db()

if __name__ == '__main__':
    app.run(debug=True)

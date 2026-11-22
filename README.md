# Student AI Performance & Placement Prediction System

A full-stack academic analytics prototype using React + Vite, FastAPI, scikit-learn and MySQL. It compares an individual student's latest inputs with the supplied student dataset, estimates an exam score, predicts a placement-status label, and provides separate student/admin experiences.

## Main capabilities
- Student registration and login; student accounts see only their own profile, assessments and report.
- Administrator login; admins see student directory, class-level analytics and recent predictions.
- Student-vs-dataset benchmark cards and charts for attendance and average academic score.
- Class distributions for attendance and average score, subject averages, and attendance-vs-score scatter plot.
- Separate Random Forest Regressor for exam-score estimation and Random Forest Classifier for placement-status classification.
- Prediction history and downloadable PDF report for each student.
- MySQL persistence using the five original data tables plus a `users` authentication table.

## Dataset and model definitions
The application uses only `data/StudentsPerformance.csv` from this project. The separately supplied alternate CSV is not used.

The original file has 1,000 records and includes math, reading, writing, study hours, attendance, sleep hours, internet usage, assignments completed and `placement_status`.

- **Placement classification:** RandomForestClassifier. Inputs: `study_hours`, `attendance`, `sleep_hours`, `internet_usage`, `assignments_completed`, `previous_score`.
- **Score regression:** RandomForestRegressor. Target: `exam_score`, defined as the mean of math, reading and writing scores. Inputs: study hours, attendance, sleep hours, internet usage and assignments completed. The derived previous score is deliberately excluded from regression inputs because it is calculated from the same subject scores as the target; including it would leak target information.
- The dataset benchmark is called a **dataset average**, not a verified student's actual classroom average. The source and quality of historical placement labels should be validated before real-world use.

## Windows setup
From the project root in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with your MySQL URL, a long random `APP_SECRET_KEY`, and administrator credentials. Create the database if it does not exist:

```sql
CREATE DATABASE student_ai_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

The first administrator account is created from `ADMIN_EMAIL` and `ADMIN_PASSWORD` on backend startup if it does not already exist. Do not use the example password outside a local demo.

Train both models:

```powershell
python ml\train_model.py
```

Start the API in terminal 1:

```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Start the React app in terminal 2:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL, usually `http://localhost:5173`. API docs: `http://127.0.0.1:8000/docs`.

## First login
- Student: choose **Create an account** on the login page.
- Admin: use the email and password configured in `.env`.

## Database changes
The existing five tables remain: `students`, `academic_records`, `class_status`, `student_background`, and `placement_predictions`. A new `users` table stores account credentials and roles. On startup, the backend adds a nullable `user_id` column to an existing `students` table if it is missing. Existing anonymous/demo student rows are retained and are not automatically assigned to new accounts.

For a production migration, use Alembic rather than relying on the lightweight additive migration included in this local project.

## Important API routes
- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `POST /api/predict` (authenticated)
- `GET /api/me/dashboard`, `PUT /api/me/profile`, `GET /api/me/report.pdf`
- `GET /api/analytics/eda` (authenticated dataset-level analytics)
- `GET /api/admin/dashboard`, `/api/admin/students`, `/api/admin/predictions` (admin only)
- `GET /api/health`, `GET /ml-metadata`

## Security and responsible-use notes
This is a local academic prototype. Passwords are PBKDF2-SHA256 hashed and API sessions use signed bearer tokens. Configure a strong secret, use HTTPS if deployed, add rate limiting, use database migrations, and review security before production. Keep student records private. Model probabilities are estimates, not guarantees or hiring decisions. The placement label provenance and dataset representativeness need independent validation.

### Current regression evaluation note
On the supplied CSV and the fixed 80/20 random split (random_state=42), the lifestyle-only Random Forest Regressor currently produced MAE about 12.48, RMSE about 15.66 and R² about -0.14. A negative R² means it performed worse than predicting the held-out mean. The UI therefore marks this score output as experimental. This dataset does not contain repeated/future exam outcomes for each student; a genuinely useful future-score model needs longitudinal data (prior routine + prior score at time T, followed by a later exam score at time T+1).

# Breathe ESG Ingestion Review Prototype

Django REST plus React prototype for ingesting SAP, utility electricity, and corporate travel CSV data, normalizing it into emissions activity rows, and letting an analyst review, edit, approve, reject, and lock rows.

## Local Setup

Backend:

```powershell
python -m venv .venv
Copy-Item backend\.env.example backend\.env
.venv\Scripts\python -m pip install -r backend\requirements.txt
.venv\Scripts\python backend\manage.py migrate
.venv\Scripts\python backend\manage.py seed_demo
.venv\Scripts\python backend\manage.py runserver 127.0.0.1:8000
```

Frontend:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:5173`. The frontend calls `http://127.0.0.1:8000` by default.

No login is required in the prototype. API calls use the seeded demo tenant `acme-industrial`.

## Sample Data

Use the CSV files in `sample_data/`:

- `sap_fuel_procurement.csv`
- `utility_electricity.csv`
- `travel_expenses.csv`

Upload each with the matching source selector in the UI.

## Validation

```powershell
.venv\Scripts\python backend\manage.py check
.venv\Scripts\python backend\manage.py test review
cd frontend
npm run build
```

## API

- `GET /api/health/`
- `GET /api/facilities/`
- `POST /api/ingestions/upload/`
- `GET /api/dashboard/`
- `GET /api/batches/`
- `GET /api/batches/<id>/raw-records/`
- `GET /api/activities/`
- `GET/PATCH /api/activities/<id>/`
- `POST /api/activities/<id>/approve/`
- `POST /api/activities/<id>/reject/`
- `POST /api/activities/<id>/lock/`

## Required Assignment Docs

- `MODEL.md`
- `DECISIONS.md`
- `TRADEOFFS.md`
- `SOURCES.md`

## Deployment

`render.yaml` is included as a deployable blueprint for a Render backend service, Postgres database, and static frontend.

Use `DEPLOYMENT.md` to deploy the live app.
Use `SUBMISSION_CHECKLIST.md` before sending the assignment email.

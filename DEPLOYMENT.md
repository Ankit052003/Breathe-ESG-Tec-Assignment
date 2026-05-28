# Deployment Guide

The assignment requires a live deployed app. Local-only submission will not be reviewed.

This repository is prepared for Render deployment with `render.yaml`.

## Before Deploying

Push the repository to GitHub. Do not commit `.env`, `db.sqlite3`, `node_modules`, or `frontend/dist`.

## Render Blueprint Deployment

1. Open Render.
2. Go to **Blueprints**.
3. Choose **New Blueprint Instance**.
4. Connect the GitHub repository.
5. Select the root-level `render.yaml`.
6. Apply the blueprint.

The blueprint creates:

- `breathe-esg-api`: Django REST backend.
- `breathe-esg-review`: React static frontend.
- `breathe-esg-db`: Postgres database.

## Environment URLs

The blueprint assumes these Render service URLs:

- Backend: `https://breathe-esg-api.onrender.com`
- Frontend: `https://breathe-esg-review.onrender.com`

If Render gives different service names or URLs, update:

- `ALLOWED_HOSTS` on the backend service.
- `CORS_ALLOWED_ORIGINS` on the backend service.
- `CSRF_TRUSTED_ORIGINS` on the backend service.
- `VITE_API_BASE_URL` on the frontend static service.

Then redeploy the frontend and backend.

## Post-Deploy Verification

1. Open the backend health endpoint:

```text
https://breathe-esg-api.onrender.com/api/health/
```

Expected response:

```json
{"status":"ok"}
```

2. Open the frontend:

```text
https://breathe-esg-review.onrender.com
```

3. Upload each sample file from `sample_data/`:

- `sap_fuel_procurement.csv` as SAP
- `utility_electricity.csv` as Utility
- `travel_expenses.csv` as Travel

4. Verify the review dashboard shows imported rows, failed rows, flagged rows, source mix, and review progress.

5. Open one row, edit it while it is still `normalized` or `needs_review`, approve it, lock it, and confirm later edits are blocked.

## Submission Email

Include:

- GitHub repository link.
- Deployed frontend URL.
- Backend URL if separate.
- State: `No login required; demo tenant is acme-industrial`.
- Mention docs: `MODEL.md`, `DECISIONS.md`, `TRADEOFFS.md`, `SOURCES.md`.


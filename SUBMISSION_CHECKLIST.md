# Submission Checklist

- Push the repository to GitHub.
- Deploy the app using `render.yaml` or equivalent services. See `DEPLOYMENT.md`.
- Verify the deployed frontend loads.
- Verify `GET /api/health/` on the deployed backend returns `{"status":"ok"}`.
- Upload each sample CSV from `sample_data/` in the deployed UI.
- Edit one `needs_review` row and confirm the audit timeline records the edit.
- Approve one row, lock it, then confirm edits are blocked.
- Include these links in the submission email:
  - GitHub repository
  - deployed frontend URL
  - backend URL if separate
  - demo credentials, or state that no login is required
- Share repository access with the evaluator accounts listed in `assignment.md`.
- Confirm required documents are present:
  - `MODEL.md`
  - `DECISIONS.md`
  - `TRADEOFFS.md`
  - `SOURCES.md`

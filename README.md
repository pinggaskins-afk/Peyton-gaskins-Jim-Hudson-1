# Peyton Gaskins Auto Website - iPad / Render Edition

This edition is intentionally easy to upload from an iPad. The website HTML, CSS and JavaScript are embedded into `app.py`, so there are no nested folders and no hidden files to recreate.

## Upload these four files to GitHub

- `app.py`
- `requirements.txt`
- `render.yaml`
- `README.md`

## Deploy on Render

1. Create a GitHub repository and upload all four files above.
2. Sign in to Render and connect GitHub.
3. Choose New > Blueprint.
4. Select the repository.
5. Render reads `render.yaml` and creates the Python web service automatically.
6. Approve the deployment.
7. Open the `onrender.com` URL Render gives you.

The included Render configuration uses Python 3.13.15, installs the Python requirements, starts the site with Gunicorn, and checks `/health`.

Free Render web services can spin down after inactivity. The first load after a quiet period may therefore take longer.

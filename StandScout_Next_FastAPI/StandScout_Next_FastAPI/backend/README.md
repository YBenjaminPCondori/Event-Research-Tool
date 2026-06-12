# StandScout Backend

Python FastAPI service for ranking exhibitors at Hardware Pioneers MAX 26.

## Run from VS Code

1. Open this `backend` folder in VS Code.
2. Create/select a Python environment.
3. Install packages from `requirements.txt`.
4. Run `app/main.py` through Uvicorn:
   - module: `app.main:app`
   - port: `8000`

API docs will be available at:

`http://127.0.0.1:8000/docs`

Main endpoint:

`POST http://127.0.0.1:8000/api/rank`

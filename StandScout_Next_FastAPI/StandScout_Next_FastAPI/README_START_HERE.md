# StandScout — Next.js + FastAPI Version

This is the cleaner app architecture:

- **Frontend:** Next.js React UI for a client/user-friendly experience.
- **Backend:** Python FastAPI service that ranks exhibitors and returns JSON.
- **Event:** Hardware Pioneers MAX 26.
- **Floorplan:** Fixed to the supplied Hardware Pioneers MAX 26 floorplan.

## What this version is for

Use this version when you want to turn StandScout into a proper web app rather than a single offline HTML demo.

The user-facing flow is:

1. User enters interests such as `edge AI, embedded firmware, FPGA, robotics`.
2. Frontend sends this to the Python API.
3. Backend ranks exhibitors using the scraped event data.
4. Frontend displays the recommended stands, reasons, map markers, and route line.

## Folders

```text
StandScout_Next_FastAPI/
├── backend/    # Python FastAPI ranking API
└── frontend/   # Next.js React UI
```

## Suggested VS Code workflow

Open the root folder in VS Code.

Start the backend from the `backend` folder, then start the frontend from the `frontend` folder.

Backend local URL:

```text
http://127.0.0.1:8000/docs
```

Frontend local URL:

```text
http://localhost:3000
```

## Notes

This package keeps the backend simple but real. The UI is designed to be understandable for non-technical users, while the Python API keeps the ranking logic separate and reusable.

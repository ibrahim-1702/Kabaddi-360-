# Copilot Workspace Instructions: Kabaddi Ghost Trainer

## Purpose

Make AI assistance fast and safe in this repository by encoding:

- common pipelines and tooling commands
- module boundaries (frontend, backend, pose pipeline)
- test expectations and break/fix strategy
- policy and style cues for this academic project

## Key project areas

- `frontend/` : web UI, Flask backend under `frontend/backend/`
- `kabaddi_backend/` : Django REST API services
- `level1_pose/` : low-level pose extraction pipeline
- `pipeline/` : higher-stage DTW alignment / error localization / scoring
- `documents/` : design + algorithm docs used as reference
- `samples/` : input videos and pose artifacts for reproduction

## Recommended agent workflow

1. Start by checking for existing docs and commands in `README.md` and `API_*` docs.
2. Locate the targeted code path.
3. Use repository conventions:
   - Python (`.py`) + Jupyter-style data pipeline
   - Django for backend API tests in `kabaddi_backend/`
   - Frontend HTML/JS in `frontend/`
4. Prefer diagnosis/repair over full rewrite unless user asks.
5. Validate with minimal reproducer commands and existing test harness.

## Build & run commands (quick reference)

- Frontend
  - `cd frontend && python backend/app.py`
  - visit `http://localhost:5000`
- Django backend
  - `cd kabaddi_backend && pip install -r requirements.txt && python manage.py migrate && python manage.py runserver`
- Level 1 pose pipeline
  - `cd level1_pose && pip install -r requirements.txt && python demo_run.py`

## Quality & policy notes

- Project environment: Python 3.8+.
- Keep contributions readable and modular; avoid large monolithic message changes.
- Minimize hardcoded absolute paths; use `os.path.join` or config constants.
- This is academic work with existing experimental code; prefer conservative changes in core math.

## Typical tasks to route in chat

- Fix a failure in transform/temporal alignment by inspecting `pipeline/*` and `level1_pose/*`.
- Add or adjust pose error metric (see `pose_validation_metrics.py`).
- Improve API schema in `kabaddi_backend/` and associated tests (`test_api.py`).
- Add frontend output rendering, checks with `frontend/results.html`.

## Shop talk for Copilot helpers

- “I want a minimal reproducer for `IndexError` in pose array” => inspect `pose_validation_metrics.py`, `pipeline/*`.
- “Add endpoint to return similarity score JSON” => update `kabaddi_backend/` views + routes + test.
- “Create a pipeline step to normalize YOLO/MediaPipe pose landmarks” => level1 pipeline + transform function + tests.

## Next automation notes

- If you change code in `kabaddi_backend/`, run `python manage.py test` there.
- If modifying pipeline timing/path, use `pipeline_test_1/` sample inputs.

> Link, don’t embed: prefer references to existing docs (`README.md`, `PIPELINE_README.md`, `DOCS/*.md`), not copy/paste.

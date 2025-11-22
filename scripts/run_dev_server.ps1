if (-not (Test-Path ".venv")) {

    python -m venv .venv

}

.\.venv\Scripts\activate

uvicorn verifypulse.api_server:app --reload --port 8000

FROM python:3.12-slim

WORKDIR /code

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/

# Hugging Face Spaces listens on 7860 (PORT env is set by the platform).
EXPOSE 7860

# Single worker: the APScheduler auto-publisher must run exactly once.
CMD ["sh", "-c", "cd backend && gunicorn app.main:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-7860}"]

# Lightweight base image for Flask + Gunicorn.
FROM python:3.11-slim

# Keep Python output unbuffered and avoid writing .pyc files.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# App lives here in the container.
WORKDIR /app

# Build deps only needed for installing wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install runtime dependencies.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# Copy the rest of the app.
COPY . ./

# Flask/Gunicorn will bind to 5000 in the container.
EXPOSE 5000

# Default command for production-style serving.
# Override env vars to point at your data:
#   GCBV_DB_PATH=/app/resources/chat.db
#   GCBV_ROOT_PATH=/app/resources/Google Chat
#   GCBV_CONVERSATION=<optional>
CMD ["gunicorn", "-b", "0.0.0.0:5000", "wsgi:app"]

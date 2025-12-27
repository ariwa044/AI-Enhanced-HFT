FROM python:3.10-slim

# Build cache buster for requirements.txt updates
ARG CACHEBUST=1

WORKDIR /code

# Install system dependencies if needed (e.g. for some numpy/pandas builds)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

# Expose default port (Cloud Run uses 8080 by default)
EXPOSE 8080

# Use shell form to allow variable expansion for $PORT (Cloud Run requirement)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

FROM python:3.10-slim

WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

# Expose port for Cloud Run health checks
EXPOSE 8080

# Set environment variable for port
ENV PORT=8080

# Run the cloud agent
CMD ["python", "-m", "app.cloud_agent"]

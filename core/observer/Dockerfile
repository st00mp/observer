FROM python:3.9-slim

WORKDIR /app

# Update packages and fix security vulnerabilities
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY core/observer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY core/observer/app.py ./core/observer/app.py
COPY core/observer/features/ ./core/observer/features/
COPY core/observer/requirements.txt ./core/observer/requirements.txt
COPY shared/ ./shared/

# Copy Alembic migration files to the root directory
COPY core/observer/alembic.ini ./
COPY core/observer/migrations/ ./migrations/

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "core.observer.app:app", "--host", "0.0.0.0", "--port", "8000"]

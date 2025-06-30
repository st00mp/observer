FROM python:3.9-slim

WORKDIR /app

# Update packages and fix security vulnerabilities
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY core/syntinel/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY core/syntinel/app.py ./core/syntinel/app.py
COPY core/syntinel/modules/ ./core/syntinel/modules/
COPY core/syntinel/requirements.txt ./core/syntinel/requirements.txt
COPY shared/ ./shared/

# Copy Alembic migration files to the root directory
COPY core/syntinel/alembic.ini ./
COPY core/syntinel/migrations/ ./migrations/

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "core.syntinel.app:app", "--host", "0.0.0.0", "--port", "8000"]

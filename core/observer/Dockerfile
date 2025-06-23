FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY core/observer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY core/observer/ ./core/observer/
COPY shared/ ./shared/

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "core.observer.src.app:app", "--host", "0.0.0.0", "--port", "8000"]

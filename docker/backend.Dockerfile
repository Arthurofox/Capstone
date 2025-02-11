# docker/backend.Dockerfile
FROM python:3.11.11-slim

WORKDIR /app

# Since context is ../backend, we don't need to include 'backend/' in the path
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--reload"]
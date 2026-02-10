# Base Python image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBUG=False

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y build-essential gcc libpq-dev pkg-config default-libmysqlclient-dev --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better caching)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the project code into the container
COPY . .

# Create static files directory if it doesn't exist
RUN mkdir -p static/images
RUN mkdir -p staticfiles

# Collect static files

RUN DJANGO_SECRET_KEY=dummy-build-key python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Command to run the application (using Gunicorn)
CMD ["gunicorn", "api.wsgi:application", "--bind", "0.0.0.0:8000"]

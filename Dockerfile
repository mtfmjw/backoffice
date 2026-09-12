# Use Python 3.14 base image
FROM python:3.14-slim

# Prevent Python from writing .pyc files & enable realtime stdout logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install build tools and PostgreSQL client libraries
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source files
COPY . .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Collect static files at entrypoint time
#RUN python manage.py collectstatic --noinput

EXPOSE 8000
EXPOSE 5432

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "backoffice.wsgi:application"]

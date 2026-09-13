#!/bin/sh

# Ensure RDS_ENDPOINT is provided
if [ -z "$RDS_ENDPOINT" ]; then
  echo "Error: RDS_ENDPOINT environment variable is not set."
  exit 1
fi

echo "Starting socat proxy on port 5432 -> $RDS_ENDPOINT:5432..."

# Run socat in the background (forks incoming connections to RDS)
socat TCP-LISTEN:5432,fork,reuseaddr TCP:$RDS_ENDPOINT:5432 &

# Collect static files into STATIC_ROOT during container build
python manage.py collectstatic --noinput

# Execute the container's primary CMD process
exec "$@"
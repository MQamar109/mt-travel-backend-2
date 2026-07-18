#!/bin/sh
echo "Waiting for database..."
until python manage.py migrate --run-syncdb 2>&1 | grep -v "No migrations"; do
  echo "Database not ready, retrying in 2s..."
  sleep 2
done
echo "Migrations applied."
exec "$@"

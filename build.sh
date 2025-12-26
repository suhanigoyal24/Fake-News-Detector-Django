#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Collect static files
echo "Collecting static files..."
python3 manage.py collectstatic --noinput

# Apply database migrations
echo "Running migrations..."
python3 manage.py migrate

echo "Build script completed successfully."

#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Set the path to your Django project
PROJECT_DIR="fakereader"

# Navigate to the project directory
cd $PROJECT_DIR

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Apply database migrations
echo "Running migrations..."
python manage.py migrate

echo "Build script completed successfully."

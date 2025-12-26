#!/bin/bash

# Install Python dependencies (already done by Render, optional)
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

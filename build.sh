#!/usr/bin/env bash
# filepath: build.sh

set -o errexit

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Navigate to Django project directory
cd proctor

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate

# Create default admin account (safe to run multiple times)
echo "Creating default admin account..."
python manage.py create_default_admin

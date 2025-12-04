#!/usr/bin/env bash
# exit on error
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate

# Load initial data if datadump.json exists
if [ -f "datadump.json" ]; then
  echo "Loading initial data from datadump.json..."
  python manage.py loaddata datadump.json
fi

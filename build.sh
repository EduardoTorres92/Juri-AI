#!/usr/bin/env bash
set -o errexit

pip install uv
uv export --no-hashes -o requirements.txt
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate

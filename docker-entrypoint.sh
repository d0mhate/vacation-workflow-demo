#!/bin/sh
set -e

python vacation_workflow/manage.py migrate --noinput
python vacation_workflow/manage.py runserver 0.0.0.0:8000

python manage.py collectstatic
cp -r /app/docs/. /app/collected_static/docs/
cp -r /app/collected_static/. /static/backend_static/
gunicorn --bind 0.0.0.0:8000 backend.wsgi
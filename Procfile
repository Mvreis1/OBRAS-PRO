web: gunicorn run:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 --keep-alive 5 --max-requests 1000 --access-logfile - --error-logfile -
release: flask db upgrade

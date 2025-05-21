FROM python:3.9
COPY requirements.txt /code/
RUN pip install --no-cache-dir -r /code/requirements.txt --default-timeout=1000
ADD dashboard/code/ /code/
WORKDIR /code/
ENV PYTHONUNBUFFERED=1
CMD ["gunicorn", "--config", "gunicorn/gunicorn_config.py", "app:app"]
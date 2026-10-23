FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
COPY .build-wheels/ /tmp/wheels/
ARG PIP_NO_INDEX=0
RUN pip install --no-cache-dir --find-links=/tmp/wheels -r requirements.txt && rm -rf /tmp/wheels
COPY . .
RUN rm -rf /app/.build-wheels && useradd --create-home app && mkdir -p /app/.local /app/staticfiles && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]

FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade -r requirements.txt

RUN groupadd --system appuser \
    && useradd --system --gid appuser --create-home appuser

COPY --chown=appuser:appuser . .
EXPOSE 5000

USER appuser

CMD ["gunicorn", "-b", "0.0.0.0:5000", "run:app"]
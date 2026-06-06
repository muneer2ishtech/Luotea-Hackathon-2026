FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh && mkdir -p data/processed

ENV PORT=8090
ENV PYTHONUNBUFFERED=1
EXPOSE 8090

ENTRYPOINT ["/docker-entrypoint.sh"]

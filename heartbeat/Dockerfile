# Heartbeat-Empfänger für Repo-Statistik. Railway baut dieses Image aus dem Ordner heartbeat/
# (Root-Verzeichnis des Service) und hängt ein Volume unter /data ein.
FROM python:3.12-slim
WORKDIR /app
COPY server.py .
ENV PORT=8080 DATENBANK=/data/heartbeat.sqlite PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python3", "server.py"]

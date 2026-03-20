FROM python:3.12-slim

WORKDIR /app
COPY scheduler.py .
COPY jobs.json .

ENV PORT=8010
EXPOSE 8010

CMD ["python", "scheduler.py"]

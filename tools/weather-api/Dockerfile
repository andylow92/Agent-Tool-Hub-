FROM python:3.12-slim

WORKDIR /app
COPY weather.py .

ENV PORT=8001
EXPOSE 8001

CMD ["python", "weather.py"]

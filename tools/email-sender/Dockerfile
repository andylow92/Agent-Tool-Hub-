FROM python:3.12-slim

WORKDIR /app
COPY email_sender.py .

ENV PORT=8008
EXPOSE 8008

CMD ["python", "email_sender.py"]

FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY convert.py .

EXPOSE 8003
ENV PORT=8003

CMD ["python", "convert.py"]

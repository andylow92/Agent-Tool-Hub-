FROM python:3.11-slim

WORKDIR /app
COPY agent_talk.py .
COPY registry.json .

EXPOSE 8004
ENV PORT=8004
ENV AGENT_ID=orchestrator

CMD ["python", "agent_talk.py"]

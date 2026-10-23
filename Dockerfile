FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -e .

EXPOSE 8008
CMD ["uvicorn", "ai_news_radar.web.app:app", "--host", "0.0.0.0", "--port", "8008"]

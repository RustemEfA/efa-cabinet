FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY efa_agents ./efa_agents
RUN useradd --system --uid 1001 worker
USER worker
# переменные: DATABASE_URL, YC_API_KEY, YC_FOLDER_ID, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (+ EFA_MODEL_* при смене моделей)
CMD ["python", "-m", "efa_agents.worker"]

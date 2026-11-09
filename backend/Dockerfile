FROM python:3.12-slim
WORKDIR /workspace
COPY backend ./backend
COPY data_pipeline ./data_pipeline
COPY data/processed/skills_vocab.json ./data/processed/skills_vocab.json
COPY frontend/public/images/companies/catalog.json ./frontend/public/images/companies/catalog.json
# Model chạy trên CPU (EMBED_DEVICE=cpu): cài torch bản CPU trước để tránh kéo ~6 GB thư viện CUDA.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -e './backend[ai]'
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /workspace/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

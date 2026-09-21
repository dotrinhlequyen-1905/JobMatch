# Recruitment Platform - He Thong Tuyen Dung Thong Minh

> Do an chuyen nganh: Xay dung he thong tuyen dung thong minh ung dung AI (SBERT + Cross-encoder)

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy, PostgreSQL + pgvector, Redis, Celery
- **Frontend:** React, Vite, TypeScript, Tailwind CSS
- **AI:** Sentence-BERT (SBERT), Cross-encoder re-ranking
- **Payment:** VietQR / SePay webhook
- **Infra:** Docker Compose, Nginx

## Getting Started

```bash
cp .env.example .env
make dev
```

## Architecture

See [docs/architecture.md](docs/architecture.md)

# BTSP Local Installation Guide

## Prerequisites

Install the following on the workstation or server:

- Git
- Docker Engine
- Docker Compose v2

## First Run

```bash
git clone https://github.com/finalmethos-ops/btsp.git
cd btsp
cp .env.example .env
make up
```

## Service URLs

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Backend health: http://localhost:8000/api/v1/health
- Backend readiness: http://localhost:8000/api/v1/ready
- Nginx entrypoint: http://localhost:8080

## Database Migrations

Run migrations after the database is available:

```bash
make migrate
```

## Troubleshooting

### Port conflicts

Check whether ports 3000, 5432, 6379, 8000, or 8080 are already in use.

### Environment file missing

Create `.env` from the tracked template:

```bash
cp .env.example .env
```

### Container logs

```bash
make logs
```

## Production Notes

For production or on-premises deployment, change all default secrets, set production CORS origins, and use managed backup procedures for PostgreSQL volumes.

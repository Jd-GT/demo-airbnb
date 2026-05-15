# Deployment a la nube

Estado: **plan**, no implementado todavía. Esta es la guía sugerida
basada en la arquitectura objetivo (AWS).

## Topología objetivo

```
┌─────────────────────────────────────────────────────────────┐
│                          AWS                                │
│                                                             │
│  ┌──────────────┐  HTTPS    ┌─────────────────────────┐    │
│  │ Route 53     │──────────▶│  CloudFront / Amplify   │    │
│  │ DNS          │           │  (Frontend Next.js SSR) │    │
│  └──────────────┘           └────────────┬────────────┘    │
│                                          │                  │
│                                          ▼                  │
│                              ┌─────────────────────────┐    │
│                              │  ALB / API Gateway      │    │
│                              └────────────┬────────────┘    │
│                                          │                  │
│                                          ▼                  │
│                              ┌─────────────────────────┐    │
│                              │  ECS Fargate            │    │
│                              │  (Django + Gunicorn)    │    │
│                              │  auto-scaling 2-10 tasks│    │
│                              └────────────┬────────────┘    │
│                                          │                  │
│                                          ▼                  │
│                              ┌─────────────────────────┐    │
│                              │  RDS PostgreSQL Multi-AZ│    │
│                              │  + automated backups    │    │
│                              └─────────────────────────┘    │
│                                                             │
│  Soporte:                                                   │
│   - Secrets Manager (DJANGO_SECRET_KEY, FERNET_KEY, DB pwd) │
│   - S3 (uploads de fotos de propiedades, futuro)            │
│   - CloudWatch (logs + alarmas)                             │
│   - SES (emails transaccionales, Sprint 4)                  │
└─────────────────────────────────────────────────────────────┘
```

## Variables de entorno requeridas en producción

```bash
# Django core
DJANGO_SECRET_KEY=<generate strong random>     # MUST not be the default
DJANGO_DEBUG=False                              # CRITICAL
DJANGO_ALLOWED_HOSTS=api.demoairbnb.app,*.demoairbnb.app
DJANGO_CORS_ALLOWED_ORIGINS=https://app.demoairbnb.app

# DB (apuntar a RDS)
POSTGRES_DB=demoairbnb
POSTGRES_USER=demoairbnb_app
POSTGRES_PASSWORD=<from secrets manager>
POSTGRES_HOST=<rds endpoint>
POSTGRES_PORT=5432
POSTGRES_CONN_MAX_AGE=600

# Cifrado de tokens externos (Sprint 5)
DJANGO_FERNET_KEY=<generate fernet>

# JWT
SIMPLE_JWT_SIGNING_KEY=<override del SECRET_KEY si quieres separarlo>

# Logging
SENTRY_DSN=https://<key>@sentry.io/<project>

# Email (Sprint 4)
SES_REGION=us-east-1
SES_FROM=no-reply@demoairbnb.app
```

## Checklist pre-deploy

- [ ] `DEBUG=False` en producción.
- [ ] `SECRET_KEY` de >50 chars, NO el default.
- [ ] `ALLOWED_HOSTS` no contiene `*` en prod.
- [ ] CORS apunta SÓLO al dominio del frontend prod.
- [ ] Postgres con SSL forzado.
- [ ] RDS con backups automáticos y snapshot manual previo al deploy.
- [ ] WhiteNoise o S3 + CloudFront para `STATIC_ROOT` (frontend
      estático ya lo sirve Amplify, esto es para Django admin).
- [ ] Logs van a CloudWatch.
- [ ] Sentry capturando errores.
- [ ] Health check endpoint para el ALB (`/api/schema/` sirve, o crear
      `/healthz/`).
- [ ] Migraciones aplicadas ANTES de switchear tráfico (job task
      ECS one-shot).
- [ ] Super-admin creado (vía script de migración o manual).
- [ ] Primer CREATE_TENANT code generado para onboarding del primer
      cliente real.

## Multi-tenant en DNS

El middleware soporta resolución por subdominio
(`acme.demoairbnb.app` → tenant `acme`). Para que esto funcione en
producción:

- Configurar Route 53 con un wildcard A/CNAME `*.demoairbnb.app` →
  el ALB.
- El certificado ACM debe ser wildcard `*.demoairbnb.app`.
- El frontend (Amplify) debe servirse en el mismo wildcard.

Alternativa más simple si los subdominios son lío: dejar el frontend
en `app.demoairbnb.app` y resolver el tenant por header
`X-Tenant-ID` (que el frontend ya envía vía localStorage).

## CI/CD sugerido

GitHub Actions:

1. **PR**: lint (ruff), tests (`python manage.py test apps`), build
   frontend (`npm run build`).
2. **Merge a `main`**: build de imágenes Docker, push a ECR, deploy
   a ECS staging, smoke tests.
3. **Tag `v*`**: deploy a producción (con aprobación manual).

## Rollback

ECS soporta rollback al task definition anterior con un click. Para
cambios de schema (migraciones), siempre se debe:

1. Hacer migraciones **backward-compatible** (e.g., añadir nullable
   antes de marcar required en una segunda migración).
2. Tener snapshot de RDS del momento previo al deploy.
3. Si algo falla: rollback de ECS + (si necesario) restore de RDS.

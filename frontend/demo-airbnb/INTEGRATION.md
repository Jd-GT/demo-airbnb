# Documentación de integración — demo-airbnb

## Stack del frontend
- Framework: Next.js 15.5.7 + React 19.2.0
- Librería HTTP usada: fetch
- Variable de entorno base URL: NEXT_PUBLIC_API_BASE_URL

## Stack del backend
- Framework: Django 5.2 + Django REST Framework
- Puerto por defecto: 8000

## Dependencias externas a instalar
> Lista todo lo que se debe instalar ANTES de correr `npm run dev`.
> Si no hay nada adicional, escribe explícitamente: "Ninguna dependencia adicional requerida."

### Frontend
- Ninguna dependencia adicional requerida.

### Backend
- django-cors-headers — habilita CORS para las llamadas locales del frontend.

## CORS configurado
- Origen permitido: http://localhost:3000, http://127.0.0.1:3000, http://localhost:5173, http://127.0.0.1:5173
- Dónde se configuró: demoairbnb/demoairbnb/settings.py, aprox. líneas 24-39 y 122-142

## Mapa de conexiones realizadas

| Dato / Sección del frontend | Archivo frontend modificado | Endpoint del back | Método | Endpoint creado? |
|---|---|---|---|---|
| Dashboard - KPI de propiedades y ocupación | src/app/page.tsx | /api/tenants/{tenant_id}/inventory/properties/?year=&month= | GET | No |
| Dashboard - ingresos mensuales/anuales | src/app/page.tsx | /api/tenants/{tenant_id}/finance/analytics/?year=&month= | GET | Sí |
| Dashboard - próximos check-in/check-out | src/app/page.tsx | /api/tenants/{tenant_id}/booking/reservations/?from=&to= | GET | No |
| Calendario - reservas del mes | src/app/calendario/page.tsx | /api/tenants/{tenant_id}/booking/reservations/?from=&to= | GET | No |
| Propiedades - listado y métricas | src/app/propiedades/page.tsx | /api/tenants/{tenant_id}/inventory/properties/?year=&month= | GET | No |
| Finanzas - serie anual e ingresos por propiedad | src/app/finanzas/page.tsx | /api/tenants/{tenant_id}/finance/analytics/?year=&month= | GET | Sí |
| Integraciones - estado de conexiones | src/app/integraciones/page.tsx | /api/tenants/{tenant_id}/integrations/ | GET | Sí |
| Bootstrap demo - tenant, auth y seed inicial | src/lib/api.ts | /api/tenants/, /api/auth/token/, /api/auth/token/refresh/, /api/tenants/{tenant_id}/inventory/amenities/, /api/tenants/{tenant_id}/inventory/properties/, /api/tenants/{tenant_id}/crm/contacts/, /api/tenants/{tenant_id}/booking/reservations/ | POST / GET | No |

## Datos que NO se pudieron conectar (TODO)
> Se mantuvieron fallbacks mínimos únicamente donde no existe soporte real en el backend actual.

- **plataforma de reserva**: no existe campo, modelo ni endpoint para el canal/OTA asociado a cada reserva.
- **bloqueos manuales de calendario**: no existe modelo ni endpoint para bloqueos manuales fuera de reservas.
- **gastos operativos**: no existe modelo contable/ledger ni endpoint de gastos.
- **ingresos por plataforma**: depende de plataforma de reserva, que hoy no existe en backend.
- **comisiones de plataformas**: no existe modelo ni endpoint de comisiones por canal.
- **utilidad neta**: depende de gastos operativos que no existen en backend.
- **metadatos visuales de propiedad**: no existen campos/backend para imagen, piso, habitaciones, baños y estado visual.

## Instrucciones para correr el proyecto localmente

### Backend
```bash
cd demoairbnb

# Variables relevantes/opcionales:
# DJANGO_SECRET_KEY=change-me-in-production
# DJANGO_DEBUG=True
# DJANGO_ALLOWED_HOSTS=*
# DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
# POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_CONN_MAX_AGE
# Si POSTGRES_DB no existe, el proyecto usa SQLite local.

../.venv/bin/pip install -r ../requirements.txt
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py test
../.venv/bin/python manage.py runserver 8000
```

### Frontend
```bash
# Variables de entorno:
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

cd /frontend/demo-airbnb
npm install
npm run dev
```

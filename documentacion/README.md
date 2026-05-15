# Documentación — Demo Airbnb PMS

Esta carpeta es **el punto de entrada** para cualquier desarrollador (o IA)
que se sume al proyecto. Describe qué es el sistema, qué hay implementado,
qué falta, y cómo está organizado el código.

## ¿Qué es esto?

Un **PMS (Property Management System) multi-tenant**, parecido a Airbnb
para administrar el inventario interno de hosts/inmobiliarias. Inspirado en
Odoo (centros de costos, contabilidad analítica, gestión de roles). Está
pensado para ir en la **nube** (AWS) y para que **un super-admin** controle
qué empresas pueden tener cuenta en la plataforma.

| Capa     | Stack                                                     |
| -------- | --------------------------------------------------------- |
| Backend  | Python 3.13 + Django 5.2 + DRF 3.15 + JWT + drf-spectacular |
| Frontend | Next.js 15 (App Router) + React 19 + Tailwind 4 + shadcn |
| DB       | PostgreSQL (con fallback a SQLite en dev)                 |
| Infra    | Docker Compose para dev. Producción objetivo: AWS ECS / RDS / Amplify |

## Cómo navegar esta documentación

1. **`STATE.md`** — Empieza aquí. Tabla de "qué está hecho vs qué falta",
   por épica y por módulo. Si vas a implementar algo nuevo, valida primero
   contra esta tabla.
2. **`ARCHITECTURE.md`** — Modelo del dominio, estructura de apps Django,
   middleware multi-tenant, RBAC, decisiones arquitectónicas y por qué.
3. **`AUTH_FLOW.md`** — El flujo de login/signup, cómo funcionan los
   `InvitationCode` (CREATE_TENANT vs JOIN_TENANT), el rol del super-admin,
   y los puntos de extensión.
4. **`API.md`** — Contrato REST completo. Endpoints por módulo, ejemplos
   de request/response, headers, auth.
5. **`PRIVACY_AND_RBAC.md`** — Cómo se enforza la privacidad multi-tenant y
   los permisos por módulo. Importante para entender por qué `/settings`
   se ve distinto según el rol.
6. **`FRONTEND.md`** — Estructura de carpetas del frontend, AuthProvider,
   convenciones para nuevas páginas, helpers.
7. **`SETUP.md`** — Cómo levantar el proyecto en local (sin y con Docker),
   crear un super-admin, generar el primer código de invitación.
8. **`DEPLOYMENT.md`** — Guía de despliegue a AWS (ECS + RDS + Amplify) y
   variables de entorno requeridas en producción.
9. **`NEXT_STEPS.md`** — La hoja de ruta priorizada. Lo que está listo
   para que el próximo dev/IA arranque sin perder tiempo decidiendo.
10. **`CHANGELOG.md`** — Cambios recientes (Sprint 0 = acceso controlado +
    limpieza de mocks; ver fecha 2026-05-13).
11. **`docs/ai/`** — La documentación funcional original del proyecto:
    historias de usuario, diccionario de tablas, plan de implementación.
    Esta carpeta (`documentacion/`) es la documentación **técnica**; la
    otra es la documentación **funcional**.

## Convención que estamos usando

- Todo el backend asume **multi-tenancy estricto**. Cualquier modelo de
  negocio nuevo hereda de `TenantAwareModel` y filtra automáticamente
  por el tenant del request. Ver `ARCHITECTURE.md`.
- Todo endpoint nuevo declara `permission_module` y opcionalmente
  `required_permission_level`. Ver `PRIVACY_AND_RBAC.md`.
- Las integraciones externas se configuran por tenant en
  `Tenant.integration_config`. Sólo el OWNER ve el contenido raw.
- **No hay pasarelas de pago.** Si ves Stripe, PayPal o "online payment"
  en algún lado, es restos del producto antiguo y se debe eliminar.
- **No hay signup público sin código.** Si ves UI o endpoint que
  permita crear un tenant sin `invitation_code`, es un bug — repórtalo.

- # Plan de Desarrollo y Estrategia de Equipo (SaaS PMS)

    Este documento define cómo un equipo de 4 personas (1 Frontend, 3 Full-Stack/Python) debe organizarse para construir el PMS usando Django REST Framework (DRF) y React (Next.js), garantizando que el código sea mantenible, escalable y no se convierta en un "spaghetti" de código.

    LAS INSTRUCCIONES SE ENCUENTRAN EN: ETAPA ACTUAL DE PROYECTO, leer TODOS los Archivos para indicar los prompts antes de iniciar incluyendo este.

    ## Archivos para indicar los prompts
    - EXPLICACION_TABLAS.md, 
        - Aqui estan las tablas y modelos que se usaran en el SAAS a construir, y componentes del sistema
    - IMPLEMENTACION.md
        - Archivo actual 
    - ARQUITECTURA_TABLAS.md, 
        - Explicacion y sustentacion de los detalles de cada tabla y relacionamiento entre ellas (leer siempre EXPLICACION.md antes de leer este )
    - user_stories.md 
        - Historias de usuario, las cuales vas a ir marcando como completadas segun el alcance del sprint y del codigo desarrollado
    ------
    ## Archivos importantes:
    - /demoairbnb: 
         - Base DJANGO REST FRAMEWORK donde se deben implementar las funcionalidades indicadas en la seccion de ETAPA DE PROYECTO
    - /documentacion (esta la crearas tu) y documentaras el codigo y cambios que haces en el /demoairbnb
    - /requirements.txt
    - /BACKEND_FRONT_API.md (lo creas tu) se debe documentar las apis y endpoints que el FRONTEND DEV debe conocer para desarrollar el FRONT.

    ## ETAPA ACTUAL DE PROYECTO

    1) Actualmente no se tiene nada implementado
    2) Se requiere hacer unicamente el sprint 1, y se debe dejar listo para empezar el sprint 2, leer primero todos `Archivos para indicar los prompts` para entender el concepto del SAAS a implementar.
    3) SOLO SE TRABAJA EL BACK y debemos tener presente la creacion de un JSON o documentacion necesaria que requiere el desarrollador front para integrar el back, esto debe ir documentado en /BACKEND_FRONT_API
    4) MARCAR HISTORIAS USUARIO A MEDIDA QUE DESARROLLA EL CODIGO BASE: user_stories, marcar con un CHECK [x]
    ------
    
    ## 0. Descripción de los Componentes
    
    A continuación se detallan los subsistemas técnicos que implementan la solución.
    
    ### A. Frontend: Portal Web (Spa & Dashboard)
    
    - **Tecnología**: **Next.js (React)** + TailwindCSS.
    - **Rol**: Interfaz de usuario para administradores y huéspedes.
    - **Sub-componentes**:
      - *SaaS Context Provider*: Carga dinámicamente colores y logos según el subdominio.
      - *Dashboard View*: Gráficos de ocupación e ingresos.
      - *Calendar Component*: Vista drag-and-drop de reservas.
      - *Guest Portal*: Vista pública read-only para el huésped.
    
    ### B. Backend: API RESTful & Lógica de Negocio
    
    - **Tecnología**: **Python (Django REST Framework)**.
    - **Rol**: Orquestador central. Procesa reglas de negocio, validaciones y seguridad.
    - **Sub-componentes**:
      - *Pricing Engine*: Calcula precios complejos basados en fechas y reglas.
      - *Tenant Middleware*: Asegura el aislamiento de datos entre clientes.
      - *Doc Generator*: Servicio (usando WeasyPrint) que renderiza PDFs desde HTML.
    
    ### C. Base de Datos Relacional
    
    - **Tecnología**: **PostgreSQL (AWS RDS)**.
    - **Rol**: Persistencia de datos transaccional segura.
    - **Características**: Uso de Foreign Keys estrictas, Check Constraints para integridad de datos y particionado lógico por `tenant_id`.
    
    ### D. Capa de Integración (Channel Manager Adapter)
    
    - **Tecnología**: Python (Módulos internos).
    - **Rol**: Abstracción de APIs externas. Permite conectar nuevas plataformas sin romper el núcleo.
    - **Adaptadores**:
      - `AirbnbAdapter`: Sincronización vía iCal (MVP) o API oficial.
      - `WhatsAppService`: Envío de mensajes vía API (Twilio/Meta).
    
    ------


    ## 1. Distribución del Equipo (Roles)

    Dado el perfil del equipo (1 React fuerte, 3 Python fuertes), la estrategia ideal es **desacoplar completamente el Frontend del Backend** y usar un enfoque de *API-First*.

    ### Miembro 1: "The Frontend Lead" (Especialista React)

    - **Responsabilidad**: Todo el repositorio de Next.js.
    - **Tareas**: Creación de componentes UI/UX, integración de la API, manejo del estado global (Redux/Zustand), y el contexto del Tenant (SaaS branding).
    - **Regla de Oro**: Nunca bloqueado por el Backend. Si un endpoint no existe, crea un *Mock* (JSON estático) de la respuesta esperada y sigue construyendo la UI.

    ### Miembro 2: "The Core Builder" (Arquitecto Backend)

    - **Responsabilidad**: Diseñar la base sólida del repo Django.
    - **Tareas**: Configurar el `TenantMiddleware`, modelos base (`AbstractBaseModel` con `tenant_id`), autenticación JWT, y configuración de AWS (CI/CD básico).
    - **Aporte**: Asegura que nadie rompa el aislamiento SaaS.

    ### Miembro 3: "The Domain Expert" (Backend - Reservations & Pricing)

    - **Responsabilidad**: La lógica de negocio más dura.
    - **Tareas**: Modelos de `Reservation`, `PriceRules`, y el endpoint de cotización (`/quote`) que es el corazón matemático del sistema.

    ### Miembro 4: "The Integrator" (Backend - CRM, Finanzas & Ops)

    - **Responsabilidad**: Módulos adyacentes al Core.
    - **Tareas**: Modelos de `Leads`, `Payments`, `AnalyticAccounts`, `Tasks`. Desarrollo del motor de plantillas y generación de PDFs.

    ------

    ## 2. Estrategia de Código: ¿Cómo no enredarse?

    **SÍ, hay que hacer un "Código Base" (Scaffolding) antes de que todos empiecen a programar.**

    ### A. Repositorios Separados (Monorepo vs Polyrepo)

    Recomendación: **Dos repositorios separados** (`pms-backend` y `pms-frontend`).

    - Esto evita conflictos de merge entre mundos distintos y permite despliegues independientes a AWS (ECS para Django, Amplify para Next.js).

    ### B. El "Core App" en Django (El Código Base)

    El Arquitecto (Miembro 2) debe pasar la **Semana 1** creando la base antes de que los demás toquen el backend.

    1. **Apps Estructuradas**: En Django, NO meter todo en una app.

       - `apps/core/` (Tenants, **TenantRoles**, Usuarios, Middleware, Modelos Base abstractos).
       - `apps/inventory/` (Propiedades, Amenities).
       - `apps/crm/` (Contactos, Leads).
       - `apps/booking/` (Reservas, Líneas, Tarifas).
       - `apps/finance/` (Pagos, Impuestos, Analítica).

       **Importante — Gestión de Roles y Permisos (US-1.1.1)**:
       El módulo `apps/core/` es responsable de todo el sistema IAM (Identity & Access Management). La estructura de permisos usa RBAC (Role-Based Access Control) ligero:
       - `TenantRole`: Define roles personalizados por Tenant con un JSON de permisos por módulo.
       - `User`: Referencia un `TenantRole` (excepto `OWNER` que tiene acceso irrestricto).
       - El `TenantMiddleware` no solo aísla datos sino que también verifica que `user.role.permissions[modulo]` tenga el nivel requerido (`none` | `read` | `write` | `admin`) antes de dejar pasar cualquier request.
       - **Regla de seguridad**: Nunca confiar en el frontend para ocultar secciones. Todo permiso se valida en el backend en cada endpoint.

    2. **Modelo Base Abstracto**: Todo modelo debe heredar de esto (excepto Tenant):

       ```py
       python
       class TenantAwareModel(models.Model):
       
           tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
       
           created_at = models.DateTimeField(auto_now_add=True)
       
           # El manager por defecto filtra por el tenant actual del request
       
           objects = TenantManager() 
       
           class Meta: abstract = True
       ```

       Así nadie "olvida" filtrar por Tenant.

    ### C. El Contrato de API (Swagger/OpenAPI)

    ¡Vital para que el Frontend y Backend trabajen en paralelo!

    - Antes de escribir código, definan cómo se verán los JSON en una herramienta como Swagger o Postman.
    - El Frontend asume que ese JSON existe y programa. El Backend programa para que su respuesta coincida con ese JSON.

    ------

    ## 3. Flujo de Trabajo (Git & Sprints)

    ### Git Flow Simplificado (Ramas)

    1. `main`: Código en producción.
    2. `staging`: Código integrado y probado.
    3. `dev`: Ramas creadas desde `staging` por cada desarrollador, donde se implementan nuevas funcionalidades a partir de la base, `staging`.

    ### Fases de Desarrollo (Sprints Recomendados)  

    **Sprint 1: Inventario y CRM (1-2 Semanas)**
    - Backend: Configurar Django, PostgreSQL, Modelos Base DUMB (solo tablas, sin lógica).
    - Frontend: Repositorio Next.js, Layouts principales, Theming de Tailwind, Mockups de UI.
    - API: Documento de Swagger acordado.
    - Backend (Dev 3 y 4): Endpoints CRUD de Propiedades, Contactos y Leads.
    - Frontend (Dev 1): Pantallas de Listado y Creación de Inmuebles, Kanban de CRM.
    - Funcionalidades: Disponibilidad, Creación de Reserva. Endpoint de `/quote`, Creación de los tenants, usuarios y propiedades.
    - **[US-1.1.1] Gestión de Usuarios y Roles (Miembro 2 — Core Builder)**:
      - Endpoint `POST /api/tenants/{id}/roles/` — Crear un rol personalizado con JSON de permisos.
      - Endpoint `GET/PUT/DELETE /api/tenants/{id}/roles/{role_id}/` — Administrar roles.
      - Endpoint `POST /api/tenants/{id}/users/` — Invitar/crear usuario y asignarle un rol.
      - Endpoint `PATCH /api/tenants/{id}/users/{user_id}/` — Cambiar rol o desactivar usuario (`is_active=false`).
      - Seed automático al crear un Tenant: crear rol `Admin Total` (todos los módulos en `admin`) y rol `Solo Lectura` (todos en `read`) como defaults.
      - El primer usuario del Tenant se crea con `system_role=OWNER` y nunca puede ser degradado ni desactivado.

    **Sprint 2: El Motor de Reservas (3 Semanas)**

    - Backend (Dev 2 y 3): Lógica del Precio, 
    - Frontend (Dev 1 y 4 - *Dev 4 apoya en Front si sabe algo de JS*): Calendario Interactivo, Cotizador, Flujo de creación de compra.

    **Sprint 3: Finanzas y Operaciones (2 Semanas)**

    - Backend (Dev 3 y 4): Pagos, Cuentas Analíticas, Generación de PDF. Tareas de Limpieza.
    - Frontend (Dev 1): Dashboard financiero, Lista de Tareas, Vista de Recibos.

    **Sprint 4: Pulido y Lanzamiento Técnico (AWS)**

    - Despliegue de DB a RDS.
    - Despliegue de Django a Elastic Beanstalk o ECS.
    - Despliegue de Next.js a AWS Amplify.
    - Pruebas de extremo a extremo (E2E).

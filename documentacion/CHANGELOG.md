# Changelog

## 2026-05-15 — Hotfix 5.6: Reservas externas (Airbnb/Booking), CRM hardening, página /reservas

### Backend

**`Contact` (CRM) — duplicados ahora retornan 400, no 500**
- `ContactSerializer.validate` pre-chequea unicidad por tenant para
  `email` (case-insensitive) y `tax_id`. Mensaje en español: *"Ya existe
  un cliente con ese email en esta empresa"* / *"Ya existe un cliente
  con ese ID fiscal"*.
- `create()`/`update()` envueltos en `transaction.atomic` + `try/except
  IntegrityError` como defensa en profundidad por si gana la race
  condition entre validate y save.
- `ContactViewSet.get_serializer_context` ahora inyecta `tenant_id`
  para que la validación arriba funcione.

**`Reservation.guest` acepta PLATFORM además de GUEST**
- Antes: `guest.type` se forzaba a `GUEST` → no se podía registrar
  reservas externas tipo "Airbnb #1234" cuando aún no se conoce al
  huésped real.
- Ahora: `guest.type ∈ {GUEST, PLATFORM}`. Los `AGENT` siguen
  bloqueados como guest (van en `agent_id` con su comisión).
- Mensaje claro: *"El titular de la reserva debe ser un Huésped o una
  Plataforma (Airbnb, Booking, etc.). Los agentes van en el campo
  agent."*

**Tests añadidos (5 nuevos, total 71):**
- `apps/crm/tests/test_contact_dedup.py`:
  - Email duplicado → 400 con clave `email`.
  - tax_id duplicado → 400 con clave `tax_id`.
  - Múltiples contactos sin email no colisionan.
- `apps/booking/tests/test_platform_guest.py`:
  - Crear reserva con guest=PLATFORM funciona y devuelve `guest_name`.
  - Crear reserva con guest=AGENT sigue siendo 400.

### Frontend

**Modal `NewReservationModal` (extraído a componente compartido)**
- Movido a `src/components/new-reservation-modal.tsx` para usarlo
  desde `/calendario` y `/reservas` sin duplicación.
- Dropdown del titular ahora usa `<optgroup>` para separar:
  - **Huéspedes** (Contact.type=GUEST)
  - **Plataformas (reservas externas)** (Contact.type=PLATFORM)
- El "+ Nuevo" inline también permite elegir el tipo (Huésped o
  Plataforma). Cuando es PLATFORM, oculta el campo teléfono y cambia
  el placeholder a *"Ej: Airbnb, Booking.com, Expedia"*.
- Muestra el tipo del contacto seleccionado bajo el dropdown.

**`/reservas` (NUEVA página)**
- Listado completo en tabla: check-in/check-out, propiedad, titular,
  noches, total, pagado, saldo, estado, estado de pago.
- KPIs arriba: total visibles, confirmadas, con saldo pendiente,
  ingresos esperados.
- Filtros: búsqueda por huésped/propiedad, estado de reserva, estado
  de pago, ventana de tiempo (botones "+ meses pasados" / "+ futuros").
- Botón "+ Nueva reserva" usa el mismo modal que el calendario.
- Sidebar nuevo link **Reservas** (entre Dashboard y Calendario).

### Por qué (decisiones)

- **PLATFORM como guest, no como nuevo campo `source`**: el modelo de
  `Contact` ya tenía PLATFORM y nunca se usaba. Reusarlo evita una
  migración y mantiene el modelo simple. El operador crea un Contact
  *"Airbnb"* una vez y lo selecciona como guest en cada reserva
  externa, igual que un huésped real. Stats por cliente del CRM
  funcionan idéntico: el reporte de "Airbnb" muestra cuántas reservas
  vinieron de allí, total facturado, etc. — exactamente lo que el
  usuario pidió ("ver lo que he hecho por fuera de Whatsapp").
- **Pre-validación de duplicados en serializer en lugar de sólo
  catch del IntegrityError**: el catch funciona pero deja la
  transacción en estado abortado, lo que en Postgres impide siguientes
  queries en el mismo request. Pre-validar evita ese estado.
- **`/reservas` reutiliza el modal del calendario, no duplica**:
  extracción a `components/new-reservation-modal.tsx`. Cualquier
  mejora futura aplica a ambas pantallas.

### Limitaciones conocidas

- El listado de `/reservas` no pagina; con miles de reservas se
  ralentiza. Añadir paginación cuando crezca.
- La búsqueda es client-side (sobre los resultados ya cargados). Si
  filtras por meses muy amplios, descarga muchas reservas. El
  backend ya soporta `?from=&to=`, pero no aún `?search=` por nombre.
- No hay forma de **editar** una reserva existente desde la UI
  (cambiar fechas, cancelar). Sólo crear y consultar. La API soporta
  PATCH parcialmente — pendiente añadir UI.

---

## 2026-05-15 — Hotfix Sprint 5.5: Pagos con clarity, validación overpayment, mini-CRM clientes

### Backend

**Modelo Payment**
- Nuevo tipo `EXTRA` (daños, servicios extra, late fees). Sin tope —
  intencional, porque el negocio no puede predecir cuánto puede cobrar
  por arreglar una pared rota.
- Constante `LODGING_PAYMENT_TYPES = {ADVANCE, BALANCE}` para distinguir
  pagos que cuentan contra el saldo de alojamiento vs pagos paralelos.

**Modelo Reservation**
- Nuevo campo `extras_received` (Decimal cache, sum de pagos `EXTRA`).
- Recompute en `_recompute_payment_status`:
  - `amount_paid` ahora **solo** suma `ADVANCE+BALANCE − REFUND`
    (antes contaba EXTRA).
  - `extras_received` se rellena por separado.
  - `payment_status` sigue derivándose de `amount_paid` vs `total_amount`.

**Validación en `register_payment`**
- Si `type ∈ LODGING_PAYMENT_TYPES`: rechaza con 400 si el monto excede
  `total_amount − amount_paid`. Mensaje claro: *"el monto excede el saldo
  pendiente ($X). Cobra como máximo ese valor, o registra el sobrante
  como Pago extra"*.
- Si `type == REFUND`: rechaza si excede `amount_paid`.
- Si `type == EXTRA`: sin tope (los daños / servicios extra pueden ser
  arbitrariamente grandes).
- Mismas validaciones se ven reflejadas en el endpoint
  `POST /finance/payments/` que ahora retorna 400 con `{amount: "..."}`
  en lugar de aceptar y romper la integridad del balance.

**Modelo Contact (CRM)**
- Nuevos campos: `tax_id` (cédula/RUT/NIT, único por tenant cuando no
  está vacío), `address`, `nationality`, `notes`.
- Constraint adicional: `tenant_unique_contact_tax_id`.

**Endpoint nuevo: stats por cliente**
- `GET /api/tenants/<id>/crm/contacts/<contact_id>/stats/` →
  `{reservations_count, confirmed_reservations_count,
    cancelled_reservations_count, total_billed, total_lodging_paid,
    total_extras_paid, total_refunded, outstanding_balance,
    first_check_in, last_check_out, nights_total}`.
- Implementado en `apps/crm/services.py:get_contact_stats`.

**Reportes Excel actualizados**
- `payments.xlsx` ahora incluye una columna **Categoría**
  (Alojamiento / Extra / Reembolso) y los totales al final están
  desglosados: alojamiento neto, extras, reembolsos, total entradas.

**Tests añadidos (7 nuevos, total 66):**
- `apps/finance/tests/test_payment_validation.py`:
  lodging payment cannot exceed balance,
  partial then full overpayment blocked,
  EXTRA has no upper bound,
  endpoint returns 400 on overpayment,
  refund cannot exceed paid.
- `apps/crm/tests/test_contact_stats.py`:
  stats endpoint sums lodging+extras correctly,
  Contact supports CRM fields (tax_id, address, nationality, notes).

### Frontend

**`/pagos` reescrito**
- KPIs separados: Alojamiento neto · Extras · Reembolsos · Total entradas.
- El selector de Reserva muestra el `payment_status` en cada opción
  (`Sin pagar / Pago parcial / Pagado / Sobrepagado`).
- Al elegir reserva, aparece un panel de **balance en vivo**: total
  alojamiento, pagado, saldo pendiente, extras recibidos.
- El botón **Registrar pago se desactiva** si el monto excede el saldo
  (lodging) o lo pagado (refund), con mensaje rojo inline.
- Sugerencia automática de tipo:
  - Reserva pagada al 100% → sugiere EXTRA.
  - Reserva sin pagos → sugiere ADVANCE.
- Helper text dinámico según el tipo elegido (qué valida, qué tope tiene).

**`/clientes` (NUEVO mini-CRM)**
- Listado con búsqueda por nombre/email/teléfono y filtros por tipo
  (Huésped / Agente / Plataforma).
- Conteos por tipo arriba como botones-filtro.
- Panel de detalle a la derecha con:
  - Datos básicos (nombre, email, teléfono, ID fiscal, nacionalidad,
    dirección, notas, % comisión si es agente).
  - Botón Editar inline + Eliminar (con confirmación).
  - **Reporte por cliente**: reservas confirmadas/canceladas, noches
    totales, saldo pendiente, total facturado, pagado alojamiento,
    extras pagados, reembolsado. Primera estancia / última check-out.
- Modal "Nuevo cliente" con todos los campos CRM.

**Sidebar**: nuevo link **Clientes** entre Propiedades y Finanzas.

### Por qué (decisiones)

- **EXTRA como tipo separado, no como bandera booleana**: queda
  visible en el listado, en los reportes Excel, y en el badge de la
  fila. La distinción "alojamiento vs extra" es semántica, no
  técnica — merece un valor de enum, no un flag escondido.
- **`extras_received` como cache en `Reservation`**: para que el balance
  panel del frontend pueda mostrarlo sin agregar otra query. Se recalcula
  en cada Payment write como `amount_paid`.
- **No hay overpayment "fuerte"**: si por algún caso de migración de
  data llega una `Reservation` con `amount_paid > total_amount`, el
  estado queda OVERPAID y el reporte lo muestra. La validación bloquea
  futuros overpayments via la API; no asumimos invariante perfecto en
  histórico.
- **Tax_id único por tenant pero opcional**: no quisimos forzar el
  campo en signup (rompería casos de huéspedes que pagan en efectivo
  sin documentar), pero cuando se llena evitamos duplicados (caso
  típico: cargar un huésped dos veces). El partial-unique-index hace
  el trabajo en Postgres.
- **Stats endpoint en lugar de aggregate query en el listado**: para
  no penalizar el list (`fetchContacts`) que se usa en muchos lados.
  Solo cuando el usuario abre el detalle se carga el reporte completo.

### Limitaciones conocidas

- El recompute de `payment_status` no usa locking — si dos requests
  registran pagos sobre la misma reserva al mismo tiempo, podrían leer
  el mismo `amount_paid` previo y ambos pasar la validación. Para el
  caso de uso (operador humano registrando pagos) la probabilidad es
  ínfima. Cuando se exponga la API a clientes externos, envolver
  `register_payment` en un `select_for_update`.
- El listado de pagos en `/pagos` no pagina; con miles de pagos puede
  ralentizar. Añadir paginación cuando crezca.
- `outstanding_balance` en stats puede ser negativo si el cliente tiene
  reembolsos > facturación (caso raro). Lo dejamos visible como
  número, no lo escondemos.

---

## 2026-05-14 — Sprint 4 + 5: Operaciones, plantillas, voucher PDF, hardening + Google Calendar stub

### Sprint 4 — Operaciones y comunicación

**App nueva: `apps/ops`**
- Modelo `Task` (CLEANING / MAINTENANCE / INSPECTION / OTHER) con
  `status` (PENDING / IN_PROGRESS / DONE / CANCELLED), `due_date`,
  `assigned_to`, link opcional a `reservation`. CRUD endpoints + acción
  `POST /ops/tasks/{id}/complete/`.
- Auto-creación: cada `create_reservation()` ahora dispara
  `ensure_cleaning_task_for_reservation()` (idempotente). La tarea
  vence el día de check-out.
- Permission custom `_OpsTaskPermission`: deja pasar a usuarios con
  `system_role=CLEANER` aunque no tengan rol asignado, y la queryset
  filtra por `assigned_to=request.user` automáticamente para ellos. Un
  CLEANER sólo puede marcar como IN_PROGRESS o DONE su propia tarea.
- Modelo `MessageTemplate` (canales WHATSAPP / EMAIL / INTERNAL) con
  cuerpo + asunto y placeholders `{{guest_name}}`, `{{property_name}}`,
  `{{property_address}}`, `{{check_in}}`, `{{check_out}}`, `{{nights}}`,
  `{{total_amount}}`, `{{balance_due}}`, `{{amount_paid}}`,
  `{{reservation_id}}`, `{{tenant_name}}`.
- `POST /ops/render-message/` renderiza una plantilla contra una reserva
  y devuelve `{channel, subject, body}`. **No envía nada** — el frontend
  copia al portapapeles o usa wa.me. Decisión consciente: cero dependencia
  de proveedores de email/WhatsApp todavía.
- Voucher PDF (`reportlab`): `GET /ops/voucher/{reservation_id}.pdf`
  renderiza un A4 con datos de la reserva, líneas detalladas y totales.

**Esqueleto Google Calendar (apps/core/integrations.py)**
- Modelo `GoogleCalendarCredential` con `refresh_token_encrypted` (Fernet),
  `calendar_id`, `is_active`, `last_sync_at/status/error`.
- Adapter `GoogleCalendarAdapter` (puerto + adaptador): `sync_reservation()`
  devuelve `{status: not_configured | stub_ok}`. Cuando se implemente la
  sincronización real, sólo cambia este archivo — el resto del código ya
  llama a `get_adapter_for_tenant(tenant_id).sync_reservation(reservation)`.
- Endpoints:
  - `GET/PUT/DELETE /tenants/{id}/integrations/google-calendar/` — manejo
    de la credencial (token write-only, nunca devuelto).
  - `POST /tenants/{id}/integrations/google-calendar/sync/{reservation_id}/`
    — disparador manual del sync.

### Sprint 5 — Hardening / NFRs

- **`apps/core/crypto.py`**: helper `encrypt_secret/decrypt_secret` con
  Fernet (AES-128-CBC + HMAC). Lee `DJANGO_FERNET_KEY` del env, fallback
  derivado de `SECRET_KEY` para dev. Documenta que producción **debe**
  setear `DJANGO_FERNET_KEY` para que rotar `SECRET_KEY` no invalide
  los tokens almacenados.
- **`django-simple-history`** habilitado:
  - `Tenant`, `TenantRole`, `User` (excluyendo password/last_login),
    `InvitationCode`, `Reservation`, `Payment` ahora llevan `HistoricalRecords`.
  - `simple_history.middleware.HistoryRequestMiddleware` añadido para
    capturar el usuario que origina cada cambio.
- **Rate limiting** con `django-ratelimit`:
  - Login (`/api/auth/token/`) → 10 POST/min/IP.
  - Signup (`/api/auth/register/`) → 5 POST/h/IP.
  - Configurable: `RATELIMIT_ENABLE=False` desactiva (auto-off durante
    `manage.py test`).
- **Healthcheck** `GET /healthz` (sin auth): `{status: ok|degraded, db: bool}`.
  Sirve para el health check del ALB / liveness probe.

**Tests añadidos (14 nuevos, total 59):**
- `apps/ops/tests/test_ops.py`: auto-creación de tarea de limpieza,
  CLEANER scoping (sólo ve sus tareas, sólo completa las suyas), render
  de plantilla con placeholders, descarga voucher PDF (verifica magic
  bytes `%PDF`).
- `apps/core/tests/test_security_and_history.py`: round-trip de Fernet,
  manejo de None/'', detección de tampering, healthcheck OK, historial
  de Tenant capturando renombrados, Google credential cifrado al guardar
  y nunca devuelto en claro, MEMBER no accede a credenciales, sync
  endpoint stub devuelve `not_configured`.

### Frontend Sprint 4

**API client (`lib/api.ts`)**

Nuevos tipos: `OpsTask`, `MessageTemplate`, `RenderedMessage`,
`GoogleCalendarCredential`, `GoogleSyncResult`. Funciones:
`fetchTasks/createTask/updateTask/completeTask`,
`fetchMessageTemplates/createMessageTemplate/deleteMessageTemplate`,
`renderMessage`, `downloadVoucherPdf`,
`fetchGoogleCalendarCredential/saveGoogleCalendarCredential/
deleteGoogleCalendarCredential`, `syncReservationToGoogle`.

**Páginas**

- **`/tareas`** (NUEVA): KPIs por estado (Pendientes / En curso / Hechas /
  Canceladas), filtro por estado, formulario para crear tarea manual,
  acciones "Empezar" y "Marcar hecha". Botón Empezar pasa a IN_PROGRESS;
  Marcar hecha llama a `/complete/` que setea `completed_at`.
  - **Vista CLEANER** simplificada: el sidebar conmuta automáticamente a
    "Mis tareas" + "Mi cuenta" cuando el usuario tiene
    `system_role=CLEANER`. La página oculta KPIs y formulario, sólo
    muestra el listado de tareas asignadas.
- **`/plantillas`** (NUEVA): editor de plantillas con paleta de
  placeholders pegables. Renderizador que toma plantilla + reserva y
  devuelve subject/body, con copia al portapapeles. Botón "PDF" para
  descargar el voucher de la reserva seleccionada (reusa
  `downloadVoucherPdf`).
- **`/integraciones`** (extendida): nuevo panel "Configurar Google
  Calendar" sólo visible para `users:admin`. Permite escribir el
  `refresh_token` (campo `password` en HTML para que no quede en
  histórico de autocompletar), eligir `calendar_id`, marcar
  `is_active`. Muestra si ya hay un token guardado sin nunca exponerlo.
- **Sidebar** (`app-shell.tsx`): añade "Tareas" y "Plantillas". CLEANER
  ve un sidebar reducido con sólo "Mis tareas" y "Mi cuenta".

### Por qué (decisiones)

- **Tasks van en `apps/ops` y no en `apps/booking`**: separación de
  responsabilidades. La generación automática de tareas es un side-effect
  de booking, pero el dominio de operaciones (limpieza, mantenimiento,
  inspección) tiene su propia lógica que no debería contaminar el
  motor de reservas. Si en el futuro hay tareas independientes de
  reservas (mantenimiento programado), siguen viviendo en ops.
- **CLEANER scoping vía permission custom + queryset filter**: dos capas
  de defensa. La permission deja pasar a CLEANER aunque no tenga role,
  y el queryset filtra automáticamente. Si alguna mutación se cuela
  via PATCH, el viewset también valida `task.assigned_to_id == user.id`
  antes de aceptar.
- **Render de plantilla sin enviar**: evita locking-in con un proveedor
  (Twilio, Meta WhatsApp Cloud, SendGrid). El operador genera el texto
  y lo pega/envía por su canal de preferencia. Cuando el negocio decida
  un proveedor, se añade un botón "Enviar" que llama a su API.
- **Voucher con reportlab y no WeasyPrint**: WeasyPrint requiere
  GTK/Cairo/Pango en el sistema operativo, lo que es un dolor en Windows
  y aumenta el tamaño de la imagen Docker. reportlab es 100% Python y
  suficiente para un PDF de 1 página estructurado en tablas.
- **Fernet en lugar de cifrado a nivel de DB (pgcrypto)**: portátil
  entre SQLite (dev) y Postgres (prod). El costo es perder búsqueda por
  el campo cifrado, pero no es necesario buscar tokens.
- **Google Calendar como adapter stub**: la implementación real necesita
  registrar app en Google Cloud Console, manejar OAuth2 con flask-style
  redirects, y un worker periódico para refrescar tokens. Es una
  feature de varios días, fuera del scope de hardening. El stub deja la
  interfaz lista para que cuando alguien lo implemente sólo tenga que
  reemplazar el cuerpo de `sync_reservation()`.
- **History sin endpoint REST aún**: las tablas históricas se llenan
  automáticamente. Para consultarlas hay que ir a Django Admin o
  escribir queries puntuales. Un endpoint REST `/audit/?model=&id=`
  queda pendiente — ver `NEXT_STEPS.md`.

### Limitaciones conocidas

- Google Calendar es stub: NO sincroniza con la API real. El frontend
  permite guardar el refresh_token cifrado, pero el job de sync no
  existe. Si alguien lo activa con `is_active=True`, el adapter sólo
  loggea "would sync" y devuelve `stub_ok`.
- `MessageTemplate` no soporta condicionales ni loops (sólo `{{var}}`).
  Si se necesita lógica más compleja, migrar a Jinja2.
- Las tablas históricas de simple-history pueden crecer mucho. En prod
  hay que configurar `simple_history.utils.bulk_create_with_history` y
  un job de archivado periódico.
- Rate limit usa el cache backend default (LocMemCache en dev). En
  producción multi-instancia hay que configurar Redis para que las
  cuotas se compartan entre workers.

---

## 2026-05-14 — Sprint 2 + 3: Motor de tarifas, líneas, pagos manuales, contabilidad analítica, Excel

### Backend

**Modelos nuevos**

- `apps/booking/models.py`:
  - `PriceRule` — tarifas dinámicas por fecha + propiedad. `is_percent`,
    `modifier`, `min_nights`, `priority`, M2M a propiedades (vacío = todas).
  - `ReservationLine` — desglose de cobros (NIGHT/FEE/EXTRA/DISCOUNT) con
    M2M a `Tax`. Auto-generadas al crear la reserva.
  - `Reservation` ahora tiene: `tax_total`, `amount_paid`, `agent_commission`,
    `payment_status` (PENDING/PARTIAL/PAID/OVERPAID). Status acepta también
    CHECKED_IN / CHECKED_OUT.
- `apps/finance/models.py`:
  - `Tax` (PERCENT|FIXED) con `apply_to(base)` para calcular impuesto.
  - `AnalyticAccount` — centro de costo, OneToOne con `Property` (auto-creado).
  - `AnalyticLine` — apuntes contables. `category` ∈ INCOME, CLEANING_COST,
    MAINTENANCE, UTILITIES, COMMISSION, OTHER_EXPENSE, OTHER_INCOME.
    Normalización automática: gasto siempre negativo, ingreso siempre positivo.
  - `Payment` — registro manual (CASH/TRANSFER/OTHER, sin pasarelas online).
    Tipos ADVANCE/BALANCE/REFUND. Tras cada pago, se recalcula
    `Reservation.amount_paid` y `payment_status` atómicamente.
- `apps/inventory/Property` ahora tiene `is_active` y al crearse genera su
  `AnalyticAccount` (vía `save()` → `ensure_cost_center_for_property`).

**Servicios**

- `apps/booking/services.py`:
  - `calculate_quote()` reescrito: ahora itera por noche, resuelve la regla
    aplicable (desempate por priority y luego por especificidad), retorna
    `nights_breakdown`, `applied_rule_names`, `min_nights_required`.
  - `create_reservation()`: calcula `agent_commission`, crea las
    `ReservationLine`s automáticas (NIGHT + FEE) y, si la reserva queda
    confirmada/checked-in, llama `accrue_reservation_income`.
  - `recompute_reservation_totals()` para cuando se editen líneas a futuro.
- `apps/finance/services.py`:
  - `ensure_cost_center_for_property` (idempotente).
  - `accrue_reservation_income` (idempotente, también crea la línea de comisión).
  - `register_payment` / `delete_payment` con recálculo automático del
    `payment_status`.
  - `register_expense` (gastos manuales como AnalyticLine negativo).
  - `get_profit_and_loss(account?, from?, to?)` → income/expenses/net + by_category.
  - `build_pnl_xlsx`, `build_payments_xlsx`, `build_occupancy_xlsx` con
    openpyxl (instalación añadida a requirements.txt).
  - `get_property_month_metrics` ahora calcula también ADR.

**Endpoints REST nuevos**

- `GET/POST /api/tenants/<id>/finance/taxes/` + detalle CRUD.
- `GET /api/tenants/<id>/finance/cost-centers/` + detalle (read+update).
- `GET /api/tenants/<id>/finance/analytic-lines/?account_id=&from=&to=`.
- `POST /api/tenants/<id>/finance/expenses/` (registra gasto manual).
- `GET/POST/DELETE /api/tenants/<id>/finance/payments/`.
- `GET /api/tenants/<id>/finance/profit-and-loss/?account_id=&from_date=&to_date=`.
- `GET /api/tenants/<id>/finance/reports/pnl.xlsx?year=`.
- `GET /api/tenants/<id>/finance/reports/occupancy.xlsx?year=`.
- `GET /api/tenants/<id>/finance/reports/payments.xlsx?from=&to=`.
- `GET/POST /api/tenants/<id>/booking/price-rules/` + detalle CRUD.

**Tests añadidos**

- `apps/booking/tests/test_price_rules.py` — quote sin reglas, percent rule,
  min_nights rejection, prioridades, comisión de agente al crear reserva.
- `apps/finance/tests/test_payments_and_pnl.py` — auto-creación de cost
  center, devengo de ingresos idempotente, pago parcial/completo/refund,
  POST /payments/ end-to-end, gasto manual negativo, P&L endpoint, descarga
  de Excel real (verifica content-type y bytes).

**Total tests**: 28 → **45 tests verdes**.

**Migraciones**

- `inventory/0002_property_is_active.py`
- `booking/0003_*` — PriceRule, ReservationLine (sin M2M aún), nuevos campos
  en Reservation.
- `finance/0001_initial.py` — Tax, AnalyticAccount, AnalyticLine, Payment.
- `booking/0004_*` — añade el M2M ReservationLine→Tax (split por dependencia
  circular).

### Frontend

**API client (`lib/api.ts`)**

Tipos y helpers nuevos: `Tax`, `PriceRule`, `CostCenter`, `PaymentItem`,
`AnalyticLineItem`, `ProfitAndLoss`, `ExpenseCategory`. Funciones:
`fetchTaxes/createTax/deleteTax`, `fetchPriceRules/createPriceRule/
deletePriceRule`, `fetchCostCenters`, `fetchPayments/createPayment/
deletePayment`, `createExpense/fetchAnalyticLines`, `fetchProfitAndLoss`,
y los descargadores `downloadPnLXlsx`, `downloadOccupancyXlsx`,
`downloadPaymentsXlsx` (binario via blob → anchor click).

**Páginas**

- **`/pagos`** (NUEVA) — KPIs por método, formulario para registrar
  pago manual (selector de reserva, fecha, monto, tipo, método, referencia,
  notas), tabla histórica con borrado, descarga Excel. Gating estricto por
  `finance:read` y `finance:write`.
- **`/contabilidad`** (NUEVA) — selector de centro de costo y año, tarjetas
  P&L (ingresos/gastos/neto), desglose por categoría, formulario para
  registrar gasto operativo (categorías limitadas a expenses), tabla de
  movimientos del período, descarga P&L y Ocupación en Excel. Gating por
  `finance:read`/`write`.
- **Sidebar** (`app-shell.tsx`) — nuevos links: Pagos (Wallet icon),
  Contabilidad (BookOpen icon).

### Por qué (decisiones)

- **PriceRule por noche, no por reserva**: permite escenarios "fin de semana
  +20% pero entre semana sin recargo" sin truncar a una sola tarifa.
- **`amount_paid` y `payment_status` son CACHE en `Reservation`**: para
  evitar agregaciones en cada query del calendario. Se recalculan
  atómicamente cuando se crea/borra un Payment.
- **Refunds NO son negativos en `amount`**: se guardan como cantidades
  positivas con `type=REFUND`. La lógica de `_recompute_payment_status`
  los resta del total. Esto facilita reportes ("total reembolsado este mes").
- **AnalyticLine normaliza el signo en `save()`**: el operador escribe
  "registró un gasto de 80" sin pensar en signos; el modelo se encarga
  de convertirlo a -80.
- **Cost center auto-creado en `Property.save()`**: invariante del dominio.
  Toda propiedad rentable necesita un centro de costos; lo aseguramos en
  el modelo, no en el view o el serializer.
- **Excel se genera con openpyxl en memoria** y se devuelve como blob.
  Sin almacenamiento intermedio. Para reportes muy grandes habrá que
  considerar streaming.

### Limitaciones conocidas

- `ReservationLine` ya soporta impuestos (M2M a `Tax`), pero las reservas
  auto-generadas no aplican impuestos por default. Falta UI para editar
  líneas y asignar `Tax` (Sprint 4 / siguiente iteración).
- El P&L incluye comisiones de agente en su categoría
  (`AnalyticLineCategory.COMMISSION`), pero la línea sólo se crea al
  *crear* la reserva, no al cambiarle el agente después. Si se modifica
  el agente, hay que recrear el devengo manualmente.
- Los Excel no se firman digitalmente. Si la contabilidad legal exige
  firma, necesita PDF firmado adicional (futuro).

---

## 2026-05-13 — Sprint 0: Acceso controlado y limpieza

### Backend

**Añadido**

- Modelo `InvitationCode` en `apps/core/models.py` con dos propósitos
  (`CREATE_TENANT` / `JOIN_TENANT`), `max_uses`, `expires_at`,
  `consume()` atómico, audit trail.
- Endpoint `GET /api/me/` (returns user + tenant + permissions
  resolvidos contra `system_role`).
- Endpoint `/api/tenants/<id>/invitation-codes/` (CRUD de códigos
  JOIN_TENANT, requiere USERS:admin).
- Comando `manage.py issue_invite_code` para super-admin CLI.
- Django Admin enriquecido para `InvitationCode` (con acción "Generar
  código" y display de estado), `Tenant` (con acciones de
  activar/desactivar).
- Servicios `issue_create_tenant_code()`, `issue_join_tenant_code()`,
  `resolve_invitation_code()`.
- Helper `safe_readonly_permissions()` en `constants.py`.
- Tests: `test_invitation_codes_api.py`, `test_privacy.py`. +10 tests
  nuevos. Suite completa: 28 tests verdes.

**Modificado**

- `UserRegistrationSerializer` ahora **siempre** requiere
  `invitation_code`. El propósito del código decide si se crea un
  tenant nuevo o se une a uno existente.
- El rol seeded "Solo Lectura" ahora arranca con `users=none` y
  `finance=none` (antes era todo `read`). Privacidad por default.
- `TenantSerializer.to_representation()` filtra
  `integration_config={}` para usuarios no-OWNER.
- `TenantViewSet` perdió la action `create`. Ya no hay
  `POST /api/tenants/` público.
- `apps/core/services.DEFAULT_TENANT_INTEGRATIONS` reducido a sólo
  `google_calendar` (status pending). Eliminados los 5 mocks
  (Airbnb, Booking, Channel, Stripe, Mailchimp).
- `default_read_permissions()` ahora delega en
  `safe_readonly_permissions()`.

**Eliminado / Deprecated**

- `POST /api/tenants/` (era el signup público antiguo).
- Endpoint legacy de creación pública de tenants.
- 5 integraciones mock que confundían a usuarios pensando que
  funcionaban.

### Frontend

**Añadido**

- `auth-provider.tsx` ahora carga `/api/me/` al iniciar y expone
  `me`, `permissions`, helper `can(module, level)`, `refreshMe()`.
- Helper `hasPermission()` en `lib/api.ts`.
- Helper `register()` único (reemplaza
  `registerNewTenant`/`registerJoinTenant`).
- Funciones `fetchInvitationCodes()`, `createInvitationCode()`,
  `deactivateInvitationCode()`, `fetchCurrentUser()`.
- Tipos `CurrentUserResponse`, `InvitationCode`, `PermissionMap`.
- Página `/login` reescrita con UX clara: el código va primero, hay
  helper textual para el subdominio explicando que NO es un dominio,
  banner explicativo del flujo.
- Página `/settings` reescrita con panel de gestión de invitation
  codes (generar, copiar, desactivar) y gating por permisos
  (MEMBER ve banner "no tienes permisos" en lugar de los datos del
  equipo).

**Eliminado**

- `registerNewTenant`, `registerJoinTenant`, `createTenant`,
  `updateTenantInvitationCode` en `lib/api.ts`.

### Documentación

- Carpeta `documentacion/` creada como punto de entrada técnico:
  `README.md`, `STATE.md`, `ARCHITECTURE.md`, `AUTH_FLOW.md`,
  `API.md`, `PRIVACY_AND_RBAC.md`, `FRONTEND.md`, `SETUP.md`,
  `NEXT_STEPS.md`, `CHANGELOG.md`.
- `docs/ai/user_stories.md` actualizado: añadida Épica 0 (acceso
  controlado), eliminadas US de pasarela de pago, marcadas las
  completadas.

### Migraciones

- `apps/core/migrations/0002_invitation_codes_and_cleanup.py` (crea
  `InvitationCode`).

### Bugs arreglados

- Subdominio aceptaba `xxx.com` en el frontend pero el backend
  respondía error críptico. Ahora el frontend valida client-side y
  muestra mensaje claro: "Solo minúsculas, números y guiones. No
  incluyas '.com' ni espacios."
- "Empresa a unirte" era ambiguo. Ahora dice "Subdominio de la
  empresa (opcional)" porque el código ya identifica al tenant.
- "Código de invitación" no decía dónde conseguirlo. Ahora hay un
  banner que explica.
- Un MEMBER veía toda la información del OWNER (email, branding,
  invitation code) en `/settings`. Arreglado por las 3 capas de
  privacidad descritas en `PRIVACY_AND_RBAC.md`.

### Por qué (decisiones)

- **Bloqueamos signup público** porque el modelo de negocio del SaaS
  es B2B handpicked: el operador conoce a sus clientes y los onboarda
  manualmente. Evita spam, costos de hosting innecesarios y elimina
  la necesidad de verificar emails/cards.
- **InvitationCode como modelo aparte** (no campo en Tenant) porque
  permite expirar, contar usos, auditar y soportar dos flujos
  distintos (crear vs unirse) con el mismo mecanismo.
- **Eliminamos integraciones mock** porque mostraban "connected" sin
  hacer nada y confundían al usuario. Mejor tener sólo lo que
  realmente vamos a implementar (Google Calendar).
- **Default Solo Lectura sin USERS/FINANCE** porque por privacidad
  los datos de equipo y plata deben ser opt-in, no opt-out.

---

## Antes (Sprint 1 inicial — pre-2026-05-13)

Trabajo realizado por el equipo previo. Resumen:

- Setup Django/DRF/JWT, base multi-tenant.
- CRUD de Properties, Amenities, Contacts, Leads.
- Booking con quote/availability/create.
- Finance analytics (revenue mensual + ocupación).
- Frontend Next.js con páginas de Dashboard, Propiedades, Calendario,
  Finanzas, Integraciones, Settings, Login.
- 12 tests originales.

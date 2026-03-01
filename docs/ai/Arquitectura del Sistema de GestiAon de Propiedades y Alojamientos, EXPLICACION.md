- # Diccionario de Datos - Sistema de Gestión de Propiedades y Alojamientos

  Este documento detalla cada tabla, campo y relación del sistema, explicando su propósito y lógica de negocio asociada.

  ---

  ## 1. Capa SaaS (Multi-Tenancy)

  ### Tabla: `tenants` (Clientes / Empresas)
  **Descripción General del Modelo**:
  Esta entidad es la base del sistema **Multi-tenant**. Representa a cada "Cliente SaaS" (una empresa de gestión inmobiliaria o un host profesional) que paga por usar la plataforma. Su función principal es el **aislamiento de datos**: todos los queries del sistema deben filtrar obligatoriamente por `tenant_id` para asegurar que un cliente nunca vea los datos de otro. Contiene también la configuración de marca (Whitelabel) y las llaves maestras de integración.

  | Campo | Tipo | Descripción |
  | :--- | :--- | :--- |
  | `id` | UUID (PK) | Identificador único del tenant. |
  | `name` | String | Nombre de la empresa (e.g., "Caribe Rentals"). |
  | `subdomain` | String | Subdominio único para acceso (e.g., `caribe.app.com`). El middleware usa esto para identificar el tenant activo. |
  | `branding_config` | JSON | Configuración visual: `{ "logo_url": "...", "primary_color": "#FF5733" }`. Permite que la app luzca como propia del cliente. |
  | `integration_config` | JSON | Claves de API externas encriptadas: `{ "airbnb_key": "...", "whatsapp_token": "..." }`. |

  ### Tabla: `users` (Usuarios del Sistema)
  **Descripción General del Modelo**:
  Representa a una persona física con credenciales para acceder al **Panel Administrativo** (Backoffice). No confundir con "Contacts" (Huéspedes). Los usuarios son el Staff de la empresa (Administradores, Agentes de Reservas, Personal de Limpieza). Cada usuario pertenece obligatoriamente a un solo Tenant.

  | Campo | Tipo | Descripción |
  | :--- | :--- | :--- |
  | `id` | UUID (PK) | Identificador único. |
  | `email` | String | Email de login (debe ser único por Tenant). |
  | `password_hash` | String | Contraseña encriptada (bcrypt/argon2). |
  | `tenant_id` | UUID (FK) | Vincula al usuario con una empresa específica. |
  | `role` | Enum | `ADMIN` (Configuración total), `STAFF` (Solo operativo), `CLEANER` (Solo ver tareas de limpieza). |

  ---

  ## 2. Gestión de Propiedades (Inventario)

  ### Tabla: `properties` (Inmuebles / Productos)
  **Descripción General del Modelo**:
  La unidad central de negocio y el activo principal. Representa el espacio físico susceptible de ser alquilado. En términos de Odoo, esto es un `Product`.
  Cumple tres funciones clave:
  1.  **Inventario**: Controla la disponibilidad (fechas ocupadas).
  2.  **Catálogo**: Guarda la información "rica" (fotos, descripción) para mostrar al cliente.
  3.  **Centro Financiero**: Se vincula a una Cuenta Analítica para rastrear si da ganancias o pérdidas.

  | Campo | Tipo | Descripción |
  | :--- | :--- | :--- |
  | `id` | UUID (PK) | Identificador único. |
  | `tenant_id` | UUID (FK) | Tenant propietario. |
  | `name` | String | Nombre comercial (e.g., "Apto 301 - Vista Mar"). |
  | `address` | Text | Dirección física completa para generar el mapa en el Portal de Huésped. |
  | `capacity_adults` | Integer | Máximo de adultos permitidos. Valida al crear reservas. |
  | `capacity_kids` | Integer | Máximo de niños permitidos. |
  | `base_price` | Decimal | Precio por noche "desde". Es el fallback si no hay reglas de temporada. |
  | `cleaning_fee` | Decimal | Tarifa fija de limpieza que se suma automáticamente a cada reserva. |
  | `cost_center_id` | UUID (FK) | **Clave para Reportes**. Cuentas Analítica donde se imputan los ingresos/gastos de este apto. |

  ### Tabla: `amenities` (Comodidades)
  **Descripción General del Modelo**:
  Catálogo maestro de características (WiFi, Piscina, Aire Acondicionado).
  Funciona como una etiqueta (`Tag`). Su propósito es permitir filtrar propiedades ("Buscar aptos con Piscina") y mostrar iconos informativos en las cotizaciones y el portal de huésped.

  | Campo | Tipo | Descripción |
  | :--- | :--- | :--- |
  | `id` | UUID (PK) | Identificador único. |
  | `name` | String | Nombre (WiFi, Piscina, Aire Acondicionado). |
  | `icon_key` | String | Clave para renderizar el icono en frontend (e.g., `fa-wifi`, `mdi-pool`). |

  ---

  ## 3. CRM & Contactos

  ### Tabla: `contacts` (Partners)
  **Descripción General del Modelo**:
  Entidad unificada de "Terceros". Sigue el patrón `res.partner` de Odoo.
  En lugar de tener tablas separadas, centralizamos aquí a **todos** los actores externos para simplificar la gestión. Un contacto puede ser un Huésped, un Agente Comisionista (como Daniel), o una Plataforma (Airbnb).
  Esto permite, por ejemplo, que un "Agente" también pueda ser "Huésped" en el futuro sin duplicar datos.

  | Campo | Tipo | Descripción |
  | :--- | :--- | :--- |
  | `id` | UUID (PK) | Identificador único. |
  | `name` | String | Nombre completo o Razón Social. |
  | `email` | String | Correo electrónico principal. |
  | `phone` | String | Teléfono (Formato internacional +57...). Usado para integración WhatsApp. |
  | `type` | Enum | `GUEST` (Cliente Final), `AGENT` (Comisionista), `PLATFORM` (Fuente de reservas como Airbnb). |
  | `commission_rate` | Decimal | Solo aplica si `type=AGENT`. Porcentaje pactado (e.g., 10%) que se calcula sobre las ventas referidas. |

  ### Tabla: `leads` (Oportunidades de Venta)
  **Descripción General del Modelo**:
  Representa el proceso de **pre-venta**.
  Antes de que exista una reserva confirmada, existe una intención, una pregunta en WhatsApp o una consulta. Este modelo permite gestionar ese "limbo" para no ensuciar el calendario con bloqueos falsos. Permite medir la efectividad comercial (% de cierres).

  | Campo | Tipo | Descripción |
  | :--- | :--- | :--- |
  | `id` | UUID (PK) | Identificador único. |
  | `contact_id` | UUID (FK) | Cliente interesado. |
  | `source_id` | UUID (FK) | Canal de origen (Airbnb, WhatsApp Directo, Referido). Clave para saber qué canal vende más. |
  | `stage` | Enum | `NEW` (Sin contactar), `QUOTED` (Presupuesto enviado), `WON` (Reservado - Convierte a Reserva), `LOST` (Perdido). |
  | `expected_revenue` | Decimal | Valor estimado de la venta (Noches * Precio Promedio). |
  | `notes` | Text | Bitácora de seguimiento ("Cliente pide descuento", "Quiere entrar antes"). |

  ---

  ## 4. Reservas y Operaciones (Core)

  ### Tabla: `reservations` (Orden de Venta)
  **Descripción General del Modelo**:
  El objeto transaccional más importante. Representa el **contrato de ocupación** entre el Host y el Huésped.
  Maneja tres aspectos vitales:
  1.  **Tiempo**: Bloquea el calendario (Check-in/Check-out).
  2.  **Dinero Total**: Define cuánto debe pagar el cliente (suma de líneas).
  3.  **Estado**: Controla el ciclo de vida (Borrador -> Confirmado -> En Casa -> Salida).

  | Campo | Tipo | Descripción |
  | :--- | :--- | :--- |
  | `id` | UUID (PK) | Identificador único (e.g., #RES-001). |
  | `guest_id` | UUID (FK) | Cliente principal (Titular del contrato). |
  | `property_id` | UUID (FK) | Propiedad alquilada. |
  | `agent_id` | UUID (FK) | (Opcional) Agente que trajo la reserva. Se usa para liquidar comisiones. |
  | `check_in` | Datetime | Fecha y hora de entrada. |
  | `check_out` | Datetime | Fecha y hora de salida. |
  | `total_amount` | Decimal | **Computed Field**. Suma total de `reservation_lines`. |
  | `amount_paid` | Decimal | **Computed Field**. Suma de `payments` asociados. |
  | `payment_status` | Enum | Visibilidad rápida de deuda: `PENDING` (0%), `PARTIAL` (Anticipo abonado), `PAID` (Saldo completo). |
  | `status` | Enum | Ciclo de vida: `DRAFT` (Cotización), `CONFIRMED` (Reserva firme), `CHECKED_IN`, `CHECKED_OUT`, `CANCELLED`. |

  ### Tabla: `reservation_lines` (Detalle Financiero)
  **Descripción General del Modelo**:
  Permite que una reserva no sea solo un número plano, sino una factura detallada.
  Cada "concepto" cobrable es una línea. Esto da flexibilidad para agregar servicios extras (Desayuno, Transporte, Fee de Mascota) sin modificar la estructura de la reserva.
  Es aquí donde se aplican los impuestos.

  | Campo | Tipo | Descripción |
  | :--- | :--- | :--- |
  | `id` | UUID (PK) | Identificador único. |
  | `reservation_id` | UUID (FK) | Reserva padre. |
  | `type` | Enum | `NIGHT` (Cargo por noche), `FEE` (Cargo único como limpieza), `EXTRA` (Servicio opcional). |
  | `description` | String | Texto en la factura ("5 Noches Temporada Alta"). |
  | `quantity` | Integer | Cantidad (e.g., 5 noches, 1 limpieza). |
  | `unit_price` | Decimal | Precio unitario. |
  | `tax_ids` | JSON | Lista de impuestos que aplican a esta línea específica (e.g., Alojamiento tiene IVA, pero Limpieza no). |

  ---

  ## 5. Finanzas y Contabilidad Analítica

  ### Tabla: `payments` (Caja / Tesorería)
  **Descripción General del Modelo**:
  Registro **inmutable** de flujo de caja real. A diferencia de la Reserva (que dice "cuánto me deben"), esta tabla dice "cuánto dinero tengo en la mano".
  Soporta el modelo de **Anticipos**: Un pago puede ser parcial para confirmar la reserva, dejando un saldo pendiente (`balance_due`) para pagar al llegar.

  | Campo | Tipo | Descripción |
  | :--- | :--- | :--- |
  | `id` | UUID (PK) | Identificador único. |
  | `reservation_id` | UUID (FK) | Reserva que se está pagando. |
  | `date` | Date | Fecha real de recepción del dinero. |
  | `amount` | Decimal | Monto recibido. |
  | `type` | Enum | `ADVANCE` (Anticipo para bloquear fecha), `BALANCE` (Pago final). Usado para reportes de "Ingresos Futuros" vs "Realizados". |
  | `method` | Enum | Medio de pago: `CASH`, `TRANSFER`, `STRIPE`, `PAYPAL`. Facilita la conciliación bancaria. |

  ### Tabla: `analytic_accounts` (Centros de Costo)
  **Descripción General del Modelo**:
  Representa una "dimensión contable" para agrupar movimientos. Cada Propiedad tiene automáticamente una cuenta asociada.
  Permite responder la pregunta: *"¿Cuánto ganó exactamente el Apto 301 este mes?"* separando sus ingresos y gastos específicos del resto de la empresa.

  | Campo | Tipo | Descripción |
  | :--- | :--- | :--- |
  | `id` | UUID (PK) | Identificador único. |
  | `property_id` | UUID (FK) | Propiedad dueña de esta cuenta. |
  | `name` | String | Nombre descriptivo (e.g., "Cuenta Apto 301"). |
  | `balance` | Decimal | Saldo acumulado histórico (Ingresos - Gastos). |

  ### Tabla: `analytic_lines` (Apuntes Contables)
  **Descripción General del Modelo**:
  Es el "Diario Mayor" de la contabilidad analítica.
  Cada vez que se confirma una reserva, el sistema crea automáticamente líneas positivas (Ingresos) aquí.
  Cada vez que se paga una reparación o limpieza, el sistema crea líneas negativas (Gastos).
  Sumando las líneas de un periodo, obtienes el P&L (Profit & Loss).

  | Campo | Tipo | Descripción |
  | :--- | :--- | :--- |
  | `id` | UUID (PK) | Identificador único. |
  | `account_id` | UUID (FK) | Centro de costo afectado. |
  | `reference_id` | UUID (Generic FK) | ID del objeto origen (Reserva ID o Tarea ID). Permite trazabilidad. |
  | `date` | Date | Fecha del devengo. |
  | `amount` | Decimal | Valor. Positivo (+) = Ingreso, Negativo (-) = Gasto. |
  | `category` | Enum | Clasificación para reportes: `INCOME` (Alquiler), `CLEANING_COST`, `MAINTENANCE`, `UTILITIES` (Servicios públicos). |

  ---

  ## 6. Configuración

  ### Tabla: `price_rules` (Motor de Precios)
  **Descripción General del Modelo**:
  Motor lógico que permite la "Precios Dinámicos" sin intervención manual.
  Funciona como capas de reglas: El sistema busca si la fecha de la reserva cae en alguna regla activa; si sí, aplica la modificación sobre el precio base.

  | Campo | Tipo | Descripción |
  | :--- | :--- | :--- |
  | `id` | UUID (PK) | Identificador único. |
  | `name` | String | Nombre interno (e.g., "Navidad 2025"). |
  | `start_date` | Date | Inicio vigencia regla. |
  | `end_date` | Date | Fin vigencia regla. |
  | `price_modifier` | Decimal | Ajuste matemático. Puede ser Porcentaje (`1.5` = +50%) o Valor Fijo (`50`). |
  | `min_nights` | Integer | Restricción: "En Navidad mínimo 5 noches". Si no cumple, no deja reservar. |
  | `specific_days` | JSON | (Opcional) Días de la semana (e.g., "Solo Viernes y Sábados +20%"). |

  ### Tabla: `taxes` (Impuestos)
  **Descripción General del Modelo**:
  Configuración fiscal. Define qué porcentajes se deben sumar a las líneas de venta.
  Permite flexibilidad legal (e.g., IVA diferente para turismo, o exenciones).

  | Campo | Tipo | Descripción |
  | :--- | :--- | :--- |
  | `name` | String | Nombre en factura ("IVA 19%"). |
  | `value` | Decimal | Factor matemático (0.19). |
  | `type` | Enum | `PERCENT` (% sobre base), `FIXED` (Valor fijo por estancia). |
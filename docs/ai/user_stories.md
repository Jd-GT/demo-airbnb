# Historias de Usuario y Épicas (SaaS PMS)

Basado en todos los dolores actuales (manejo en Excel, control manual de pagos, falta de reportes claros, y necesidad de automatización) y en la arquitectura diseñada (Multi-tenant, Monolito Modular), aquí están definidos los requerimientos en formato Ágil.

---

## ÉPICA 1: Gestión Centralizada del Inventario y CRM
**Descripción:** Como Host, necesito dejar de usar Excel para gestionar mis propiedades, tarifas y la base de datos de mis clientes, para tener una única fuente de verdad accesible desde cualquier lugar.

*   [x] **US-1.1: Creación de Propiedades**
    *   **Como** Administrador del Tenant.
    *   **Quiero** poder registrar una nueva propiedad llenando su nombre, dirección, capacidad (adultos/niños), tarifa base y tarifa de limpieza.
    *   **Para** tener mi inventario digitalizado y listo para recibir reservas.
*   [x] **US-1.1.1: Agregar usuarios con x permisos a cada tenant**
    *   **Como** Administrador del Tenant.
    *   **Quiero** poder crear nuevos usuarios para mi inmobiliaria y asignarles permisos específicos (Ej: solo lectura, editor de reservas, administrador total).
    *   **Para** que mi equipo pueda colaborar en la plataforma sin compartir contraseñas ni dar acceso irrestricto a todo el sistema.
*   [x] **US-1.2: Gestión de Comodidades (Amenities)**
    *   **Como** Staff/Administrador.
    *   **Quiero** asignar características (WiFi, Piscina, AC) a cada propiedad.
    *   **Para** que la información detallada esté disponible al enviar cotizaciones a los clientes.
*   [x] **US-1.3: Base de Datos Única de Contactos**
    *   **Como** Agente de Reservas.
    *   **Quiero** crear y buscar contactos (Huéspedes, Comisionistas, Plataformas) por nombre, teléfono o email en un solo lugar.
    *   **Para** identificar rápidamente a clientes recurrentes y no duplicar información.
*   [x] **US-1.4: Pipeline de Ventas (Leads / Cotizaciones)**
    *   **Como** Agente de Reservas.
    *   **Quiero** registrar una consulta (Lead) de WhatsApp, indicando el cliente, fechas deseadas y el valor esperado, agrupándolos por estado (Nuevo, Cotizado, Ganado).
    *   **Para** hacer seguimiento a las ventas que aún no son reservas confirmadas y no perder clientes potenciales.
*   **US-1.5: Tarifas Dinámicas por Temporada**
    *   Nota Sprint 1: Se implementó cotización base (`/quote`) con tarifa base + limpieza, pero no reglas dinámicas de temporada.
    *   **Como** Administrador.
    *   **Quiero** crear reglas de precios (Ej: "Temporada Alta: +20% del 15 de Dic al 15 de Ene") aplicables a propiedades específicas.
    *   **Para** no tener que calcular o recordar manualmente a cuánto debo vender un apartamento en diferentes fechas.

---

## ÉPICA 2: Motor de Reservas y Calendario Unificado
**Descripción:** Como Host, necesito un sistema que cruce la disponibilidad y me permita crear reservas completas (con sus cobros adicionales y comisiones) sin riesgo de "overbooking".

*   **US-2.1: Calendario General de Ocupación**
    *   **Como** Staff/Agente de Reservas.
    *   **Quiero** visualizar un calendario tipo Gantt que me muestre todas mis propiedades y las reservas bloqueando los días.
    *   **Para** saber de un vistazo qué está disponible para vender hoy o el próximo mes.
*   [x] **US-2.2: Creación de Reserva Manual (Directa)**
    *   **Como** Agente de Reservas.
    *   **Quiero** crear una reserva seleccionando Propiedad, Cliente, Fechas de Check-in/out, la cual calcule automáticamente el costo total basado en las reglas de precio.
    *   **Para** formalizar una venta directa (WhatsApp/Referido) en el sistema.
*   [x] **US-2.3: Validación de Overbooking**
    *   **Como** Sistema (Backend).
    *   **Quiero** rechazar cualquier intento de crear o mover una reserva si las fechas interfieren con otra reserva confirmada en la misma propiedad.
    *   **Para** garantizar que nunca se le venda el mismo apartamento a dos personas en la misma fecha.
*   **US-2.4: Desglose de Cobros (Líneas de Reserva)**
    *   **Como** Agente de Reservas.
    *   **Quiero** que al crear una reserva se autogeneren las líneas de cobro (Ej: 3 Noches $X, 1 Tarifa Limpieza $Y) y poder agregar cargos extras manuales (Ej: Desayuno).
    *   **Para** tener claridad financiera de qué se le está cobrando al huésped.
*   **US-2.5: Asignación de Comisiones a Intermediarios**
    *   **Como** Administrador.
    *   **Quiero** vincular un Agente Comisionista (Ej: Daniel) a una reserva, calculando automáticamente su comisión sobre el subtotal del alojamiento.
    *   **Para** saber exactamente cuánto le debo pagar a mis vendedores a fin de mes.
*   **US-2.6: Sincronización Básica iCal (MVP)**
    *   **Como** Sistema (Integrador).
    *   **Quiero** importar periódicamente calendarios iCal de Airbnb/Booking para crear "Bloqueos" en mi calendario.
    *   **Para** evitar vender por WhatsApp fechas que ya se vendieron en las OTAs (Online Travel Agencies).

---

## ÉPICA 3: Control Financiero y Reportes de Rentabilidad (P&L)
**Descripción:** Como Host, necesito saber exactamente cuánto entra, cuánto sale, quién me debe dinero, y si un apartamento específico es rentable o está dando pérdidas.

*   **US-3.1: Registro de Anticipos (Caja)**
    *   **Como** Agente de Reservas.
    *   **Quiero** registrar que un huésped hizo un pago parcial (Anticipo 50%) detallando el método (Transferencia, Efectivo).
    *   **Para** asegurar la reserva y reflejar que el pago_status es "Parcialmente Pagado".
*   **US-3.2: Cobro de Saldos (Check-in)**
    *   **Como** Staff/Recepcionista.
    *   **Quiero** ver fácilmente cuánto saldo pendiente (Balance Due) tiene un huésped al momento de llegar, y registrar el pago final.
    *   **Para** no entregar las llaves sin haber recaudado la totalidad del dinero.
*   **US-3.3: Impuestos Configurables**
    *   **Como** Administrador.
    *   **Quiero** configurar tipos de impuestos (Ej: IVA 19%, Impuesto al Turismo local) y aplicarlos a ciertas líneas de reserva.
    *   **Para** cumplir con la legalidad contable del país sin cálculos manuales.
*   **US-3.4: Creación de Centros de Costo (Cuentas Analíticas)**
    *   **Como** Sistema (Backend).
    *   **Quiero** que al crear una Propiedad, se cree en background una Cuenta Analítica vinculada a ella.
    *   **Para** tener un "bolsillo" contable listo para recibir los ingresos y gastos de ese inmueble.
*   **US-3.5: Devengo Automático de Ingresos**
    *   **Como** Sistema (Backend).
    *   **Quiero** que al pasar una reserva a estado Confirmado/Facturado, se cree automáticamente una Línea Analítica Positiva en la Cuenta de esa Propiedad.
    *   **Para** registrar el ingreso en la "hoja de balance" del apartamento.
*   **US-3.6: Registro de Gastos Operativos**
    *   **Como** Administrador.
    *   **Quiero** registrar manualmente gastos (Servicios Públicos, Reparaciones) asignando el monto negativo a la Cuenta Analítica de una Propiedad específica.
    *   **Para** trackear las salidas de dinero reales del negocio.
*   **US-3.7: Reporte de Rentabilidad por Propiedad (P&L)**
    *   **Como** Administrador / Dueño.
    *   **Quiero** ver un reporte consolidado (Tabla/Gráfico) que sume ingresos y reste gastos de una Cuenta Analítica en un mes específico.
    *   **Para** tomar decisiones de negocio (saber cuál inmueble deja más ganancia o gasta mucho en mantenimiento).
*   **US-3.8: Reporte de Ocupación y ADR**
    *   **Como** Administrador / Dueño.
    *   **Quiero** ver el porcentaje ocupación (%) y la Tarifa Promedio Diaria (ADR) por mes y por propiedad.
    *   **Para** analizar el rendimiento comercial de mis activos.

---

## ÉPICA 4: Automatización Operativa y Comunicación
**Descripción:** Como Host, necesito reducir el tiempo de tareas mecánicas (avisar de limpiezas, enviar confirmaciones por WhatsApp) para enfocarme en crecer el negocio.

*   **US-4.1: Generación de Tareas de Limpieza**
    *   **Como** Sistema (Backend).
    *   **Quiero** que al llegar el día de "Check-out" de una reserva, se genere automáticamente una "Tarea de Limpieza" asignada a la Propiedad.
    *   **Para** que el personal de limpieza sepa a qué apartamento ir sin que tenga que avisarles por teléfono.
*   **US-4.2: Notificación al Personal (Dashboard)**
    *   **Como** Personal de Limpieza (User `CLEANER`).
    *   **Quiero** loguearme en la app y ver únicamente un listado con las tareas de limpieza del día y poder marcarlas como "Completadas".
    *   **Para** optimizar mi ruta de trabajo y notificar al recepcionista que el apto está listo.
*   **US-4.3: Plantillas de Correo/Mensajes**
    *   **Como** Administrador.
    *   **Quiero** crear plantillas de texto con variables maestras (Ej: "Hola {{guest_name}}, tu reserva en {{property_name}} está lista. Código WiFi: {{wifi_pass}}").
    *   **Para** no tener que redactar el mismo correo cientos de veces.
*   **US-4.4: Envío de Confirmación de Reserva**
    *   **Como** Agente de Reservas.
    *   **Quiero** tener un botón en la Reserva que genere un email/mensaje con la plantilla de Confirmación y se lo envíe al huésped.
    *   **Para** darle seguridad y profesionalismo al cliente.
*   **US-4.5: Descarga de Voucher PDF**
    *   **Como** Huésped / Agente de Reservas.
    *   **Quiero** poder descargar un documento en PDF (generado automáticamente con el Template Engine) que contenga los detalles oficiales de la reserva, importes pagados y políticas.
    *   **Para** tener un comprobante físico o digital oficial de mi compra.

---

## ÉPICA 5: Requerimientos No Funcionales (NFRs)
**Descripción:** Como Arquitecto/Propietario, necesito que el sistema sea seguro, rápido, escalable y mantenible para garantizar la continuidad del negocio y la protección de datos, sin importar cuántas propiedades o Tenants se agreguen.

*   [x] **NFR-5.1: Aislamiento de Datos (Multitenancy)**
    *   **RESTricción:** Los datos de un Tenant A jamás deben ser accesibles ni visibles por un usuario del Tenant B, bajo ninguna circunstancia (incluso en caso de bugs).
    *   **Medición:** Validaciones a nivel de middleware y pruebas automatizadas de intento de inyección de `tenant_id` ajeno en todos los endpoints REST.
*   **NFR-5.2: Rendimiento y Tiempos de Carga**
    *   **RESTricción:** Las consultas de disponibilidad en el calendario y las respuestas de la API pública para reservas externas deben responder en menos de 500ms al 95% de las peticiones (prevenir timeouts en integraciones web).
    *   **Medición:** Uso de caché eficiente (ej. Redis en el futuro) para tablas estáticas (Amenities) y queries optimizadas para reservas.
*   **NFR-5.3: Trazabilidad y Auditoría (Logs)**
    *   **RESTricción:** Cualquier acción crítica como: borrar una reserva, modificar un pago o cambiar una regla de precios debe dejar un rastro (quién, cuándo, valores antiguos y nuevos).
    *   **Medición:** Uso de librerías como `django-simple-history` o logs centralizados.
*   **NFR-5.4: Disponibilidad (Uptime)**
    *   **RESTricción:** El sistema en AWS debe tener un acuerdo de nivel de servicio (SLA) de 99.9% de uptime, crucial para un motor de reservas.
    *   **Medición:** Despliegue en AWS ECS (contenedores) con auto-scaling y Health Checks, además de base de datos AWS RDS Multi-AZ.
*   **NFR-5.5: Seguridad y Privacidad de Datos**
    *   **RESTricción:** Todos los datos sensibles, en especial contraseñas y claves de API de terceros (Airbnb tokens, WhatsApp tokens integrados vía tenant), deben estar fuertemente encriptados en base de datos.
    *   **Medición:** Uso de bcrypt/argon2 para contraseñas; llaves simétricas guardadas de forma segura para los tokens de integración (usando AWS KMS o variables de entorno).
*   **NFR-5.6: Diseño Responsivo (Mobile-First)**
    *   **RESTricción:** Tanto el Portal Público del Huésped como la interfaz del Dashboard Administrativo deben funcionar y visualizarse correctamente en smartphones.
    *   **Medición:** Pruebas de usabilidad bajo tamaños de pantalla inferiores a 768px; diseño usando grillas full responsivas de Tailwind CSS.

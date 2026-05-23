# Privacidad y Control de Permisos

## Por qué este documento existe

Antes había un bug: un usuario invitado a una empresa podía entrar a
`/settings` y ver el correo del dueño, los códigos de invitación y la
configuración de integraciones del tenant. Esto se arregló en Sprint 0
y este doc explica el modelo correcto para que no vuelva a pasar.

## El modelo: 3 capas

### Capa 1 — Aislamiento por tenant (multi-tenancy)

Implementación: `apps/core/middleware.py:TenantResolutionMiddleware` +
`apps/core/managers.py:TenantAwareManager` + `contextvars`.

**Garantiza:** un usuario del tenant A jamás ve filas del tenant B,
incluso si el endpoint tiene un bug.

Sigue funcionando aunque el desarrollador escriba `Property.objects.all()`
porque el manager filtra automáticamente.

### Capa 2 — Pertenencia al tenant del path

Implementación: `apps/core/permissions.py:TenantModulePermission`.

**Garantiza:** si la URL es `/api/tenants/AAA/...` y tu `user.tenant_id`
es `BBB`, el endpoint te devuelve 403. Esto previene que alguien
manipule la URL para acceder a otro tenant aunque tenga JWT válido.

(Los superusers escapan a este check.)

### Capa 3 — RBAC por módulo

Cada vista declara `permission_module` y opcionalmente
`required_permission_level`. La permission class compara contra
`user.role.permissions[module]`.

```python
class PropertyViewSet(...):
    permission_classes = [IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.INVENTORY.value
    # required_permission_level se infiere del método HTTP:
    # GET → READ, POST/PUT/PATCH/DELETE → WRITE
```

Para pedir explícitamente ADMIN:
```python
class InvitationCodeViewSet(...):
    permission_module = ModuleKey.USERS.value
    required_permission_level = PermissionLevel.ADMIN
```

## Roles default que se siembran al crear un tenant

Implementación: `apps/core/services.py:seed_default_roles`.

| Rol            | Default? | core | users | inventory | crm | booking | finance |
| -------------- | -------- | ---- | ----- | --------- | --- | ------- | ------- |
| **Admin Total** | No      | admin| admin | admin     | admin| admin  | admin   |
| **Solo Lectura** | Sí (default) | read | **none** | read | read | read | **none** |

**Por qué `users=none` y `finance=none` en Solo Lectura:**

- Listar usuarios expone correos del equipo. Es un dato sensible que
  no debería estar disponible por default.
- Datos financieros (revenue, P&L, pagos) son aún más sensibles —
  típicamente sólo el OWNER y un contador deben verlos.

Si el OWNER quiere que su equipo de "solo lectura" sí vea esto, puede
editar el rol y subir el nivel manualmente. Es opt-in, no opt-out.

## Cómo el frontend respeta los permisos

`AuthProvider` (`src/components/auth-provider.tsx`) carga `/api/me/` al
inicializar y expone:

```ts
const { me, can, refreshMe } = useAuth();

if (can("users", "admin")) {
  // mostrar gestión de invitaciones
}
if (can("finance", "read")) {
  // mostrar panel de pagos
}
```

`me.permissions` es la fuente de verdad. **Nunca** leas `system_role`
en el frontend para decidir qué ocultar — usa `can()` siempre, así si
el OWNER cambia los permisos de un rol, la UI lo respeta sin código
nuevo.

## Gating en `/settings` (caso de estudio)

```tsx
const { me, can } = useAuth();
const canManageUsers = can("users", "admin");

// Cualquiera ve su propio perfil
<Section>{me.user.email}</Section>

// Solo USERS:admin ve el equipo y los códigos
{canManageUsers ? (
  <>
    <InvitationCodesPanel />
    <TeamPanel />
  </>
) : (
  <NotEnoughPermissionsBanner />
)}
```

El backend igual rechaza con 403 si alguien intenta llamar a
`/api/tenants/<id>/invitation-codes/` sin permisos. La verificación
del frontend es para UX, no para seguridad.

## Datos que se ocultan en serializers

Algunos campos son filtrados a nivel de serializer para defensa en
profundidad:

| Campo                          | Visible para                                  |
| ------------------------------ | ---------------------------------------------- |
| `Tenant.integration_config`    | Sólo OWNER y superuser. Resto recibe `{}`.     |
| `User.password_hash`           | Nadie (no expuesto en API).                    |
| `InvitationCode.code` (futuro) | Aún se muestra al OWNER. Si en algún momento  |
|                                | un MEMBER pudiera listarlos, debe ocultarse.   |

## Checklist al añadir un endpoint nuevo

- [ ] Hereda el modelo de `TenantAwareModel`.
- [ ] El view declara `permission_module` apropiado.
- [ ] El nivel default por método HTTP es razonable (READ para GET,
      WRITE para mutaciones). Si necesitas ADMIN, declara
      `required_permission_level`.
- [ ] El serializer no devuelve campos que un MEMBER de bajo nivel
      no debería ver. Si algún campo es sensible, filtra en
      `to_representation()`.
- [ ] El test correspondiente verifica:
  - User de otro tenant no puede acceder.
  - User del mismo tenant pero sin permiso recibe 403.
  - User con el permiso correcto sí accede.

Ver `apps/core/tests/test_privacy.py` como referencia.

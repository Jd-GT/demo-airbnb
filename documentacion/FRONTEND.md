# Frontend Guide

Stack: **Next.js 15** (App Router) + **React 19** + **TypeScript** +
**Tailwind 4** + **shadcn/ui** + **Radix** + **Framer Motion**.

## Estructura

```
frontend/demo-airbnb/
├── package.json
├── next.config.ts
├── tsconfig.json
├── tailwind.config.* (definido en globals.css con @theme inline)
└── src/
    ├── app/                          # Next.js routing
    │   ├── layout.tsx                # Root layout + AuthProvider
    │   ├── page.tsx                  # / (Dashboard)
    │   ├── login/page.tsx            # /login (signup + login en una)
    │   ├── propiedades/page.tsx
    │   ├── calendario/page.tsx
    │   ├── finanzas/page.tsx
    │   ├── integraciones/page.tsx
    │   └── settings/page.tsx
    ├── components/
    │   ├── auth-provider.tsx         # Context global de auth + permisos
    │   ├── app-shell.tsx             # Layout con sidebar
    │   ├── page-feedback.tsx         # LoadingCard / ErrorCard / EmptyCard
    │   └── ui/                       # shadcn components
    ├── hooks/
    │   ├── use-async-data.ts         # Data fetching con cancel
    │   └── use-mobile.ts
    └── lib/
        ├── api.ts                    # Cliente HTTP + tipos + helpers
        └── utils.ts                  # cn()
```

## Convenciones

### Auth siempre via `useAuth()`

```tsx
import { useAuth, useLogout } from "@/components/auth-provider";

const { me, can, refreshMe } = useAuth();
```

- `me` es el `CurrentUserResponse` o `null`.
- `can(module, level)` → boolean. Úsalo para condicionar UI.
- Después de mutaciones que cambien el perfil/tenant, llama `refreshMe()`.

### Llamadas al backend siempre via `lib/api.ts`

No escribas `fetch` directamente en componentes. El cliente ya:

- Adjunta el JWT.
- Refresca tokens automáticamente en 401.
- Extrae mensajes de error del payload.
- Usa el tenant ID del localStorage para los endpoints scoped.

Si necesitas un endpoint nuevo, exporta una función ahí. Ejemplo:

```ts
// lib/api.ts
export async function fetchPriceRules(): Promise<PriceRule[]> {
  const tenantId = getRequiredTenantId();
  return fetchApi<PriceRule[]>(`/api/tenants/${tenantId}/booking/price-rules/`);
}
```

### Páginas siguen el mismo patrón

```tsx
"use client";
import { useEffect, useState, useCallback } from "react";
import AppShell from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { fetchSomething } from "@/lib/api";

export default function MyPage() {
  const { can, me } = useAuth();
  const [data, setData] = useState<Foo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await fetchSomething()); }
    catch (e) { setError(e instanceof Error ? e.message : "..."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (!can("inventory", "read")) return <NoPermissionView />;
  return (
    <AppShell>
      {loading ? <LoadingCard/> : <DataTable rows={data}/>}
    </AppShell>
  );
}
```

### Estilos

- Tailwind 4 con `@theme inline` declarado en `globals.css`.
- Tokens custom: `--gold`, `--glass-card` (efecto glassmorphism).
- Helpers: `glass-card`, `text-gold-gradient`.
- `cn()` (de `lib/utils.ts`) para merger condicionales.

### Formularios

`react-hook-form` + `zod` están instalados pero **aún no usados**. Para
formularios nuevos:

1. Define el schema con zod.
2. Usa `useForm({resolver: zodResolver(schema)})`.
3. Envuelve cada field con `<Form>` de `components/ui/form.tsx`.

Esto va a unificar manejo de errores y validación. Lo dejamos pendiente
para Sprint 2.

## Estado pendiente del frontend

Ver `STATE.md`. Los puntos importantes:

- **CRUD UI** para propiedades, amenities, contactos, leads, reservas,
  usuarios, roles. Sólo el listado existe.
- **Calendario interactivo** (drag&drop). La vista mensual actual es
  read-only.
- **Validación con react-hook-form + zod** para los formularios nuevos.
- **Mobile-first**: el shell ya es responsive, pero las tablas largas
  no se adaptan bien a móvil. Necesita cards en pantallas pequeñas.

## Cómo agregar una página nueva

1. Crea `src/app/<ruta>/page.tsx`. Comienza con `"use client";`.
2. Si requiere auth (la mayoría), envuélvelo en `AppShell`.
3. Usa `useAuth()` para gating.
4. Pon las llamadas al API en `src/lib/api.ts` y consúmelas con
   `useAsyncData` (hay un hook reutilizable).
5. Añade un link en `src/components/app-shell.tsx` para que aparezca
   en el sidebar.

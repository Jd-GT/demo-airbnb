"use client";

/**
 * Lightweight JWT helpers backed by localStorage.
 *
 * Originally a standalone module before the merge with main introduced
 * `auth-provider.tsx`. The provider now talks to /api/me/ on its own, but
 * `api.ts` still imports primitives from here, so this file keeps them
 * available and uses the same storage keys the rest of the app already
 * understands.
 */

const ACCESS_KEY = "demo-airbnb.access_token";
const REFRESH_KEY = "demo-airbnb.refresh_token";
const USER_KEY = "demo-airbnb.current_user";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export type StoredUser = {
  id?: string;
  email?: string;
  full_name?: string;
  tenant_id?: string | null;
  tenant?: { id?: string } | null;
  [key: string]: unknown;
};

type LoginResponse = {
  access?: string;
  refresh?: string;
  access_token?: string;
  refresh_token?: string;
  user?: StoredUser;
  tenant_id?: string;
};

type Session = {
  access: string;
  refresh: string;
  tenantId: string;
  user: StoredUser;
};

function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  return window.localStorage;
}

export function getAccessToken(): string | null {
  return storage()?.getItem(ACCESS_KEY) ?? null;
}

export function getRefreshToken(): string | null {
  return storage()?.getItem(REFRESH_KEY) ?? null;
}

export function getCurrentUser(): StoredUser | null {
  const raw = storage()?.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredUser;
  } catch {
    storage()?.removeItem(USER_KEY);
    return null;
  }
}

function persist(access: string, refresh: string, user: StoredUser) {
  const s = storage();
  if (!s) return;
  s.setItem(ACCESS_KEY, access);
  s.setItem(REFRESH_KEY, refresh);
  s.setItem(USER_KEY, JSON.stringify(user));
}

function clear() {
  const s = storage();
  if (!s) return;
  s.removeItem(ACCESS_KEY);
  s.removeItem(REFRESH_KEY);
  s.removeItem(USER_KEY);
}

function resolveTenantId(payload: LoginResponse): string {
  if (payload.tenant_id) return payload.tenant_id;
  if (payload.user?.tenant_id) return payload.user.tenant_id;
  if (payload.user?.tenant?.id) return payload.user.tenant.id;
  return "";
}

export async function login(email: string, password: string): Promise<Session> {
  const response = await fetch(`${API_BASE_URL}/api/auth/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(text || "Credenciales invalidas.");
  }

  const payload = (await response.json()) as LoginResponse;
  const access = payload.access ?? payload.access_token ?? "";
  const refresh = payload.refresh ?? payload.refresh_token ?? "";
  const user = payload.user ?? ({} as StoredUser);
  const tenantId = resolveTenantId(payload);

  if (!access || !refresh) {
    throw new Error("Respuesta de login invalida (faltan tokens).");
  }

  persist(access, refresh, { ...user, tenant_id: tenantId || user.tenant_id });

  return { access, refresh, tenantId, user };
}

export async function logout(): Promise<void> {
  const refresh = getRefreshToken();
  if (refresh) {
    try {
      await fetch(`${API_BASE_URL}/api/auth/logout/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getAccessToken() ?? ""}`,
        },
        body: JSON.stringify({ refresh }),
      });
    } catch {
      // Best-effort: clearing local state is what matters.
    }
  }
  clear();
}

export async function refreshToken(): Promise<string> {
  const refresh = getRefreshToken();
  if (!refresh) {
    throw new Error("No refresh token stored.");
  }

  const response = await fetch(`${API_BASE_URL}/api/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });

  if (!response.ok) {
    clear();
    throw new Error("No fue posible refrescar la sesion.");
  }

  const payload = (await response.json()) as { access?: string };
  const access = payload.access ?? "";
  if (!access) {
    throw new Error("Refresh devolvio respuesta vacia.");
  }

  const s = storage();
  s?.setItem(ACCESS_KEY, access);
  return access;
}

export async function authenticatedFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);
  const access = getAccessToken();
  if (access && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${access}`);
  }
  if (!headers.has("Content-Type") && init.body && typeof init.body === "string") {
    headers.set("Content-Type", "application/json");
  }

  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
  let response = await fetch(url, { ...init, headers });

  if (response.status === 401 && getRefreshToken()) {
    try {
      const newAccess = await refreshToken();
      headers.set("Authorization", `Bearer ${newAccess}`);
      response = await fetch(url, { ...init, headers });
    } catch {
      // refreshToken already cleared storage; bubble the original 401.
    }
  }

  return response;
}

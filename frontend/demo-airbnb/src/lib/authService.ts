const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  'http://localhost:8000'
).replace(/\/$/, '');

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_KEY = 'user';

export const AUTH_UNAUTHORIZED_EVENT = 'demo-airbnb:auth-unauthorized';

export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  system_role: string;
  tenant_id: string | null;
};

export type LoginResult = {
  access_token: string;
  refresh_token: string;
  user: AuthUser;
};

export type SignUpInput = {
  email: string;
  full_name: string;
  password: string;
  tenant_name: string;
  subdomain: string;
  account_type: 'guest' | 'booking_agent';
};

export type TenantOwner = {
  id: string;
  email: string;
  full_name: string;
  system_role: string;
};

export type TenantResponse = {
  id: string;
  name: string;
  subdomain: string;
  owner?: TenantOwner;
};

export type SignUpResult = LoginResult & {
  tenant: TenantResponse;
};

type TokenResponse = {
  access_token?: string;
  refresh_token?: string;
  access?: string;
  refresh?: string;
  user?: AuthUser;
};

type RefreshResponse = {
  access_token?: string;
  access?: string;
};

type ApiRequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown;
};

export class AuthServiceError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown = null) {
    super(message);
    this.name = 'AuthServiceError';
    this.status = status;
    this.payload = payload;
  }
}

function getStorage(): Storage | null {
  if (typeof window === 'undefined') {
    return null;
  }

  return window.localStorage;
}

function buildUrl(path: string) {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }

  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
}

async function parseBody(response: Response) {
  const text = await response.text();

  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function getErrorMessage(payload: unknown, fallback: string) {
  if (typeof payload === 'string') {
    return payload;
  }

  if (!payload || typeof payload !== 'object') {
    return fallback;
  }

  const record = payload as Record<string, unknown>;

  if (typeof record.detail === 'string') {
    return record.detail;
  }

  if (Array.isArray(record.non_field_errors) && record.non_field_errors.length > 0) {
    return String(record.non_field_errors[0]);
  }

  for (const [field, value] of Object.entries(record)) {
    if (Array.isArray(value) && value.length > 0) {
      return `${field}: ${String(value[0])}`;
    }

    if (typeof value === 'string') {
      return `${field}: ${value}`;
    }
  }

  return fallback;
}

async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const body =
    options.body === undefined
      ? undefined
      : typeof options.body === 'string'
        ? options.body
        : JSON.stringify(options.body);

  if (body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  let response: Response;

  try {
    response = await fetch(buildUrl(path), {
      ...options,
      headers,
      body,
    });
  } catch (error) {
    throw new AuthServiceError(
      'No se pudo conectar con el servidor. Revisa tu conexion e intenta de nuevo.',
      0,
      error,
    );
  }

  const payload = await parseBody(response);

  if (!response.ok) {
    throw new AuthServiceError(
      getErrorMessage(payload, `La solicitud fallo con estado ${response.status}.`),
      response.status,
      payload,
    );
  }

  return payload as T;
}

function normalizeLoginResponse(response: TokenResponse): LoginResult {
  const accessToken = response.access_token ?? response.access;
  const refreshToken = response.refresh_token ?? response.refresh;

  if (!accessToken || !refreshToken || !response.user) {
    throw new AuthServiceError('La respuesta de autenticacion no tiene el formato esperado.', 500, response);
  }

  return {
    access_token: accessToken,
    refresh_token: refreshToken,
    user: response.user,
  };
}

function storeSession(session: LoginResult) {
  const storage = getStorage();

  storage?.setItem(ACCESS_TOKEN_KEY, session.access_token);
  storage?.setItem(REFRESH_TOKEN_KEY, session.refresh_token);
  storage?.setItem(USER_KEY, JSON.stringify(session.user));
}

function emitUnauthorized() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT));
  }
}

export async function login(email: string, password: string): Promise<LoginResult> {
  const response = await apiRequest<TokenResponse>('/api/auth/token/', {
    method: 'POST',
    body: { email, password },
  });
  const session = normalizeLoginResponse(response);
  storeSession(session);
  return session;
}

export async function signup(input: SignUpInput): Promise<SignUpResult> {
  const tenant = await apiRequest<TenantResponse>('/api/tenants/', {
    method: 'POST',
    body: {
      name: input.tenant_name,
      subdomain: input.subdomain,
      owner_email: input.email,
      owner_full_name: input.full_name,
      owner_password: input.password,
      branding_config: {
        signup_account_type: input.account_type,
      },
    },
  });

  const session = await login(input.email, input.password);

  return {
    ...session,
    tenant,
  };
}

export async function logout(): Promise<void> {
  const accessToken = getAccessToken();
  const refreshToken = getRefreshToken();

  try {
    if (accessToken) {
      await apiRequest('/api/auth/logout/', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: refreshToken ? { refresh_token: refreshToken } : undefined,
      });
    }
  } catch {
    // Local logout still succeeds even if the server request fails.
  } finally {
    clearAuthStorage();
  }
}

export async function refreshToken(): Promise<string> {
  const storedRefreshToken = getRefreshToken();

  if (!storedRefreshToken) {
    clearAuthStorage();
    throw new AuthServiceError('No hay refresh token disponible.', 401);
  }

  try {
    const response = await apiRequest<RefreshResponse>('/api/auth/token/refresh/', {
      method: 'POST',
      body: { refresh: storedRefreshToken },
    });
    const accessToken = response.access_token ?? response.access;

    if (!accessToken) {
      throw new AuthServiceError('La respuesta de refresh no tiene access token.', 500, response);
    }

    getStorage()?.setItem(ACCESS_TOKEN_KEY, accessToken);
    return accessToken;
  } catch (error) {
    clearAuthStorage();
    emitUnauthorized();
    throw error;
  }
}

export function getCurrentUser(): AuthUser | null {
  const storage = getStorage();
  const rawUser = storage?.getItem(USER_KEY);

  if (!rawUser) {
    return null;
  }

  try {
    return JSON.parse(rawUser) as AuthUser;
  } catch {
    storage?.removeItem(USER_KEY);
    return null;
  }
}

export function getAccessToken(): string | null {
  return getStorage()?.getItem(ACCESS_TOKEN_KEY) ?? null;
}

export function getRefreshToken(): string | null {
  return getStorage()?.getItem(REFRESH_TOKEN_KEY) ?? null;
}

export function clearAuthStorage() {
  const storage = getStorage();
  storage?.removeItem(ACCESS_TOKEN_KEY);
  storage?.removeItem(REFRESH_TOKEN_KEY);
  storage?.removeItem(USER_KEY);
}

export async function authenticatedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const accessToken = getAccessToken();

  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  let response = await fetch(buildUrl(path), {
    ...init,
    headers,
  });

  if (response.status === 401 && getRefreshToken()) {
    try {
      const refreshedAccessToken = await refreshToken();
      headers.set('Authorization', `Bearer ${refreshedAccessToken}`);
      response = await fetch(buildUrl(path), {
        ...init,
        headers,
      });
    } catch {
      return response;
    }
  }

  if (response.status === 401) {
    clearAuthStorage();
    emitUnauthorized();
  }

  return response;
}

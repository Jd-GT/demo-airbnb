import {
  authenticatedFetch,
  getAccessToken,
  getCurrentUser,
  getRefreshToken,
  login as authLogin,
  logout as authLogout,
  refreshToken as refreshAuthToken,
} from "./authService";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

const SESSION_STORAGE_KEY = "demo-airbnb.session.v1";

const DEMO_TENANT = {
  name: "Emilamar Demo",
  subdomain: "emilamar-demo",
  owner_email: "owner@emilamar.demo",
  owner_full_name: "Emilamar Owner",
  owner_password: "ownerpass123",
  branding_config: { primary_color: "#C9A227" },
  integration_config: {
    integrations: [
      {
        id: "airbnb",
        name: "Airbnb API",
        description: "Sincronizacion de reservas, disponibilidad y precios",
        status: "connected",
        icon: "🏠",
        color: "#FF5A5F",
        last_sync: "Hace 5 min",
        details: "12 propiedades sincronizadas",
      },
      {
        id: "booking",
        name: "Booking.com API",
        description: "Canal de reservas y gestion de tarifas",
        status: "connected",
        icon: "🔵",
        color: "#003580",
        last_sync: "Hace 12 min",
        details: "10 propiedades sincronizadas",
      },
      {
        id: "channel",
        name: "Channel Manager",
        description: "Distribucion centralizada en multiples canales OTA",
        status: "pending",
        icon: "📡",
        color: "#F59E0B",
        details: "Configuracion en progreso",
      },
      {
        id: "stripe",
        name: "Stripe Payments",
        description: "Pasarela de pagos para reservas directas",
        status: "connected",
        icon: "💳",
        color: "#635BFF",
        last_sync: "Hace 1 min",
        details: "EUR 12,400 procesados este mes",
      },
      {
        id: "google",
        name: "Google Calendar",
        description: "Sincronizacion de calendario con Google",
        status: "error",
        icon: "📅",
        color: "#4285F4",
        details: "Error de autenticacion - Token expirado",
      },
      {
        id: "mailchimp",
        name: "Mailchimp",
        description: "Marketing por email para huespedes recurrentes",
        status: "pending",
        icon: "📧",
        color: "#FFE01B",
        details: "Pendiente de activacion",
      },
    ],
  },
} as const;

const DEMO_AMENITIES = [
  { name: "WiFi", icon_key: "wifi" },
  { name: "Piscina", icon_key: "pool" },
  { name: "Aire Acondicionado", icon_key: "ac" },
  { name: "Parqueadero", icon_key: "parking" },
] as const;

const DEMO_PROPERTIES = [
  {
    name: "Beach House",
    address: "Isla de Tierra Bomba, 3er piso, Cartagena",
    capacity_adults: 4,
    capacity_kids: 2,
    base_price: "420000.00",
    cleaning_fee: "120000.00",
    amenities: ["WiFi", "Piscina", "Aire Acondicionado"],
  },
  {
    name: "Beach Town",
    address: "Isla de Tierra Bomba, 2do piso, Cartagena",
    capacity_adults: 6,
    capacity_kids: 2,
    base_price: "520000.00",
    cleaning_fee: "140000.00",
    amenities: ["WiFi", "Piscina"],
  },
  {
    name: "Beach Dúplex",
    address: "Isla de Tierra Bomba, 7mo y 8vo piso, Cartagena",
    capacity_adults: 8,
    capacity_kids: 2,
    base_price: "680000.00",
    cleaning_fee: "180000.00",
    amenities: ["WiFi", "Piscina", "Aire Acondicionado", "Parqueadero"],
  },
  {
    name: "Santo Domingo",
    address: "Centro Historico, Ciudad Amurallada, Cartagena",
    capacity_adults: 4,
    capacity_kids: 2,
    base_price: "390000.00",
    cleaning_fee: "110000.00",
    amenities: ["WiFi", "Aire Acondicionado"],
  },
] as const;

const DEMO_CONTACTS = [
  { name: "Maria Garcia", email: "maria@example.com", phone: "+573001112233", type: "GUEST", commission_rate: "0.00" },
  { name: "John Smith", email: "john@example.com", phone: "+573002224466", type: "GUEST", commission_rate: "0.00" },
  { name: "Pierre Dupont", email: "pierre@example.com", phone: "+573003336699", type: "GUEST", commission_rate: "0.00" },
  { name: "Anna Muller", email: "anna@example.com", phone: "+573004448822", type: "GUEST", commission_rate: "0.00" },
  { name: "Carlos Lopez", email: "carlos@example.com", phone: "+573005551144", type: "GUEST", commission_rate: "0.00" },
  { name: "Elena Rossi", email: "elena@example.com", phone: "+573006663355", type: "GUEST", commission_rate: "0.00" },
  { name: "Sofia Martinez", email: "sofia@example.com", phone: "+573007775577", type: "GUEST", commission_rate: "0.00" },
  { name: "Laura Chen", email: "laura@example.com", phone: "+573008887799", type: "GUEST", commission_rate: "0.00" },
  { name: "Mateo Ruiz", email: "mateo@example.com", phone: "+573009990011", type: "GUEST", commission_rate: "0.00" },
  { name: "Isabella Torres", email: "isabella@example.com", phone: "+573000123456", type: "GUEST", commission_rate: "0.00" },
  { name: "Thomas Meyer", email: "thomas@example.com", phone: "+573000654321", type: "GUEST", commission_rate: "0.00" },
  { name: "Gabriela Silva", email: "gabriela@example.com", phone: "+573000778899", type: "GUEST", commission_rate: "0.00" },
  { name: "Daniel Rivera", email: "daniel.agent@example.com", phone: "+573000445566", type: "AGENT", commission_rate: "10.00" },
] as const;

function buildDemoReservations(year: number) {
  return [
    { property: "Santo Domingo", guest: "John Smith", check_in: `${year}-01-10`, check_out: `${year}-01-12`, status: "CONFIRMED" },
    { property: "Beach House", guest: "Maria Garcia", check_in: `${year}-02-03`, check_out: `${year}-02-07`, status: "CONFIRMED" },
    { property: "Beach Town", guest: "Pierre Dupont", check_in: `${year}-02-08`, check_out: `${year}-02-14`, status: "CONFIRMED" },
    { property: "Beach Dúplex", guest: "Anna Muller", check_in: `${year}-02-15`, check_out: `${year}-02-20`, status: "CONFIRMED" },
    { property: "Santo Domingo", guest: "Carlos Lopez", check_in: `${year}-02-21`, check_out: `${year}-02-24`, status: "DRAFT" },
    { property: "Beach House", guest: "Elena Rossi", check_in: `${year}-03-05`, check_out: `${year}-03-09`, status: "CONFIRMED", agent: "Daniel Rivera" },
    { property: "Beach Town", guest: "Sofia Martinez", check_in: `${year}-04-12`, check_out: `${year}-04-16`, status: "CONFIRMED" },
    { property: "Beach Dúplex", guest: "Laura Chen", check_in: `${year}-05-18`, check_out: `${year}-05-22`, status: "CONFIRMED", agent: "Daniel Rivera" },
    { property: "Santo Domingo", guest: "Mateo Ruiz", check_in: `${year}-06-08`, check_out: `${year}-06-11`, status: "CONFIRMED" },
    { property: "Beach House", guest: "Isabella Torres", check_in: `${year}-07-14`, check_out: `${year}-07-18`, status: "CONFIRMED" },
    { property: "Beach Town", guest: "Thomas Meyer", check_in: `${year}-08-03`, check_out: `${year}-08-08`, status: "CONFIRMED" },
    { property: "Beach Dúplex", guest: "Gabriela Silva", check_in: `${year}-09-10`, check_out: `${year}-09-13`, status: "CONFIRMED" },
    { property: "Santo Domingo", guest: "Maria Garcia", check_in: `${year}-10-21`, check_out: `${year}-10-25`, status: "CONFIRMED" },
    { property: "Beach House", guest: "John Smith", check_in: `${year}-11-07`, check_out: `${year}-11-10`, status: "CONFIRMED" },
    { property: "Beach Town", guest: "Pierre Dupont", check_in: `${year}-12-15`, check_out: `${year}-12-20`, status: "CONFIRMED" },
  ] as const;
}

const DEMO_RESERVATIONS = buildDemoReservations(new Date().getFullYear());

export const SHORT_MONTH_LABELS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"] as const;
export const LONG_MONTH_LABELS = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"] as const;

export type DemoSession = {
  access: string;
  refresh: string;
  tenantId: string;
};

export type PropertyApi = {
  id: string;
  name: string;
  address: string;
  capacity_adults: number;
  capacity_kids: number;
  base_price: string;
  cleaning_fee: string;
  monthly_revenue: string;
  occupancy_rate: number;
};

export type Property = PropertyApi;

export type PropertyCreatePayload = {
  name: string;
  address: string;
  capacity_adults: number;
  capacity_kids: number;
  base_price: string;
  cleaning_fee: string;
  amenity_ids?: string[];
};

export type ReservationApi = {
  id: string;
  property: string;
  property_name: string;
  guest: string;
  guest_name: string;
  agent: string | null;
  check_in: string;
  check_out: string;
  total_amount: string;
  status: "DRAFT" | "CONFIRMED" | "CHECKED_IN" | "CHECKED_OUT" | "CANCELLED";
  payment_status?: string;
  amount_paid?: string;
  balance_due?: string;
  extras_received?: string;
};

export type Reservation = ReservationApi;

export type FinanceAnalyticsApi = {
  monthly_revenue_total: string;
  annual_revenue_total: string;
  monthly_revenue_series: Array<{ month_index: number; month: string; ingresos: string }>;
  revenue_by_property: Array<{ property_id: string; name: string; ingresos: string }>;
};

export type IntegrationApi = {
  id: string;
  name: string;
  description: string;
  status: "connected" | "pending" | "error";
  icon: string;
  color: string;
  last_sync?: string | null;
  details?: string | null;
};

export type ModuleKey = "core" | "users" | "inventory" | "crm" | "booking" | "finance";
export type PermissionLevel = "none" | "read" | "write" | "admin";

export type CurrentUserResponse = {
  user: {
    id: string;
    email: string;
    full_name: string;
    system_role: string;
    is_active: boolean;
    is_primary_owner: boolean;
    role: { id: string; name: string } | null;
    date_joined: string;
  };
  tenant: TenantSummary | null;
  permissions: Partial<Record<ModuleKey, PermissionLevel>>;
};

export type RegisterInput = {
  invitation_code: string;
  email: string;
  full_name: string;
  password: string;
  tenant_name?: string;
  tenant_subdomain?: string;
  tenant_subdomain_join?: string;
};

export type Contact = {
  id: string;
  name: string;
  email: string;
  phone: string;
  type: "GUEST" | "AGENT" | "PLATFORM";
  commission_rate: string;
  tax_id?: string;
  address?: string;
  nationality?: string;
  notes?: string;
  created_at?: string;
  updated_at?: string;
};

export type ContactStats = {
  contact_id: string;
  reservations_count: number;
  confirmed_reservations_count: number;
  cancelled_reservations_count: number;
  total_billed: string;
  total_lodging_paid: string;
  total_extras_paid: string;
  total_refunded: string;
  outstanding_balance: string;
  first_check_in: string | null;
  last_check_out: string | null;
  nights_total: number;
};

export type QuoteResult = {
  property_id: string;
  check_in: string;
  check_out: string;
  nights: number;
  nightly_rate: string;
  subtotal_amount: string;
  cleaning_fee: string;
  total_amount: string;
  nights_breakdown?: unknown[];
  applied_rule_names?: string[];
  min_nights_required?: number;
};

export type PaymentTypeValue = "ADVANCE" | "BALANCE" | "EXTRA" | "REFUND";

export type PaymentItem = {
  id: string;
  reservation: string;
  reservation_label: string;
  date: string;
  amount: string;
  type: PaymentTypeValue;
  is_lodging: boolean;
  method: "CASH" | "TRANSFER" | "OTHER";
  reference: string;
  notes: string;
  recorded_by?: string | null;
  created_at?: string;
};

export type CostCenter = {
  id: string;
  name: string;
  property: string | null;
  property_name?: string | null;
  is_active: boolean;
  balance: string;
};

export type ExpenseCategory =
  | "CLEANING_COST"
  | "MAINTENANCE"
  | "UTILITIES"
  | "COMMISSION"
  | "OTHER_EXPENSE";

export type AnalyticLineItem = {
  id: string;
  account: string;
  account_name: string;
  date: string;
  amount: string;
  category: string;
  description: string;
  reference_type?: string;
  reference_id?: string | null;
  created_at?: string;
};

export type ProfitAndLoss = {
  income: string;
  expenses: string;
  net: string;
  by_category: Record<string, string>;
};

export type TaskStatus = "PENDING" | "IN_PROGRESS" | "DONE" | "CANCELLED";
export type TaskType = "CLEANING" | "MAINTENANCE" | "INSPECTION" | "OTHER";

export type OpsTask = {
  id: string;
  property: string | null;
  property_name?: string | null;
  reservation?: string | null;
  type: TaskType;
  title: string;
  notes: string;
  due_date: string;
  assigned_to?: string | null;
  assigned_to_name?: string | null;
  status: TaskStatus;
  completed_at?: string | null;
  created_at?: string;
};

export type MessageChannel = "EMAIL" | "WHATSAPP" | "INTERNAL";

export type MessageTemplate = {
  id: string;
  name: string;
  channel: MessageChannel;
  subject: string;
  body: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
};

export type RenderedMessage = {
  channel: MessageChannel;
  subject: string;
  body: string;
};

export type InvitationCode = {
  id: string;
  code: string;
  purpose: string;
  tenant_subdomain?: string;
  role?: { id: string; name: string } | null;
  max_uses: number;
  uses_count: number;
  expires_at?: string | null;
  is_active: boolean;
  is_usable: boolean;
  is_expired: boolean;
  is_exhausted: boolean;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type TenantUser = CurrentUserResponse["user"];

export type GoogleCredentialResponse = {
  configured?: boolean;
  message?: string;
  id?: string;
  calendar_id?: string;
  is_active?: boolean;
  has_refresh_token?: boolean;
  last_sync_at?: string | null;
  last_sync_status?: string;
  last_sync_error?: string;
};

export type TenantSummary = {
  id: string;
  name: string;
  subdomain: string;
};

type AmenityApi = {
  id: string;
  name: string;
};

type ContactApi = {
  id: string;
  name: string;
  email: string;
  type: "GUEST" | "AGENT" | "PLATFORM";
};

type TokenResponse = {
  access: string;
  refresh: string;
};

type RawRequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

const PERMISSION_RANK: Record<PermissionLevel, number> = {
  none: 0,
  read: 1,
  write: 2,
  admin: 3,
};

export function isAuthenticated() {
  return Boolean(getAccessToken() && getCurrentUser());
}

export async function login(email: string, password: string) {
  const session = await authLogin(email, password);
  clearStoredSession();
  return session;
}

export function logout() {
  clearStoredSession();
  void authLogout();
}

export async function register(input: RegisterInput) {
  const response = await rawRequest<CurrentUserResponse & { access: string; refresh: string }>(
    "/api/auth/register/",
    {
      method: "POST",
      body: input,
    },
  );
  await authLogin(input.email, input.password);
  clearStoredSession();
  return response;
}

export async function fetchCurrentUser(): Promise<CurrentUserResponse> {
  const response = await authenticatedFetch("/api/me/");
  const payload = await parseResponseBody(response);

  if (!response.ok) {
    throw new ApiError("No fue posible cargar el usuario actual.", response.status, payload);
  }

  return payload as CurrentUserResponse;
}

export function hasPermission(
  permissions: Partial<Record<ModuleKey, PermissionLevel>> | undefined,
  module: ModuleKey,
  required: PermissionLevel = "read",
) {
  const granted = permissions?.[module] ?? "none";
  return PERMISSION_RANK[granted] >= PERMISSION_RANK[required];
}

let cachedSession: DemoSession | null = null;
let sessionPromise: Promise<DemoSession> | null = null;
let refreshPromise: Promise<DemoSession> | null = null;
let seedPromise: Promise<void> | null = null;
let seededTenantId: string | null = null;

function getStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
}

function readStoredSession(): DemoSession | null {
  if (cachedSession) {
    return cachedSession;
  }

  const storage = getStorage();
  const rawValue = storage?.getItem(SESSION_STORAGE_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawValue) as DemoSession;
    if (parsed.access && parsed.refresh && parsed.tenantId) {
      cachedSession = parsed;
      return parsed;
    }
  } catch {
    storage?.removeItem(SESSION_STORAGE_KEY);
  }

  return null;
}

function readAuthenticatedSession(): DemoSession | null {
  const user = getCurrentUser();
  const access = getAccessToken();
  const refresh = getRefreshToken();

  if (!user?.tenant_id || !access || !refresh) {
    return null;
  }

  return {
    access,
    refresh,
    tenantId: user.tenant_id,
  };
}

function storeSession(session: DemoSession) {
  cachedSession = session;
  getStorage()?.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
}

function clearStoredSession() {
  cachedSession = null;
  getStorage()?.removeItem(SESSION_STORAGE_KEY);
}

function formatDateForApi(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

async function parseResponseBody(response: Response) {
  if (response.status === 204) {
    return null;
  }

  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function rawRequest<T>(path: string, options: RawRequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const body =
    options.body === undefined
      ? undefined
      : typeof options.body === "string"
        ? options.body
        : JSON.stringify(options.body);

  if (body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    body,
  });
  const payload = await parseResponseBody(response);

  if (!response.ok) {
    const message =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? String((payload as { detail: string }).detail)
        : `La peticion a ${path} fallo con estado ${response.status}.`;
    throw new ApiError(message, response.status, payload);
  }

  return payload as T;
}

async function fetchTenants(accessToken: string): Promise<TenantSummary[]> {
  return rawRequest<TenantSummary[]>("/api/tenants/", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

async function resolveSession(access: string, refresh: string, tenantId?: string) {
  const tenants = await fetchTenants(access);
  const resolvedTenantId = tenantId ?? tenants[0]?.id;

  if (!resolvedTenantId) {
    throw new Error("No se encontro un tenant asociado al usuario demo.");
  }

  const session = { access, refresh, tenantId: resolvedTenantId };
  storeSession(session);
  return session;
}

async function loginDemoOwner() {
  const response = await rawRequest<TokenResponse>("/api/auth/token/", {
    method: "POST",
    body: {
      email: DEMO_TENANT.owner_email,
      password: DEMO_TENANT.owner_password,
    },
  });
  return resolveSession(response.access, response.refresh);
}

async function createDemoTenant() {
  try {
    await rawRequest("/api/tenants/", {
      method: "POST",
      body: DEMO_TENANT,
    });
  } catch (error) {
    if (error instanceof ApiError && error.status === 400) {
      return;
    }
    throw error;
  }
}

async function refreshSession(session: DemoSession): Promise<DemoSession> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const authenticatedSession = readAuthenticatedSession();

      if (
        authenticatedSession &&
        authenticatedSession.refresh === session.refresh &&
        authenticatedSession.tenantId === session.tenantId
      ) {
        const access = await refreshAuthToken();
        return { ...authenticatedSession, access };
      }

      const response = await rawRequest<{ access: string }>("/api/auth/token/refresh/", {
        method: "POST",
        body: { refresh: session.refresh },
      });
      return resolveSession(response.access, session.refresh, session.tenantId);
    })().finally(() => {
      refreshPromise = null;
    });
  }

  return refreshPromise;
}

async function requestWithSession<T>(
  path: string,
  session: DemoSession,
  options: RawRequestOptions = {},
  allowRefresh = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${session.access}`);
  headers.set("X-Tenant-ID", session.tenantId);

  try {
    return await rawRequest<T>(path, {
      ...options,
      headers,
    });
  } catch (error) {
    if (allowRefresh && error instanceof ApiError && error.status === 401) {
      const refreshed = await refreshSession(session);
      return requestWithSession(path, refreshed, options, false);
    }
    throw error;
  }
}

async function ensureSeedData(session: DemoSession) {
  if (seededTenantId === session.tenantId) {
    return;
  }

  if (!seedPromise) {
    seedPromise = (async () => {
      const amenities = await requestWithSession<AmenityApi[]>(
        `/api/tenants/${session.tenantId}/inventory/amenities/`,
        session,
      );
      const amenityIdsByName = new Map(amenities.map((amenity) => [amenity.name, amenity.id]));

      for (const amenity of DEMO_AMENITIES) {
        if (!amenityIdsByName.has(amenity.name)) {
          const createdAmenity = await requestWithSession<AmenityApi>(
            `/api/tenants/${session.tenantId}/inventory/amenities/`,
            session,
            {
              method: "POST",
              body: amenity,
            },
          );
          amenityIdsByName.set(createdAmenity.name, createdAmenity.id);
        }
      }

      const properties = await requestWithSession<PropertyApi[]>(
        `/api/tenants/${session.tenantId}/inventory/properties/`,
        session,
      );
      const propertyIdsByName = new Map(properties.map((property) => [property.name, property.id]));

      for (const property of DEMO_PROPERTIES) {
        if (!propertyIdsByName.has(property.name)) {
          const createdProperty = await requestWithSession<PropertyApi>(
            `/api/tenants/${session.tenantId}/inventory/properties/`,
            session,
            {
              method: "POST",
              body: {
                ...property,
                amenity_ids: property.amenities
                  .map((amenityName) => amenityIdsByName.get(amenityName))
                  .filter(Boolean),
              },
            },
          );
          propertyIdsByName.set(createdProperty.name, createdProperty.id);
        }
      }

      const contacts = await requestWithSession<ContactApi[]>(
        `/api/tenants/${session.tenantId}/crm/contacts/`,
        session,
      );
      const contactIdsByName = new Map(contacts.map((contact) => [contact.name, contact.id]));

      for (const contact of DEMO_CONTACTS) {
        if (!contactIdsByName.has(contact.name)) {
          const createdContact = await requestWithSession<ContactApi>(
            `/api/tenants/${session.tenantId}/crm/contacts/`,
            session,
            {
              method: "POST",
              body: contact,
            },
          );
          contactIdsByName.set(createdContact.name, createdContact.id);
        }
      }

      const reservations = await requestWithSession<ReservationApi[]>(
        `/api/tenants/${session.tenantId}/booking/reservations/`,
        session,
      );
      const reservationKeys = new Set(
        reservations.map(
          (reservation) => `${reservation.property_name}:${reservation.guest_name}:${reservation.check_in}`,
        ),
      );

      for (const reservation of DEMO_RESERVATIONS) {
        const propertyId = propertyIdsByName.get(reservation.property);
        const guestId = contactIdsByName.get(reservation.guest);

        if (!propertyId || !guestId) {
          continue;
        }

        const reservationKey = `${reservation.property}:${reservation.guest}:${reservation.check_in}`;
        if (reservationKeys.has(reservationKey)) {
          continue;
        }

        await requestWithSession(
          `/api/tenants/${session.tenantId}/booking/reservations/`,
          session,
          {
            method: "POST",
            body: {
              property_id: propertyId,
              guest_id: guestId,
              agent_id:
                "agent" in reservation && reservation.agent
                  ? contactIdsByName.get(reservation.agent) ?? null
                  : null,
              check_in: reservation.check_in,
              check_out: reservation.check_out,
              status: reservation.status,
            },
          },
        );
      }

      seededTenantId = session.tenantId;
    })().finally(() => {
      seedPromise = null;
    });
  }

  return seedPromise;
}

async function initializeSession(): Promise<DemoSession> {
  const storedSession = readStoredSession();

  if (storedSession) {
    try {
      const resolved = await resolveSession(
        storedSession.access,
        storedSession.refresh,
        storedSession.tenantId,
      );
      await ensureSeedData(resolved);
      return resolved;
    } catch {
      try {
        const refreshed = await refreshSession(storedSession);
        await ensureSeedData(refreshed);
        return refreshed;
      } catch {
        clearStoredSession();
      }
    }
  }

  try {
    const logged = await loginDemoOwner();
    await ensureSeedData(logged);
    return logged;
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) {
      throw error;
    }
  }

  await createDemoTenant();
  const created = await loginDemoOwner();
  await ensureSeedData(created);
  return created;
}

export async function ensureDemoSession(): Promise<DemoSession> {
  const authenticatedSession = readAuthenticatedSession();

  if (authenticatedSession) {
    cachedSession = authenticatedSession;
    return authenticatedSession;
  }

  if (cachedSession) {
    return cachedSession;
  }

  if (!sessionPromise) {
    sessionPromise = initializeSession().finally(() => {
      sessionPromise = null;
    });
  }

  const session = await sessionPromise;
  cachedSession = session;
  return session;
}

export async function apiRequest<T>(path: string, options: RawRequestOptions = {}): Promise<T> {
  const session = await ensureDemoSession();
  return requestWithSession(path, session, options);
}

export async function fetchProperties(params?: { year: number; month: number }): Promise<PropertyApi[]> {
  const session = await ensureDemoSession();
  const query = params ? `?year=${params.year}&month=${params.month}` : "";
  return requestWithSession<PropertyApi[]>(
    `/api/tenants/${session.tenantId}/inventory/properties/${query}`,
    session,
  );
}

export async function createProperty(payload: PropertyCreatePayload): Promise<PropertyApi> {
  const session = await ensureDemoSession();
  return requestWithSession<PropertyApi>(
    `/api/tenants/${session.tenantId}/inventory/properties/`,
    session,
    {
      method: "POST",
      body: payload,
    },
  );
}

export async function fetchReservations(params: { from: string; to: string }): Promise<ReservationApi[]> {
  const session = await ensureDemoSession();
  return requestWithSession<ReservationApi[]>(
    `/api/tenants/${session.tenantId}/booking/reservations/?from=${params.from}&to=${params.to}`,
    session,
  );
}

export async function fetchFinanceAnalytics(params: { year: number; month: number }): Promise<FinanceAnalyticsApi> {
  const session = await ensureDemoSession();
  return requestWithSession<FinanceAnalyticsApi>(
    `/api/tenants/${session.tenantId}/finance/analytics/?year=${params.year}&month=${params.month}`,
    session,
  );
}


export async function fetchIntegrations(): Promise<IntegrationApi[]> {
  const session = await ensureDemoSession();
  return requestWithSession<IntegrationApi[]>(
    `/api/tenants/${session.tenantId}/integrations/`,
    session,
  );
}

export async function startGoogleCalendarOAuth(): Promise<string> {
  const session = await ensureDemoSession();
  const { authorization_url } = await requestWithSession<{
    authorization_url: string;
  }>(
    `/api/tenants/${session.tenantId}/integrations/google-calendar/oauth-init/`,
    session,
  );
  return authorization_url;
}

export type GoogleCalendarSyncResult = {
  synced: number;
  failed: number;
  errors: Array<{ reservation_id: string; error: string }>;
  last_sync_at: string | null;
  last_sync_status: "pending" | "connected" | "error";
};

export async function syncGoogleCalendarNow(): Promise<GoogleCalendarSyncResult> {
  const session = await ensureDemoSession();
  return requestWithSession<GoogleCalendarSyncResult>(
    `/api/tenants/${session.tenantId}/integrations/google-calendar/sync-now/`,
    session,
    { method: "POST" },
  );
}

export type ICalFeedApi = {
  id: string;
  property: string;
  property_name: string;
  label: string;
  ical_url: string;
  is_active: boolean;
  last_synced_at: string | null;
  last_sync_status: "never" | "ok" | "error";
  last_sync_error: string;
  created_at: string;
  updated_at: string;
};

export type ICalFeedCreatePayload = {
  property: string;
  label: string;
  ical_url: string;
  is_active?: boolean;
};

export async function fetchICalFeeds(): Promise<ICalFeedApi[]> {
  const session = await ensureDemoSession();
  return requestWithSession<ICalFeedApi[]>(
    `/api/tenants/${session.tenantId}/channels/ical-feeds/`,
    session,
  );
}

export async function createICalFeed(
  payload: ICalFeedCreatePayload,
): Promise<ICalFeedApi> {
  const session = await ensureDemoSession();
  return requestWithSession<ICalFeedApi>(
    `/api/tenants/${session.tenantId}/channels/ical-feeds/`,
    session,
    { method: "POST", body: payload },
  );
}

export async function deleteICalFeed(feedId: string): Promise<void> {
  const session = await ensureDemoSession();
  await requestWithSession<void>(
    `/api/tenants/${session.tenantId}/channels/ical-feeds/${feedId}/`,
    session,
    { method: "DELETE" },
  );
}

export type ICalFeedSyncResult = {
  feed_id: string;
  created: number;
  skipped: number;
  errors: string[];
  last_sync_status: "never" | "ok" | "error";
  last_synced_at: string | null;
};

export async function syncICalFeedNow(feedId: string): Promise<ICalFeedSyncResult> {
  const session = await ensureDemoSession();
  return requestWithSession<ICalFeedSyncResult>(
    `/api/tenants/${session.tenantId}/channels/ical-feeds/${feedId}/sync-now/`,
    session,
    { method: "POST" },
  );
}

export type ICalSyncAllResult = {
  feeds: number;
  created: number;
  skipped: number;
  errors: number;
  details: Array<{
    feed_id: string;
    label: string;
    property: string;
    created: number;
    skipped: number;
    errors: string[];
    status: string;
  }>;
};

export async function syncAllICalFeeds(): Promise<ICalSyncAllResult> {
  const session = await ensureDemoSession();
  return requestWithSession<ICalSyncAllResult>(
    `/api/tenants/${session.tenantId}/channels/ical-feeds/sync-all/`,
    session,
    { method: "POST" },
  );
}

function compactQuery(params: Record<string, unknown> = {}) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

async function tenantRequest<T>(path: string, options: RawRequestOptions = {}) {
  const session = await ensureDemoSession();
  return requestWithSession<T>(`/api/tenants/${session.tenantId}${path}`, session, options);
}

export async function fetchContacts(params: { search?: string } = {}) {
  return tenantRequest<Contact[]>(`/crm/contacts/${compactQuery(params)}`);
}

export async function fetchContactStats(contactId: string) {
  return tenantRequest<ContactStats>(`/crm/contacts/${contactId}/stats/`);
}

export async function createContact(input: Partial<Contact>) {
  return tenantRequest<Contact>("/crm/contacts/", {
    method: "POST",
    body: input,
  });
}

export async function updateContact(contactId: string, input: Partial<Contact>) {
  return tenantRequest<Contact>(`/crm/contacts/${contactId}/`, {
    method: "PATCH",
    body: input,
  });
}

export async function deleteContact(contactId: string) {
  return tenantRequest<void>(`/crm/contacts/${contactId}/`, { method: "DELETE" });
}

export async function deleteProperty(propertyId: string) {
  return tenantRequest<void>(`/inventory/properties/${propertyId}/`, {
    method: "DELETE",
  });
}

export async function quoteReservation(input: {
  property_id: string;
  check_in: string;
  check_out: string;
}) {
  return tenantRequest<QuoteResult>("/booking/quote/", {
    method: "POST",
    body: input,
  });
}

export async function checkAvailability(input: {
  property_id: string;
  check_in: string;
  check_out: string;
}) {
  return tenantRequest<{ available: boolean; conflicting_reservation_ids: string[] }>(
    "/booking/reservations/availability/",
    {
      method: "POST",
      body: input,
    },
  );
}

export async function createReservation(input: {
  property_id: string;
  guest_id: string;
  agent_id?: string | null;
  check_in: string;
  check_out: string;
  status?: string;
}) {
  return tenantRequest<Reservation>("/booking/reservations/", {
    method: "POST",
    body: input,
  });
}

export async function fetchPayments(params: Record<string, unknown> = {}) {
  return tenantRequest<PaymentItem[]>(`/finance/payments/${compactQuery(params)}`);
}

export async function createPayment(input: {
  reservation_id: string;
  date: string;
  amount: string;
  type: PaymentTypeValue;
  method: PaymentItem["method"];
  reference?: string;
  notes?: string;
}) {
  return tenantRequest<PaymentItem>("/finance/payments/", {
    method: "POST",
    body: input,
  });
}

export async function deletePayment(paymentId: string) {
  return tenantRequest<void>(`/finance/payments/${paymentId}/`, { method: "DELETE" });
}

export async function fetchCostCenters() {
  return tenantRequest<CostCenter[]>("/finance/cost-centers/");
}

export async function createCostCenter(input: { name: string; property?: string | null }) {
  return tenantRequest<CostCenter>("/finance/cost-centers/", {
    method: "POST",
    body: input,
  });
}

export async function fetchProfitAndLoss(params: {
  account_id?: string;
  from_date?: string;
  to_date?: string;
}) {
  return tenantRequest<ProfitAndLoss>(`/finance/profit-and-loss/${compactQuery(params)}`);
}

export async function fetchAnalyticLines(params: Record<string, unknown> = {}) {
  return tenantRequest<AnalyticLineItem[]>(
    `/finance/analytic-lines/${compactQuery(params)}`,
  );
}

export async function createExpense(input: {
  account_id: string;
  date: string;
  amount: string;
  category: ExpenseCategory;
  description?: string;
}) {
  return tenantRequest<AnalyticLineItem>("/finance/expenses/", {
    method: "POST",
    body: input,
  });
}

export async function fetchTasks(params: Record<string, unknown> = {}) {
  return tenantRequest<OpsTask[]>(`/ops/tasks/${compactQuery(params)}`);
}

export async function createTask(input: Partial<OpsTask>) {
  return tenantRequest<OpsTask>("/ops/tasks/", {
    method: "POST",
    body: input,
  });
}

export async function updateTask(taskId: string, input: Partial<OpsTask>) {
  return tenantRequest<OpsTask>(`/ops/tasks/${taskId}/`, {
    method: "PATCH",
    body: input,
  });
}

export async function completeTask(taskId: string) {
  return tenantRequest<OpsTask>(`/ops/tasks/${taskId}/complete/`, {
    method: "POST",
  });
}

export async function fetchMessageTemplates() {
  return tenantRequest<MessageTemplate[]>("/ops/templates/");
}

export async function createMessageTemplate(input: {
  name: string;
  channel: MessageChannel;
  subject?: string;
  body: string;
}) {
  return tenantRequest<MessageTemplate>("/ops/templates/", {
    method: "POST",
    body: input,
  });
}

export async function deleteMessageTemplate(templateId: string) {
  return tenantRequest<void>(`/ops/templates/${templateId}/`, { method: "DELETE" });
}

export async function renderMessage(templateId: string, reservationId: string) {
  return tenantRequest<RenderedMessage>("/ops/render-message/", {
    method: "POST",
    body: { template_id: templateId, reservation_id: reservationId },
  });
}

export async function fetchTenantUsers() {
  const current = await fetchCurrentUser();
  if (!current.tenant?.id) {
    return [];
  }
  return tenantRequest<TenantUser[]>("/users/");
}

export async function fetchInvitationCodes() {
  return tenantRequest<InvitationCode[]>("/invitation-codes/");
}

export async function createInvitationCode(input: {
  max_uses?: number;
  expires_at?: string | null;
  notes?: string;
  role_id?: string | null;
}) {
  return tenantRequest<InvitationCode>("/invitation-codes/", {
    method: "POST",
    body: input,
  });
}

export async function deactivateInvitationCode(codeId: string) {
  return tenantRequest<void>(`/invitation-codes/${codeId}/`, { method: "DELETE" });
}


export function shiftMonth(year: number, month: number, delta: number) {
  const shifted = new Date(year, month - 1 + delta, 1);
  return {
    year: shifted.getFullYear(),
    month: shifted.getMonth() + 1,
  };
}

export function toNumber(value: number | string) {
  return typeof value === "number" ? value : Number(value);
}

export function getMonthDateRange(year: number, month: number) {
  const start = new Date(year, month - 1, 1);
  const end = new Date(year, month, 1);
  return {
    start,
    end,
    startIso: formatDateForApi(start),
    endIso: formatDateForApi(end),
  };
}

async function requestBlobWithSession(
  path: string,
  session: DemoSession,
  allowRefresh = true,
): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Authorization: `Bearer ${session.access}`,
      "X-Tenant-ID": session.tenantId,
    },
  });

  if (allowRefresh && response.status === 401) {
    const refreshed = await refreshSession(session);
    return requestBlobWithSession(path, refreshed, false);
  }

  if (!response.ok) {
    const payload = await parseResponseBody(response);
    throw new ApiError("No fue posible descargar el archivo.", response.status, payload);
  }

  return response.blob();
}

function triggerDownload(blob: Blob, filename: string) {
  if (typeof window === "undefined") {
    return;
  }

  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export async function downloadReservationVoucher(
  _tenantId: string,
  reservationId: string,
) {
  const session = await ensureDemoSession();
  const blob = await requestBlobWithSession(
    `/api/tenants/${session.tenantId}/booking/reservations/${reservationId}/voucher-pdf/`,
    session,
  );
  triggerDownload(blob, `voucher-${reservationId}.pdf`);
}

export async function downloadPropertyReport(_tenantId: string, reportId: string) {
  const session = await ensureDemoSession();
  const blob = await requestBlobWithSession(
    `/api/tenants/${session.tenantId}/finance/profitability/${reportId}/download/`,
    session,
  );
  triggerDownload(blob, `report-${reportId}.pdf`);
}

export async function downloadPaymentsXlsx() {
  const session = await ensureDemoSession();
  const blob = await requestBlobWithSession(
    `/api/tenants/${session.tenantId}/finance/reports/payments.xlsx`,
    session,
  );
  triggerDownload(blob, "payments.xlsx");
}

export async function downloadPnLXlsx(year: number) {
  const session = await ensureDemoSession();
  const blob = await requestBlobWithSession(
    `/api/tenants/${session.tenantId}/finance/reports/pnl.xlsx?year=${year}`,
    session,
  );
  triggerDownload(blob, `pnl-${year}.xlsx`);
}

export async function downloadOccupancyXlsx(year: number) {
  const session = await ensureDemoSession();
  const blob = await requestBlobWithSession(
    `/api/tenants/${session.tenantId}/finance/reports/occupancy.xlsx?year=${year}`,
    session,
  );
  triggerDownload(blob, `occupancy-${year}.xlsx`);
}

export async function downloadVoucherPdf(reservationId: string) {
  const session = await ensureDemoSession();
  const blob = await requestBlobWithSession(
    `/api/tenants/${session.tenantId}/ops/voucher/${reservationId}.pdf`,
    session,
  );
  triggerDownload(blob, `voucher-${reservationId}.pdf`);
}

"use client";

import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/app-shell";
import { ErrorCard, LoadingCard } from "@/components/page-feedback";
import { useAsyncData } from "@/hooks/use-async-data";
import { useAuth } from "@/components/auth-provider";
import {
  GoogleCredentialResponse,
  fetchGoogleCalendarCredential,
  fetchIntegrations,
  saveGoogleCalendarCredential,
  type IntegrationApi,
} from "@/lib/api";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Calendar,
  Check,
  Clock,
  ExternalLink,
  KeyRound,
  Loader2,
  Save,
  ShieldAlert,
} from "lucide-react";

const statusConfig = {
  connected: {
    label: "Conectado",
    icon: Check,
    bgClass: "bg-emerald-500/10",
    textClass: "text-emerald-400",
    dotClass: "bg-emerald-500",
  },
  pending: {
    label: "Pendiente",
    icon: Clock,
    bgClass: "bg-yellow-500/10",
    textClass: "text-yellow-400",
    dotClass: "bg-yellow-500",
  },
  error: {
    label: "Error",
    icon: AlertTriangle,
    bgClass: "bg-red-500/10",
    textClass: "text-red-400",
    dotClass: "bg-red-500",
  },
} as const;

export default function IntegracionesPage() {
  const { can } = useAuth();
  const canManage = can("users", "admin");
  const integrations = useAsyncData<IntegrationApi[]>(fetchIntegrations, []);

  return (
    <AppShell>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        <div className="mb-6">
          <h1 className="font-serif text-3xl font-semibold text-gold-gradient">
            Integraciones
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Conexiones externas configuradas para tu empresa.
          </p>
        </div>

        {canManage && <GoogleCalendarPanel />}

        {integrations.loading ? (
          <LoadingCard message="Cargando integraciones…" />
        ) : integrations.error ? (
          <ErrorCard message={integrations.error} />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(integrations.data || []).map((it) => {
              const cfg = statusConfig[it.status];
              const Icon = cfg.icon;
              return (
                <div
                  key={it.id}
                  className="glass-card rounded-xl p-5 flex items-start gap-4"
                >
                  <span
                    className="flex items-center justify-center w-10 h-10 rounded-lg text-xl"
                    style={{ backgroundColor: `${it.color}20`, color: it.color }}
                  >
                    {it.icon}
                  </span>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h3 className="font-medium">{it.name}</h3>
                      <span
                        className={`text-xs flex items-center gap-1 px-2 py-0.5 rounded ${cfg.bgClass} ${cfg.textClass}`}
                      >
                        <Icon className="h-3 w-3" /> {cfg.label}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {it.description}
                    </p>
                    {it.details && (
                      <p className="text-xs text-muted-foreground mt-2 italic">
                        {it.details}
                      </p>
                    )}
                    {it.last_sync && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Última sincronización: {it.last_sync}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </motion.div>
    </AppShell>
  );
}

function GoogleCalendarPanel() {
  const [data, setData] = useState<GoogleCredentialResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [calendarId, setCalendarId] = useState("primary");
  const [refreshToken, setRefreshToken] = useState("");
  const [isActive, setIsActive] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const cred = await fetchGoogleCalendarCredential();
      setData(cred);
      if (cred?.calendar_id) setCalendarId(cred.calendar_id);
      if (typeof cred?.is_active === "boolean") setIsActive(cred.is_active);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error cargando credencial");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    setInfo("");
    try {
      await saveGoogleCalendarCredential({
        calendar_id: calendarId.trim() || "primary",
        is_active: isActive,
        refresh_token: refreshToken || undefined,
      });
      setRefreshToken("");
      setInfo("Credencial guardada. El token quedó cifrado en la BD.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error guardando credencial");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="glass-card rounded-xl p-6 mb-6 flex items-center gap-2 text-sm">
        <Loader2 className="h-4 w-4 animate-spin" /> Cargando Google Calendar…
      </div>
    );
  }

  return (
    <div className="glass-card rounded-xl p-6 mb-6">
      <div className="flex items-center gap-2 mb-3">
        <Calendar className="h-5 w-5 text-gold" />
        <h2 className="font-serif text-xl font-semibold">
          Configurar Google Calendar
        </h2>
      </div>
      <p className="text-xs text-muted-foreground mb-4">
        Pega aquí el <code className="font-mono">refresh_token</code> obtenido
        del flujo OAuth de Google (offline access). Se almacena cifrado con
        Fernet. El esquema de sincronización en sí se ejecutará cuando esté
        configurado el job (Sprint posterior).
      </p>

      {data?.has_refresh_token ? (
        <p className="text-xs text-emerald-300 mb-3 flex items-center gap-1">
          <Check className="h-3 w-3" /> Hay un refresh_token guardado.
          Reemplázalo escribiendo uno nuevo abajo.
        </p>
      ) : (
        <p className="text-xs text-yellow-300 mb-3 flex items-center gap-1">
          <ShieldAlert className="h-3 w-3" /> Aún no hay refresh_token.
        </p>
      )}

      {error && (
        <p className="text-xs text-red-400 bg-red-500/10 p-2 rounded mb-3">
          {error}
        </p>
      )}
      {info && (
        <p className="text-xs text-emerald-300 bg-emerald-500/10 p-2 rounded mb-3">
          {info}
        </p>
      )}

      <form
        onSubmit={handleSave}
        className="grid grid-cols-1 md:grid-cols-3 gap-3"
      >
        <input
          type="text"
          value={calendarId}
          onChange={(e) => setCalendarId(e.target.value)}
          className={inputClass}
          placeholder="calendar_id (default: primary)"
        />
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="h-4 w-4"
          />
          Sincronización activa
        </label>
        <a
          href="https://developers.google.com/identity/protocols/oauth2"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-200"
        >
          <ExternalLink className="h-3 w-3" /> Cómo obtener un refresh_token
        </a>
        <input
          type="password"
          value={refreshToken}
          onChange={(e) => setRefreshToken(e.target.value)}
          className={`${inputClass} md:col-span-3`}
          placeholder="Pega aquí el refresh_token"
          autoComplete="off"
        />
        <button
          type="submit"
          disabled={saving}
          className="md:col-span-3 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-gold text-zinc-900 font-medium hover:bg-gold/90 disabled:opacity-50"
        >
          {saving ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          Guardar credencial cifrada
        </button>
      </form>

      <details className="mt-4 text-xs text-muted-foreground">
        <summary className="cursor-pointer flex items-center gap-1">
          <KeyRound className="h-3 w-3" /> ¿Cómo funciona la seguridad?
        </summary>
        <p className="mt-2 leading-snug">
          El refresh_token se cifra con Fernet (AES-128 + HMAC) usando la
          variable de entorno <code className="font-mono">DJANGO_FERNET_KEY</code>.
          La API nunca devuelve el token en claro: sólo expone{" "}
          <code className="font-mono">has_refresh_token</code>. Ver
          <code className="font-mono"> documentacion/PRIVACY_AND_RBAC.md</code>.
        </p>
      </details>
    </div>
  );
}

const inputClass =
  "w-full px-3 py-2 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none";

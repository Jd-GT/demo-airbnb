"use client";

import AppShell from "@/components/app-shell";
import { ErrorCard, LoadingCard } from "@/components/page-feedback";
import { useAsyncData } from "@/hooks/use-async-data";
import {
  fetchIntegrations,
  startGoogleCalendarOAuth,
  syncGoogleCalendarNow,
  type IntegrationApi,
} from "@/lib/api";
import ICalFeedsSection from "./ical-feeds-section";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Check,
  Clock,
  ExternalLink,
  RefreshCw,
  Zap,
} from "lucide-react";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

type Integration = {
  id: string;
  name: string;
  description: string;
  status: "connected" | "pending" | "error";
  icon: string;
  color: string;
  lastSync?: string | null;
  details?: string | null;
};

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

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

function mapIntegration(integration: IntegrationApi): Integration {
  return {
    id: integration.id,
    name: integration.name,
    description: integration.description,
    status: integration.status,
    icon: integration.icon,
    color: integration.color,
    lastSync: integration.last_sync,
    details: integration.details,
  };
}

function IntegracionesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const googleParam = searchParams.get("google");
  const googleReason = searchParams.get("reason");

  const { data, error, loading, reload } = useAsyncData(
    async () => (await fetchIntegrations()).map(mapIntegration),
    [],
  );

  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [callbackBanner, setCallbackBanner] = useState<
    { kind: "success" | "error"; message: string } | null
  >(null);
  const [syncing, setSyncing] = useState(false);
  const [syncSummary, setSyncSummary] = useState<string | null>(null);

  useEffect(() => {
    if (!googleParam) return;
    if (googleParam === "connected") {
      setCallbackBanner({
        kind: "success",
        message: "Google Calendar conectado correctamente.",
      });
    } else if (googleParam === "error") {
      setCallbackBanner({
        kind: "error",
        message: googleReason
          ? `No se pudo conectar Google Calendar: ${googleReason}`
          : "No se pudo conectar Google Calendar.",
      });
    }
    router.replace("/integraciones", { scroll: false });
    reload?.();
  }, [googleParam, googleReason, router, reload]);

  const handleConnectGoogle = async () => {
    setConnecting(true);
    setConnectError(null);
    try {
      const url = await startGoogleCalendarOAuth();
      window.location.assign(url);
    } catch (err) {
      setConnectError(
        err instanceof Error ? err.message : "No se pudo iniciar la conexion.",
      );
      setConnecting(false);
    }
  };

  const handleSyncGoogle = async () => {
    setSyncing(true);
    setSyncSummary(null);
    try {
      const result = await syncGoogleCalendarNow();
      setSyncSummary(
        result.failed > 0
          ? `Sincronizadas ${result.synced} reservas, ${result.failed} fallidas.`
          : `Sincronizadas ${result.synced} reservas.`,
      );
      reload?.();
    } catch (err) {
      setSyncSummary(
        err instanceof Error ? `Error: ${err.message}` : "No se pudo sincronizar.",
      );
    } finally {
      setSyncing(false);
    }
  };

  const integrations = data ?? [];
  const connectedCount = integrations.filter(
    (integration) => integration.status === "connected",
  ).length;
  const pendingCount = integrations.filter(
    (integration) => integration.status === "pending",
  ).length;
  const errorCount = integrations.filter(
    (integration) => integration.status === "error",
  ).length;

  return (
    <AppShell>
      <motion.div variants={containerVariants} initial="hidden" animate="show">
        <motion.div
          variants={itemVariants}
          className="mb-8 flex items-center justify-between"
        >
          <div>
            <h1 className="font-serif text-3xl font-semibold text-gold-gradient">
              Integraciones
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Conexiones activas con plataformas y servicios
            </p>
          </div>
          <button className="flex items-center gap-2 rounded-lg border border-gold/20 bg-gold/10 px-4 py-2.5 text-sm font-medium text-gold transition-colors hover:bg-gold/20">
            <Zap className="h-4 w-4" />
            Nueva Integracion
          </button>
        </motion.div>

        {loading ? (
          <motion.div variants={itemVariants} className="mb-8">
            <LoadingCard
              title="Cargando integraciones"
              message="Consultando configuraciones activas desde el backend."
            />
          </motion.div>
        ) : null}

        {!loading && error ? (
          <motion.div variants={itemVariants} className="mb-8">
            <ErrorCard
              title="No fue posible cargar las integraciones"
              message={error}
            />
          </motion.div>
        ) : null}

        {callbackBanner ? (
          <motion.div variants={itemVariants} className="mb-6">
            <div
              className={`flex items-start gap-3 rounded-lg border p-4 text-sm ${
                callbackBanner.kind === "success"
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                  : "border-red-500/30 bg-red-500/10 text-red-300"
              }`}
            >
              {callbackBanner.kind === "success" ? (
                <Check className="mt-0.5 h-4 w-4" />
              ) : (
                <AlertTriangle className="mt-0.5 h-4 w-4" />
              )}
              <span>{callbackBanner.message}</span>
            </div>
          </motion.div>
        ) : null}

        {connectError ? (
          <motion.div variants={itemVariants} className="mb-6">
            <ErrorCard title="Error al iniciar OAuth de Google" message={connectError} />
          </motion.div>
        ) : null}

        {syncSummary ? (
          <motion.div variants={itemVariants} className="mb-6">
            <div className="flex items-start gap-3 rounded-lg border border-gold/20 bg-gold/10 p-4 text-sm text-gold">
              <RefreshCw className="mt-0.5 h-4 w-4" />
              <span>{syncSummary}</span>
            </div>
          </motion.div>
        ) : null}

        <motion.div variants={itemVariants} className="mb-8 grid grid-cols-3 gap-4">
          <div className="glass-card flex items-center gap-3 rounded-lg p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/10">
              <Check className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-xl font-semibold text-foreground">
                {connectedCount}
              </p>
              <p className="text-xs text-muted-foreground">Conectadas</p>
            </div>
          </div>

          <div className="glass-card flex items-center gap-3 rounded-lg p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-yellow-500/10">
              <Clock className="h-5 w-5 text-yellow-400" />
            </div>
            <div>
              <p className="text-xl font-semibold text-foreground">
                {pendingCount}
              </p>
              <p className="text-xs text-muted-foreground">Pendientes</p>
            </div>
          </div>

          <div className="glass-card flex items-center gap-3 rounded-lg p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-500/10">
              <AlertTriangle className="h-5 w-5 text-red-400" />
            </div>
            <div>
              <p className="text-xl font-semibold text-foreground">
                {errorCount}
              </p>
              <p className="text-xs text-muted-foreground">Con Error</p>
            </div>
          </div>
        </motion.div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {integrations.map((integration) => {
            const status = statusConfig[integration.status];
            const StatusIcon = status.icon;

            return (
              <motion.div
                key={integration.id}
                variants={itemVariants}
                whileHover={{ y: -4, transition: { duration: 0.2 } }}
                className="glass-card glass-card-hover group relative overflow-hidden rounded-xl p-5"
              >
                <div
                  className={`absolute left-0 right-0 top-0 h-0.5 ${status.dotClass}`}
                />

                <div className="mb-4 flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-muted/50 text-xl">
                      {integration.icon}
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-foreground">
                        {integration.name}
                      </h3>
                      <span
                        className={`mt-1 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${status.bgClass} ${status.textClass}`}
                      >
                        <StatusIcon className="h-2.5 w-2.5" />
                        {status.label}
                      </span>
                    </div>
                  </div>
                </div>

                <p className="mb-3 text-xs leading-relaxed text-muted-foreground">
                  {integration.description}
                </p>

                {integration.details ? (
                  <p className="mb-3 text-xs text-foreground/70">
                    {integration.details}
                  </p>
                ) : null}

                <div className="flex items-center justify-between border-t border-border/50 pt-3">
                  {integration.lastSync ? (
                    <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                      <RefreshCw className="h-2.5 w-2.5" />
                      {integration.lastSync}
                    </span>
                  ) : (
                    <span />
                  )}

                  {integration.id === "google" ? (
                    <div className="flex items-center gap-2">
                      {integration.status === "connected" ? (
                        <button
                          onClick={handleSyncGoogle}
                          disabled={syncing}
                          className="flex items-center gap-1 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-300 transition-colors hover:bg-emerald-500/20 disabled:opacity-50"
                        >
                          <RefreshCw
                            className={`h-3 w-3 ${syncing ? "animate-spin" : ""}`}
                          />
                          {syncing ? "Sincronizando..." : "Sincronizar ahora"}
                        </button>
                      ) : null}
                      <button
                        onClick={handleConnectGoogle}
                        disabled={connecting}
                        className="flex items-center gap-1 rounded-md border border-gold/20 bg-gold/10 px-2.5 py-1 text-xs text-gold transition-colors hover:bg-gold/20 disabled:opacity-50"
                      >
                        {connecting
                          ? "Redirigiendo..."
                          : integration.status === "connected"
                            ? "Reconectar"
                            : "Conectar con Google"}
                        <ExternalLink className="h-3 w-3" />
                      </button>
                    </div>
                  ) : (
                    <button className="flex items-center gap-1 text-xs text-gold opacity-0 transition-colors hover:text-gold-light group-hover:opacity-100">
                      {integration.status === "connected"
                        ? "Configurar"
                        : integration.status === "error"
                          ? "Reconectar"
                          : "Activar"}
                      <ExternalLink className="h-3 w-3" />
                    </button>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>

        <ICalFeedsSection />
      </motion.div>
    </AppShell>
  );
}

export default function IntegracionesPage() {
  return (
    <Suspense
      fallback={
        <AppShell>
          <LoadingCard
            title="Cargando integraciones"
            message="Preparando configuracion de conexiones."
          />
        </AppShell>
      }
    >
      <IntegracionesContent />
    </Suspense>
  );
}

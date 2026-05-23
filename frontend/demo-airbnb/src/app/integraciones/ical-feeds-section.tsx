"use client";

import { ErrorCard } from "@/components/page-feedback";
import { useAsyncData } from "@/hooks/use-async-data";
import {
  createICalFeed,
  deleteICalFeed,
  fetchICalFeeds,
  fetchProperties,
  syncAllICalFeeds,
  syncICalFeedNow,
  type ICalFeedApi,
  type PropertyApi,
} from "@/lib/api";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Calendar,
  Check,
  Clock,
  Plus,
  RefreshCw,
  Trash2,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";

type FeedStatus = ICalFeedApi["last_sync_status"];

const statusStyle: Record<
  FeedStatus,
  { label: string; bg: string; text: string; icon: typeof Check }
> = {
  ok: {
    label: "Sincronizado",
    bg: "bg-emerald-500/10",
    text: "text-emerald-300",
    icon: Check,
  },
  error: {
    label: "Error",
    bg: "bg-red-500/10",
    text: "text-red-300",
    icon: AlertTriangle,
  },
  never: {
    label: "Sin sincronizar",
    bg: "bg-yellow-500/10",
    text: "text-yellow-300",
    icon: Clock,
  },
};

function formatRelative(value: string | null): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export default function ICalFeedsSection() {
  const {
    data: feeds,
    error,
    loading,
    reload,
  } = useAsyncData(() => fetchICalFeeds(), []);

  const today = useMemo(() => new Date(), []);
  const { data: properties } = useAsyncData<PropertyApi[]>(
    () =>
      fetchProperties({
        year: today.getFullYear(),
        month: today.getMonth() + 1,
      }),
    [],
  );

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ property: "", label: "", ical_url: "" });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [syncingAll, setSyncingAll] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);

  const resetForm = () => {
    setForm({ property: "", label: "", ical_url: "" });
    setFormError(null);
  };

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await createICalFeed({
        property: form.property,
        label: form.label.trim(),
        ical_url: form.ical_url.trim(),
        is_active: true,
      });
      setShowForm(false);
      resetForm();
      reload?.();
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "No se pudo crear el feed.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleSync = async (feedId: string) => {
    setBusyId(feedId);
    setBanner(null);
    try {
      const result = await syncICalFeedNow(feedId);
      setBanner(
        result.errors.length > 0
          ? `Sync con errores: ${result.errors.join(" · ")}`
          : `Feed sincronizado: ${result.created} nuevas, ${result.skipped} omitidas.`,
      );
      reload?.();
    } catch (err) {
      setBanner(
        err instanceof Error ? `Error: ${err.message}` : "Error sincronizando.",
      );
    } finally {
      setBusyId(null);
    }
  };

  const handleSyncAll = async () => {
    setSyncingAll(true);
    setBanner(null);
    try {
      const result = await syncAllICalFeeds();
      setBanner(
        `Sync global: ${result.feeds} feeds · ${result.created} reservas nuevas · ${result.errors} con error.`,
      );
      reload?.();
    } catch (err) {
      setBanner(
        err instanceof Error ? `Error: ${err.message}` : "Error en sync global.",
      );
    } finally {
      setSyncingAll(false);
    }
  };

  const handleDelete = async (feedId: string) => {
    if (!window.confirm("¿Eliminar este feed? Las reservas ya importadas se mantendrán.")) {
      return;
    }
    setBusyId(feedId);
    setBanner(null);
    try {
      await deleteICalFeed(feedId);
      reload?.();
    } catch (err) {
      setBanner(
        err instanceof Error ? `Error: ${err.message}` : "Error eliminando feed.",
      );
    } finally {
      setBusyId(null);
    }
  };

  const propertyOptions = properties ?? [];
  const items = feeds ?? [];

  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="mt-10"
    >
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gold/10 text-gold">
            <Calendar className="h-5 w-5" />
          </div>
          <div>
            <h2 className="font-serif text-xl font-semibold text-foreground">
              Feeds iCal (Airbnb, Booking.com)
            </h2>
            <p className="text-xs text-muted-foreground">
              Importa bloqueos y reservas externas via URL .ics. Una propiedad puede
              tener varios feeds.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {items.length > 0 ? (
            <button
              onClick={handleSyncAll}
              disabled={syncingAll}
              className="flex items-center gap-1.5 rounded-md border border-gold/20 bg-gold/10 px-3 py-1.5 text-xs text-gold transition-colors hover:bg-gold/20 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${syncingAll ? "animate-spin" : ""}`} />
              {syncingAll ? "Sincronizando..." : "Sync todos"}
            </button>
          ) : null}
          <button
            onClick={() => {
              resetForm();
              setShowForm((v) => !v);
            }}
            className="flex items-center gap-1.5 rounded-md border border-gold/30 bg-gold/15 px-3 py-1.5 text-xs font-medium text-gold transition-colors hover:bg-gold/25"
          >
            {showForm ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
            {showForm ? "Cancelar" : "Añadir feed"}
          </button>
        </div>
      </div>

      {banner ? (
        <div className="mb-4 flex items-start gap-2 rounded-lg border border-gold/20 bg-gold/10 p-3 text-xs text-gold">
          <RefreshCw className="mt-0.5 h-3.5 w-3.5" />
          <span>{banner}</span>
        </div>
      ) : null}

      {showForm ? (
        <form
          onSubmit={handleCreate}
          className="glass-card mb-4 grid grid-cols-1 gap-3 rounded-xl p-4 md:grid-cols-4"
        >
          <label className="flex flex-col gap-1 text-xs">
            <span className="text-muted-foreground">Propiedad</span>
            <select
              required
              value={form.property}
              onChange={(e) => setForm((f) => ({ ...f, property: e.target.value }))}
              className="rounded-md border border-border bg-muted/30 px-2 py-1.5 text-foreground"
            >
              <option value="">Selecciona...</option>
              {propertyOptions.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs">
            <span className="text-muted-foreground">Etiqueta</span>
            <input
              required
              type="text"
              placeholder="Airbnb"
              value={form.label}
              onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
              className="rounded-md border border-border bg-muted/30 px-2 py-1.5 text-foreground"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs md:col-span-2">
            <span className="text-muted-foreground">URL del iCal</span>
            <input
              required
              type="url"
              placeholder="https://www.airbnb.com/calendar/ical/..."
              value={form.ical_url}
              onChange={(e) => setForm((f) => ({ ...f, ical_url: e.target.value }))}
              className="rounded-md border border-border bg-muted/30 px-2 py-1.5 text-foreground"
            />
          </label>
          {formError ? (
            <p className="md:col-span-4 text-xs text-red-400">{formError}</p>
          ) : null}
          <div className="md:col-span-4 flex justify-end">
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md border border-gold/30 bg-gold/20 px-4 py-1.5 text-xs font-medium text-gold transition-colors hover:bg-gold/30 disabled:opacity-50"
            >
              {submitting ? "Guardando..." : "Crear feed"}
            </button>
          </div>
        </form>
      ) : null}

      {loading ? (
        <p className="text-xs text-muted-foreground">Cargando feeds...</p>
      ) : null}

      {!loading && error ? (
        <ErrorCard title="No fue posible cargar los feeds iCal" message={error} />
      ) : null}

      {!loading && !error && items.length === 0 ? (
        <div className="glass-card rounded-xl p-6 text-center">
          <p className="text-sm text-muted-foreground">
            Aún no hay feeds configurados. Añade uno para empezar a importar bloqueos
            de Airbnb, Booking.com u otras plataformas.
          </p>
        </div>
      ) : null}

      {items.length > 0 ? (
        <div className="glass-card overflow-hidden rounded-xl">
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-muted/20 text-xs text-muted-foreground">
              <tr>
                <th className="px-4 py-2 text-left font-medium">Propiedad</th>
                <th className="px-4 py-2 text-left font-medium">Etiqueta</th>
                <th className="px-4 py-2 text-left font-medium">Estado</th>
                <th className="px-4 py-2 text-left font-medium">Última sync</th>
                <th className="px-4 py-2 text-right font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((feed) => {
                const style = statusStyle[feed.last_sync_status];
                const StatusIcon = style.icon;
                const busy = busyId === feed.id;
                return (
                  <tr
                    key={feed.id}
                    className="border-b border-border/50 last:border-0"
                  >
                    <td className="px-4 py-3 text-foreground">{feed.property_name}</td>
                    <td className="px-4 py-3 text-foreground">{feed.label}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${style.bg} ${style.text}`}
                        title={feed.last_sync_error || undefined}
                      >
                        <StatusIcon className="h-2.5 w-2.5" />
                        {style.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">
                      {formatRelative(feed.last_synced_at)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleSync(feed.id)}
                          disabled={busy}
                          className="flex items-center gap-1 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-xs text-emerald-300 transition-colors hover:bg-emerald-500/20 disabled:opacity-50"
                        >
                          <RefreshCw
                            className={`h-3 w-3 ${busy ? "animate-spin" : ""}`}
                          />
                          Sync
                        </button>
                        <button
                          onClick={() => handleDelete(feed.id)}
                          disabled={busy}
                          className="flex items-center gap-1 rounded-md border border-red-500/30 bg-red-500/10 px-2 py-1 text-xs text-red-300 transition-colors hover:bg-red-500/20 disabled:opacity-50"
                        >
                          <Trash2 className="h-3 w-3" />
                          Borrar
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </motion.section>
  );
}

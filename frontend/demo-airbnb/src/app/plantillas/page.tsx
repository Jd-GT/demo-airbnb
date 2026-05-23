"use client";

import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import {
  MessageChannel,
  MessageTemplate,
  RenderedMessage,
  Reservation,
  createMessageTemplate,
  deleteMessageTemplate,
  downloadVoucherPdf,
  fetchMessageTemplates,
  fetchReservations,
  renderMessage,
} from "@/lib/api";
import { motion } from "framer-motion";
import {
  Copy,
  Download,
  FileText,
  Loader2,
  MessageSquare,
  Plus,
  ShieldAlert,
  Trash2,
} from "lucide-react";

const PLACEHOLDERS = [
  "{{guest_name}}",
  "{{property_name}}",
  "{{property_address}}",
  "{{check_in}}",
  "{{check_out}}",
  "{{nights}}",
  "{{total_amount}}",
  "{{balance_due}}",
  "{{amount_paid}}",
  "{{reservation_id}}",
  "{{tenant_name}}",
];

export default function PlantillasPage() {
  const { can, loading: authLoading } = useAuth();
  // Templates live under booking module too (operational)
  const canRead = can("booking", "read");
  const canWrite = can("booking", "write");

  const [templates, setTemplates] = useState<MessageTemplate[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);

  // create form
  const [name, setName] = useState("");
  const [channel, setChannel] = useState<MessageChannel>("WHATSAPP");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("Hola {{guest_name}},\n\n");

  // render dialog state
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [selectedReservation, setSelectedReservation] = useState<string>("");
  const [rendering, setRendering] = useState(false);
  const [rendered, setRendered] = useState<RenderedMessage | null>(null);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    if (!canRead) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const today = new Date();
      const from = new Date(today.getFullYear(), today.getMonth() - 6, 1)
        .toISOString()
        .slice(0, 10);
      const to = new Date(today.getFullYear(), today.getMonth() + 6, 1)
        .toISOString()
        .slice(0, 10);
      const [tpls, resv] = await Promise.all([
        fetchMessageTemplates(),
        fetchReservations({ from, to }),
      ]);
      setTemplates(tpls);
      setReservations(resv);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error cargando plantillas");
    } finally {
      setLoading(false);
    }
  }, [canRead]);

  useEffect(() => {
    if (!authLoading) load();
  }, [authLoading, load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name || !body) {
      setError("Nombre y cuerpo son obligatorios.");
      return;
    }
    setCreating(true);
    setError("");
    try {
      const created = await createMessageTemplate({ name, channel, subject, body });
      setTemplates((prev) => [...prev, created]);
      setName("");
      setSubject("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error creando plantilla");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("¿Eliminar esta plantilla?")) return;
    try {
      await deleteMessageTemplate(id);
      setTemplates((prev) => prev.filter((t) => t.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error eliminando plantilla");
    }
  }

  async function handleRender() {
    if (!selectedTemplate || !selectedReservation) {
      setError("Selecciona plantilla y reserva.");
      return;
    }
    setRendering(true);
    setError("");
    try {
      const result = await renderMessage(selectedTemplate, selectedReservation);
      setRendered(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error renderizando");
    } finally {
      setRendering(false);
    }
  }

  function handleCopy() {
    if (!rendered) return;
    navigator.clipboard.writeText(rendered.body);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function handleVoucher() {
    if (!selectedReservation) {
      setError("Selecciona una reserva primero.");
      return;
    }
    try {
      await downloadVoucherPdf(selectedReservation);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error descargando voucher");
    }
  }

  function insertPlaceholder(p: string) {
    setBody((prev) => prev + p);
  }

  if (authLoading || loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-gold" />
        </div>
      </AppShell>
    );
  }

  if (!canRead) {
    return (
      <AppShell>
        <div className="glass-card rounded-xl p-6 flex items-start gap-3">
          <ShieldAlert className="h-5 w-5 text-zinc-400 mt-0.5" />
          <p className="text-sm">No tienes permisos sobre booking.</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        <div className="mb-6">
          <h1 className="font-serif text-3xl font-semibold text-gold-gradient">
            Plantillas de mensaje
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Crea plantillas con placeholders y úsalas para renderizar mensajes
            por reserva. (No envía mensajes; copia al portapapeles).
          </p>
        </div>

        {error && (
          <p className="text-sm text-red-400 bg-red-500/10 p-3 rounded-lg mb-4">
            {error}
          </p>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {canWrite && (
            <div className="glass-card rounded-xl p-6">
              <div className="flex items-center gap-2 mb-3">
                <Plus className="h-5 w-5 text-gold" />
                <h2 className="font-serif text-xl font-semibold">
                  Nueva plantilla
                </h2>
              </div>
              <form onSubmit={handleCreate} className="space-y-3">
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Nombre (ej: Confirmación check-in)"
                  className={inputClass}
                  required
                />
                <select
                  value={channel}
                  onChange={(e) => setChannel(e.target.value as MessageChannel)}
                  className={inputClass}
                >
                  <option value="WHATSAPP">WhatsApp</option>
                  <option value="EMAIL">Email</option>
                  <option value="INTERNAL">Interno</option>
                </select>
                {channel === "EMAIL" && (
                  <input
                    type="text"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="Asunto (Email)"
                    className={inputClass}
                  />
                )}
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  rows={6}
                  className={`${inputClass} font-mono text-sm`}
                  required
                />
                <div className="flex flex-wrap gap-1">
                  {PLACEHOLDERS.map((p) => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => insertPlaceholder(p)}
                      className="text-xs px-2 py-1 rounded bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
                    >
                      {p}
                    </button>
                  ))}
                </div>
                <button
                  type="submit"
                  disabled={creating}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-gold text-zinc-900 font-medium hover:bg-gold/90 disabled:opacity-50"
                >
                  {creating ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4" />
                  )}
                  Guardar plantilla
                </button>
              </form>
            </div>
          )}

          <div className="glass-card rounded-xl p-6">
            <div className="flex items-center gap-2 mb-3">
              <MessageSquare className="h-5 w-5 text-gold" />
              <h2 className="font-serif text-xl font-semibold">
                Renderizar para una reserva
              </h2>
            </div>
            <div className="space-y-3">
              <select
                value={selectedTemplate}
                onChange={(e) => setSelectedTemplate(e.target.value)}
                className={inputClass}
              >
                <option value="">Selecciona una plantilla…</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.channel})
                  </option>
                ))}
              </select>
              <select
                value={selectedReservation}
                onChange={(e) => setSelectedReservation(e.target.value)}
                className={inputClass}
              >
                <option value="">Selecciona una reserva…</option>
                {reservations.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.guest_name} — {r.property_name} ({r.check_in} →{" "}
                    {r.check_out})
                  </option>
                ))}
              </select>
              <div className="flex gap-2">
                <button
                  onClick={handleRender}
                  disabled={rendering}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-gold text-zinc-900 font-medium hover:bg-gold/90 disabled:opacity-50"
                >
                  {rendering ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <MessageSquare className="h-4 w-4" />
                  )}
                  Renderizar
                </button>
                <button
                  onClick={handleVoucher}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg border border-zinc-700 hover:bg-zinc-800"
                  title="Descargar voucher PDF"
                >
                  <FileText className="h-4 w-4" /> PDF
                </button>
              </div>
              {rendered && (
                <div className="mt-3 p-3 rounded-lg bg-zinc-900/60 border border-zinc-800">
                  {rendered.subject && (
                    <p className="text-xs text-muted-foreground mb-1">
                      <strong>Asunto:</strong> {rendered.subject}
                    </p>
                  )}
                  <p className="text-sm whitespace-pre-line">{rendered.body}</p>
                  <button
                    onClick={handleCopy}
                    className="mt-3 flex items-center gap-1 text-xs px-2 py-1 rounded border border-zinc-700 hover:bg-zinc-800"
                  >
                    {copied ? (
                      <>
                        <Copy className="h-3 w-3" /> ¡Copiado!
                      </>
                    ) : (
                      <>
                        <Copy className="h-3 w-3" /> Copiar al portapapeles
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="glass-card rounded-xl p-6">
          <h2 className="font-serif text-xl font-semibold mb-4">
            Plantillas existentes ({templates.length})
          </h2>
          {templates.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sin plantillas aún.</p>
          ) : (
            <div className="space-y-3">
              {templates.map((t) => (
                <div
                  key={t.id}
                  className="p-3 rounded-lg bg-zinc-800/30 border border-zinc-800"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-foreground">{t.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {t.channel}
                        {t.subject && <span> · {t.subject}</span>}
                      </p>
                    </div>
                    {canWrite && (
                      <button
                        onClick={() => handleDelete(t.id)}
                        className="p-1 rounded text-red-400 hover:bg-red-500/10"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                  <pre className="mt-2 text-xs text-muted-foreground bg-zinc-900/60 p-2 rounded whitespace-pre-wrap font-mono">
                    {t.body}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </motion.div>
    </AppShell>
  );
}

const inputClass =
  "w-full px-3 py-2 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none";

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import {
  Contact,
  ContactStats,
  createContact,
  deleteContact,
  fetchContacts,
  fetchContactStats,
  updateContact,
} from "@/lib/api";
import { motion } from "framer-motion";
import {
  Loader2,
  Mail,
  Phone,
  Plus,
  Search,
  ShieldAlert,
  Trash2,
  User,
  X,
} from "lucide-react";

const TYPE_LABEL: Record<Contact["type"], string> = {
  GUEST: "Huésped",
  AGENT: "Agente / Comisionista",
  PLATFORM: "Plataforma (OTA)",
};

const TYPE_BADGE: Record<Contact["type"], string> = {
  GUEST: "bg-blue-500/15 text-blue-300",
  AGENT: "bg-amber-500/15 text-amber-300",
  PLATFORM: "bg-purple-500/15 text-purple-300",
};

export default function ClientesPage() {
  const { can, loading: authLoading } = useAuth();
  const canRead = can("crm", "read");
  const canWrite = can("crm", "write");

  const [contacts, setContacts] = useState<Contact[]>([]);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState<Contact["type"] | "ALL">("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<Contact | null>(null);

  const load = useCallback(async () => {
    if (!canRead) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await fetchContacts({ search });
      setContacts(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error cargando clientes");
    } finally {
      setLoading(false);
    }
  }, [canRead, search]);

  useEffect(() => {
    if (!authLoading) load();
  }, [authLoading, load]);

  const filtered = useMemo(
    () =>
      filterType === "ALL"
        ? contacts
        : contacts.filter((c) => c.type === filterType),
    [contacts, filterType]
  );

  const counts = useMemo(() => {
    const acc: Record<Contact["type"] | "ALL", number> = {
      ALL: contacts.length,
      GUEST: 0,
      AGENT: 0,
      PLATFORM: 0,
    };
    for (const c of contacts) acc[c.type]++;
    return acc;
  }, [contacts]);

  async function handleDelete(c: Contact) {
    if (
      !confirm(
        `¿Eliminar "${c.name}"? Si tiene reservas asociadas, la operación fallará.`
      )
    )
      return;
    try {
      await deleteContact(c.id);
      setContacts((prev) => prev.filter((x) => x.id !== c.id));
      if (selected?.id === c.id) setSelected(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error eliminando");
    }
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
          <p className="text-sm">No tienes permisos sobre CRM.</p>
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
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="font-serif text-3xl font-semibold text-gold-gradient">
              Clientes
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Mini-CRM de huéspedes, agentes y plataformas con reportes por
              cliente.
            </p>
          </div>
          {canWrite && (
            <button
              onClick={() => setShowCreate(true)}
              className="flex items-center gap-2 rounded-lg bg-gold px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-gold/90"
            >
              <Plus className="h-4 w-4" />
              Nuevo cliente
            </button>
          )}
        </div>

        {error && (
          <p className="text-sm text-red-400 bg-red-500/10 p-3 rounded-lg mb-4">
            {error}
          </p>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          {(
            [
              ["ALL", "Total"],
              ["GUEST", "Huéspedes"],
              ["AGENT", "Agentes"],
              ["PLATFORM", "Plataformas"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setFilterType(key)}
              className={`glass-card rounded-xl p-4 text-left transition-colors ${
                filterType === key ? "ring-2 ring-gold/40" : "hover:bg-zinc-800/30"
              }`}
            >
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                {label}
              </p>
              <p className="font-serif text-2xl text-gold mt-1">
                {counts[key]}
              </p>
            </button>
          ))}
        </div>

        <div className="glass-card rounded-xl p-4 mb-4 flex items-center gap-2">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por nombre, email o teléfono…"
            className="flex-1 bg-transparent border-0 outline-none text-sm text-foreground placeholder:text-muted-foreground"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="glass-card rounded-xl p-2 lg:col-span-1 max-h-[70vh] overflow-y-auto">
            {filtered.length === 0 ? (
              <p className="p-4 text-sm text-muted-foreground">
                Sin clientes en este filtro.
              </p>
            ) : (
              filtered.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setSelected(c)}
                  className={`w-full text-left rounded-lg p-3 mb-1 transition-colors ${
                    selected?.id === c.id
                      ? "bg-zinc-800/60"
                      : "hover:bg-zinc-800/30"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-foreground">{c.name}</p>
                    <span className={`text-xs px-2 py-0.5 rounded ${TYPE_BADGE[c.type]}`}>
                      {TYPE_LABEL[c.type]}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1 flex items-center gap-2">
                    {c.email && (
                      <span className="flex items-center gap-1">
                        <Mail className="h-3 w-3" /> {c.email}
                      </span>
                    )}
                    {c.phone && (
                      <span className="flex items-center gap-1">
                        <Phone className="h-3 w-3" /> {c.phone}
                      </span>
                    )}
                    {!c.email && !c.phone && <span>—</span>}
                  </p>
                  {c.tax_id && (
                    <p className="text-xs text-zinc-500 mt-1">
                      ID fiscal: {c.tax_id}
                    </p>
                  )}
                </button>
              ))
            )}
          </div>

          <div className="lg:col-span-2">
            {selected ? (
              <ContactDetailPanel
                key={selected.id}
                contact={selected}
                canWrite={canWrite}
                onUpdated={(updated) => {
                  setContacts((prev) =>
                    prev.map((x) => (x.id === updated.id ? updated : x))
                  );
                  setSelected(updated);
                }}
                onDeleted={() => handleDelete(selected)}
              />
            ) : (
              <div className="glass-card rounded-xl p-6 text-sm text-muted-foreground">
                Selecciona un cliente de la lista para ver su perfil y reportes.
              </div>
            )}
          </div>
        </div>

        {showCreate && (
          <NewContactModal
            onClose={() => setShowCreate(false)}
            onCreated={(c) => {
              setContacts((prev) => [c, ...prev]);
              setSelected(c);
              setShowCreate(false);
            }}
          />
        )}
      </motion.div>
    </AppShell>
  );
}

// ---------- Detail panel with stats + edit ----------

function ContactDetailPanel({
  contact,
  canWrite,
  onUpdated,
  onDeleted,
}: {
  contact: Contact;
  canWrite: boolean;
  onUpdated: (c: Contact) => void;
  onDeleted: () => void;
}) {
  const [stats, setStats] = useState<ContactStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");

  // edit fields
  const [form, setForm] = useState<Contact>(contact);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setForm(contact);
    setEditing(false);
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const s = await fetchContactStats(contact.id);
        if (!cancelled) setStats(s);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [contact.id]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const updated = await updateContact(contact.id, {
        name: form.name,
        email: form.email,
        phone: form.phone,
        type: form.type,
        commission_rate: form.commission_rate,
        tax_id: form.tax_id,
        address: form.address,
        nationality: form.nationality,
        notes: form.notes,
      });
      onUpdated(updated);
      setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error guardando");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="glass-card rounded-xl p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-full bg-zinc-800 flex items-center justify-center">
              <User className="h-6 w-6 text-gold" />
            </div>
            <div>
              <h2 className="font-serif text-2xl font-semibold">
                {contact.name}
              </h2>
              <span className={`text-xs px-2 py-0.5 rounded ${TYPE_BADGE[contact.type]}`}>
                {TYPE_LABEL[contact.type]}
              </span>
            </div>
          </div>
          {canWrite && (
            <div className="flex gap-2">
              {!editing && (
                <button
                  onClick={() => setEditing(true)}
                  className="text-xs px-3 py-1.5 rounded-lg border border-zinc-700 hover:bg-zinc-800"
                >
                  Editar
                </button>
              )}
              <button
                onClick={onDeleted}
                className="p-1.5 rounded text-red-400 hover:bg-red-500/10"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>

        {error && (
          <p className="text-xs text-red-400 bg-red-500/10 p-2 rounded mb-3">
            {error}
          </p>
        )}

        {editing ? (
          <form onSubmit={handleSave} className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Input label="Nombre *" value={form.name} onChange={(v) => setForm({ ...form, name: v })} required />
            <SelectField
              label="Tipo *"
              value={form.type}
              onChange={(v) => setForm({ ...form, type: v as Contact["type"] })}
              options={[
                ["GUEST", "Huésped"],
                ["AGENT", "Agente"],
                ["PLATFORM", "Plataforma"],
              ]}
            />
            <Input label="Email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} type="email" />
            <Input label="Teléfono" value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} placeholder="+57 300 1234567" />
            <Input label="ID fiscal (cédula/NIT/RUT)" value={form.tax_id} onChange={(v) => setForm({ ...form, tax_id: v })} />
            <Input label="Nacionalidad" value={form.nationality} onChange={(v) => setForm({ ...form, nationality: v })} />
            <Input label="Dirección" value={form.address} onChange={(v) => setForm({ ...form, address: v })} className="md:col-span-2" />
            {form.type === "AGENT" && (
              <Input
                label="% Comisión"
                value={form.commission_rate}
                onChange={(v) => setForm({ ...form, commission_rate: v })}
                type="number"
              />
            )}
            <label className="md:col-span-2 flex flex-col text-xs text-muted-foreground">
              Notas internas
              <textarea
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                rows={3}
                className={inputClass}
              />
            </label>
            <div className="md:col-span-2 flex gap-2 justify-end">
              <button
                type="button"
                onClick={() => {
                  setEditing(false);
                  setForm(contact);
                }}
                className="rounded-lg border border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-800"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving}
                className="flex items-center gap-2 rounded-lg bg-gold px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-gold/90 disabled:opacity-50"
              >
                {saving && <Loader2 className="h-3 w-3 animate-spin" />}
                Guardar
              </button>
            </div>
          </form>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            <Field label="Email" value={contact.email} />
            <Field label="Teléfono" value={contact.phone} />
            <Field label="ID fiscal" value={contact.tax_id} />
            <Field label="Nacionalidad" value={contact.nationality} />
            <Field label="Dirección" value={contact.address} className="md:col-span-2" />
            {contact.type === "AGENT" && (
              <Field label="Comisión" value={`${contact.commission_rate}%`} />
            )}
            {contact.notes && (
              <div className="md:col-span-2">
                <p className="text-xs text-muted-foreground">Notas</p>
                <p className="text-sm whitespace-pre-line mt-1">{contact.notes}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Stats panel */}
      <div className="glass-card rounded-xl p-6">
        <h3 className="font-serif text-xl font-semibold mb-4">
          Reporte del cliente
        </h3>
        {loading ? (
          <Loader2 className="h-5 w-5 animate-spin text-gold" />
        ) : !stats ? (
          <p className="text-sm text-muted-foreground">Sin datos.</p>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <ReportStat
                label="Reservas confirmadas"
                value={stats.confirmed_reservations_count}
              />
              <ReportStat label="Reservas canceladas" value={stats.cancelled_reservations_count} />
              <ReportStat label="Total noches" value={stats.nights_total} />
              <ReportStat
                label="Saldo pendiente"
                value={`$${stats.outstanding_balance}`}
                highlight={parseFloat(stats.outstanding_balance) > 0}
              />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <ReportStat label="Total facturado" value={`$${stats.total_billed}`} />
              <ReportStat
                label="Pagado alojamiento"
                value={`$${stats.total_lodging_paid}`}
                positive
              />
              <ReportStat
                label="Extras pagados"
                value={`$${stats.total_extras_paid}`}
                positive
              />
              <ReportStat
                label="Reembolsado"
                value={`$${stats.total_refunded}`}
                negative
              />
            </div>
            {(stats.first_check_in || stats.last_check_out) && (
              <p className="text-xs text-muted-foreground border-t border-zinc-800 pt-3">
                Primera estancia:{" "}
                <span className="text-foreground">{stats.first_check_in ?? "—"}</span>{" "}
                · Última check-out:{" "}
                <span className="text-foreground">{stats.last_check_out ?? "—"}</span>
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------- New contact modal ----------

function NewContactModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (c: Contact) => void;
}) {
  const [form, setForm] = useState({
    name: "",
    type: "GUEST" as Contact["type"],
    email: "",
    phone: "",
    tax_id: "",
    nationality: "",
    address: "",
    commission_rate: "",
    notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name) {
      setError("Nombre obligatorio.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const created = await createContact({
        name: form.name.trim(),
        type: form.type,
        email: form.email || undefined,
        phone: form.phone || undefined,
        tax_id: form.tax_id || undefined,
        nationality: form.nationality || undefined,
        address: form.address || undefined,
        notes: form.notes || undefined,
        commission_rate:
          form.type === "AGENT" && form.commission_rate
            ? form.commission_rate
            : undefined,
      });
      onCreated(created);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error creando");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        onClick={(e) => e.stopPropagation()}
        className="glass-card w-full max-w-xl rounded-xl p-6 my-8"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-serif text-xl font-semibold">Nuevo cliente</h2>
          <button onClick={onClose} className="rounded p-1 hover:bg-muted/50">
            <X className="h-4 w-4" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <Input label="Nombre *" value={form.name} onChange={(v) => setForm({ ...form, name: v })} required />
          <SelectField
            label="Tipo *"
            value={form.type}
            onChange={(v) => setForm({ ...form, type: v as Contact["type"] })}
            options={[
              ["GUEST", "Huésped"],
              ["AGENT", "Agente"],
              ["PLATFORM", "Plataforma"],
            ]}
          />
          <Input label="Email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} type="email" />
          <Input label="Teléfono" value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} />
          <Input label="ID fiscal" value={form.tax_id} onChange={(v) => setForm({ ...form, tax_id: v })} placeholder="Cédula / RUT / NIT" />
          <Input label="Nacionalidad" value={form.nationality} onChange={(v) => setForm({ ...form, nationality: v })} />
          <Input label="Dirección" value={form.address} onChange={(v) => setForm({ ...form, address: v })} className="md:col-span-2" />
          {form.type === "AGENT" && (
            <Input
              label="% Comisión"
              value={form.commission_rate}
              onChange={(v) => setForm({ ...form, commission_rate: v })}
              type="number"
            />
          )}
          <label className="md:col-span-2 flex flex-col text-xs text-muted-foreground">
            Notas internas
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={2}
              className={inputClass}
            />
          </label>
          {error && (
            <p className="md:col-span-2 text-xs text-red-400 bg-red-500/10 p-2 rounded">
              {error}
            </p>
          )}
          <div className="md:col-span-2 flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-800"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 rounded-lg bg-gold px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-gold/90 disabled:opacity-50"
            >
              {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
              Crear
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}

// ---------- Tiny helpers ----------

const inputClass =
  "mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800/50 px-3 py-2 text-sm text-foreground focus:border-gold/50 focus:outline-none";

function Input({
  label,
  value,
  onChange,
  type = "text",
  required,
  placeholder,
  className,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
  placeholder?: string;
  className?: string;
}) {
  return (
    <label className={`flex flex-col text-xs text-muted-foreground ${className ?? ""}`}>
      {label}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        className={inputClass}
      />
    </label>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: ReadonlyArray<readonly [string, string]>;
}) {
  return (
    <label className="flex flex-col text-xs text-muted-foreground">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={inputClass}
      >
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );
}

function Field({ label, value, className }: { label: string; value: string; className?: string }) {
  return (
    <div className={className}>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm text-foreground">{value || "—"}</p>
    </div>
  );
}

function ReportStat({
  label,
  value,
  positive,
  negative,
  highlight,
}: {
  label: string;
  value: number | string;
  positive?: boolean;
  negative?: boolean;
  highlight?: boolean;
}) {
  const colour = highlight
    ? "text-gold"
    : positive
      ? "text-emerald-300"
      : negative
        ? "text-red-300"
        : "text-foreground";
  return (
    <div className="rounded-lg bg-zinc-900/40 border border-zinc-800 p-3">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className={`font-serif text-xl mt-1 ${colour}`}>{value}</p>
    </div>
  );
}

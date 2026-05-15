"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Contact,
  Property,
  QuoteResult,
  checkAvailability,
  createContact,
  createReservation,
  fetchContacts,
  fetchProperties,
  quoteReservation,
} from "@/lib/api";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Check,
  Loader2,
  Plus,
  X,
} from "lucide-react";

const TYPE_LABEL: Record<Contact["type"], string> = {
  GUEST: "Huésped",
  PLATFORM: "Plataforma (Airbnb/Booking/...)",
  AGENT: "Agente",
};

export function NewReservationModal({
  initialCheckIn,
  onClose,
  onCreated,
}: {
  initialCheckIn?: string;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [properties, setProperties] = useState<Property[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [checkingAvail, setCheckingAvail] = useState(false);
  const [quote, setQuote] = useState<QuoteResult | null>(null);
  const [available, setAvailable] = useState<boolean | null>(null);

  // form fields
  const [propertyId, setPropertyId] = useState("");
  const [guestId, setGuestId] = useState("");
  const [agentId, setAgentId] = useState("");
  const [checkIn, setCheckIn] = useState(
    initialCheckIn || new Date().toISOString().slice(0, 10)
  );
  const [checkOut, setCheckOut] = useState(() => {
    const d = new Date(initialCheckIn || new Date().toISOString().slice(0, 10));
    d.setDate(d.getDate() + 2);
    return d.toISOString().slice(0, 10);
  });
  const [status, setStatus] = useState<"DRAFT" | "CONFIRMED">("CONFIRMED");

  // inline new contact
  const [showNewGuest, setShowNewGuest] = useState(false);
  const [creatingGuest, setCreatingGuest] = useState(false);
  const [newGuestName, setNewGuestName] = useState("");
  const [newGuestPhone, setNewGuestPhone] = useState("");
  const [newGuestType, setNewGuestType] = useState<Contact["type"]>("GUEST");

  // Contacts allowed as guest: GUEST + PLATFORM. AGENT goes in agent_id.
  const guestEligible = useMemo(
    () => contacts.filter((c) => c.type === "GUEST" || c.type === "PLATFORM"),
    [contacts]
  );
  const agents = useMemo(
    () => contacts.filter((c) => c.type === "AGENT"),
    [contacts]
  );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [props, allContacts] = await Promise.all([
          fetchProperties(),
          fetchContacts(),
        ]);
        if (cancelled) return;
        setProperties(props);
        setContacts(allContacts);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Error cargando datos");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // Re-quote whenever property or dates change
  useEffect(() => {
    setQuote(null);
    setAvailable(null);
    if (!propertyId || !checkIn || !checkOut) return;
    if (checkOut <= checkIn) return;
    let cancelled = false;
    async function fetchQuote() {
      setCheckingAvail(true);
      try {
        const [q, avail] = await Promise.all([
          quoteReservation({
            property_id: propertyId,
            check_in: checkIn,
            check_out: checkOut,
          }),
          checkAvailability({
            property_id: propertyId,
            check_in: checkIn,
            check_out: checkOut,
          }),
        ]);
        if (cancelled) return;
        setQuote(q);
        setAvailable(avail.available);
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof Error ? e.message : "Error consultando disponibilidad"
          );
        }
      } finally {
        if (!cancelled) setCheckingAvail(false);
      }
    }
    fetchQuote();
    return () => {
      cancelled = true;
    };
  }, [propertyId, checkIn, checkOut]);

  async function handleCreateGuest(e: React.FormEvent) {
    e.preventDefault();
    if (!newGuestName) return;
    setCreatingGuest(true);
    setError("");
    try {
      const created = await createContact({
        name: newGuestName.trim(),
        phone: newGuestPhone || undefined,
        type: newGuestType,
      });
      setContacts((prev) => [...prev, created]);
      setGuestId(created.id);
      setNewGuestName("");
      setNewGuestPhone("");
      setShowNewGuest(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error creando contacto");
    } finally {
      setCreatingGuest(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!propertyId || !guestId || !checkIn || !checkOut) {
      setError("Faltan campos obligatorios.");
      return;
    }
    if (available === false) {
      setError("Esa propiedad no está disponible en esas fechas.");
      return;
    }
    setCreating(true);
    setError("");
    try {
      await createReservation({
        property_id: propertyId,
        guest_id: guestId,
        agent_id: agentId || null,
        check_in: checkIn,
        check_out: checkOut,
        status,
      });
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error creando reserva");
    } finally {
      setCreating(false);
    }
  }

  const selectedGuest = contacts.find((c) => c.id === guestId);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 overflow-y-auto"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        onClick={(e) => e.stopPropagation()}
        className="glass-card w-full max-w-xl rounded-xl p-6 my-8"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-serif text-xl font-semibold">
            Nueva reserva manual
          </h2>
          <button
            onClick={onClose}
            className="rounded p-1 text-muted-foreground hover:bg-muted/50 hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-gold" />
          </div>
        ) : (
          <form onSubmit={handleCreate} className="space-y-3">
            <label className="flex flex-col text-xs text-muted-foreground">
              Propiedad *
              <select
                value={propertyId}
                onChange={(e) => setPropertyId(e.target.value)}
                className={modalInput}
                required
              >
                <option value="">Selecciona una propiedad…</option>
                {properties.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.address})
                  </option>
                ))}
              </select>
              {properties.length === 0 && (
                <span className="mt-1 text-red-300">
                  No hay propiedades. Créalas primero en /propiedades.
                </span>
              )}
            </label>

            <label className="flex flex-col text-xs text-muted-foreground">
              Titular de la reserva *
              <div className="flex gap-2">
                <select
                  value={guestId}
                  onChange={(e) => setGuestId(e.target.value)}
                  className={modalInput}
                  required
                >
                  <option value="">Selecciona huésped o plataforma…</option>
                  <optgroup label="Huéspedes">
                    {guestEligible
                      .filter((c) => c.type === "GUEST")
                      .map((g) => (
                        <option key={g.id} value={g.id}>
                          {g.name}
                          {g.phone ? ` — ${g.phone}` : ""}
                        </option>
                      ))}
                  </optgroup>
                  <optgroup label="Plataformas (reservas externas)">
                    {guestEligible
                      .filter((c) => c.type === "PLATFORM")
                      .map((g) => (
                        <option key={g.id} value={g.id}>
                          {g.name}
                        </option>
                      ))}
                  </optgroup>
                </select>
                <button
                  type="button"
                  onClick={() => setShowNewGuest((v) => !v)}
                  className="rounded-lg border border-zinc-700 px-3 text-xs hover:bg-zinc-800"
                >
                  + Nuevo
                </button>
              </div>
              {selectedGuest && (
                <span className="mt-1 text-xs text-muted-foreground">
                  Tipo: {TYPE_LABEL[selectedGuest.type]}
                </span>
              )}
            </label>

            {showNewGuest && (
              <div className="rounded-lg border border-zinc-700 bg-zinc-900/40 p-3 space-y-2">
                <select
                  value={newGuestType}
                  onChange={(e) =>
                    setNewGuestType(e.target.value as Contact["type"])
                  }
                  className={modalInput}
                >
                  <option value="GUEST">Huésped (persona real)</option>
                  <option value="PLATFORM">
                    Plataforma (Airbnb / Booking / etc.)
                  </option>
                </select>
                <input
                  type="text"
                  value={newGuestName}
                  onChange={(e) => setNewGuestName(e.target.value)}
                  placeholder={
                    newGuestType === "GUEST"
                      ? "Nombre del huésped"
                      : "Ej: Airbnb, Booking.com, Expedia"
                  }
                  className={modalInput}
                />
                {newGuestType === "GUEST" && (
                  <input
                    type="text"
                    value={newGuestPhone}
                    onChange={(e) => setNewGuestPhone(e.target.value)}
                    placeholder="Teléfono (opcional, ej: +57…)"
                    className={modalInput}
                  />
                )}
                <button
                  type="button"
                  onClick={handleCreateGuest}
                  disabled={creatingGuest || !newGuestName}
                  className="w-full rounded-lg bg-zinc-700 px-3 py-1.5 text-xs hover:bg-zinc-600 disabled:opacity-50 flex items-center justify-center gap-1"
                >
                  {creatingGuest ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Plus className="h-3 w-3" />
                  )}
                  Guardar
                </button>
              </div>
            )}

            {agents.length > 0 && (
              <label className="flex flex-col text-xs text-muted-foreground">
                Agente (opcional)
                <select
                  value={agentId}
                  onChange={(e) => setAgentId(e.target.value)}
                  className={modalInput}
                >
                  <option value="">Sin agente</option>
                  {agents.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name} ({a.commission_rate}%)
                    </option>
                  ))}
                </select>
              </label>
            )}

            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col text-xs text-muted-foreground">
                Check-in *
                <input
                  type="date"
                  value={checkIn}
                  onChange={(e) => setCheckIn(e.target.value)}
                  className={modalInput}
                  required
                />
              </label>
              <label className="flex flex-col text-xs text-muted-foreground">
                Check-out *
                <input
                  type="date"
                  value={checkOut}
                  onChange={(e) => setCheckOut(e.target.value)}
                  className={modalInput}
                  required
                />
              </label>
            </div>

            <label className="flex flex-col text-xs text-muted-foreground">
              Estado
              <select
                value={status}
                onChange={(e) =>
                  setStatus(e.target.value as "DRAFT" | "CONFIRMED")
                }
                className={modalInput}
              >
                <option value="CONFIRMED">Confirmada</option>
                <option value="DRAFT">Borrador / cotización</option>
              </select>
            </label>

            <div className="rounded-lg border border-zinc-700 bg-zinc-900/40 p-3">
              {checkingAvail ? (
                <p className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" /> Calculando…
                </p>
              ) : quote ? (
                <div className="space-y-1 text-xs">
                  <p className="flex items-center justify-between">
                    <span className="text-muted-foreground">
                      {quote.nights} noche(s) × ${quote.nightly_rate}
                    </span>
                    <span>${quote.subtotal_amount}</span>
                  </p>
                  {parseFloat(quote.cleaning_fee) > 0 && (
                    <p className="flex items-center justify-between">
                      <span className="text-muted-foreground">Limpieza</span>
                      <span>${quote.cleaning_fee}</span>
                    </p>
                  )}
                  <p className="flex items-center justify-between border-t border-zinc-700 pt-1 font-medium text-foreground">
                    <span>Total</span>
                    <span>${quote.total_amount}</span>
                  </p>
                  {quote.applied_rule_names.length > 0 && (
                    <p className="text-emerald-300 mt-1">
                      Reglas: {quote.applied_rule_names.join(", ")}
                    </p>
                  )}
                  <p
                    className={`flex items-center gap-1 mt-2 ${
                      available
                        ? "text-emerald-300"
                        : available === false
                          ? "text-red-300"
                          : "text-muted-foreground"
                    }`}
                  >
                    {available === true && (
                      <>
                        <Check className="h-3 w-3" /> Disponible
                      </>
                    )}
                    {available === false && (
                      <>
                        <AlertTriangle className="h-3 w-3" /> NO disponible
                        (overbooking)
                      </>
                    )}
                  </p>
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Selecciona propiedad y fechas para ver la cotización.
                </p>
              )}
            </div>

            {error && (
              <p className="rounded-lg bg-red-500/10 p-2 text-xs text-red-400">
                {error}
              </p>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg border border-zinc-700 px-4 py-2 text-sm hover:bg-zinc-800"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={creating || !available}
                className="flex items-center gap-2 rounded-lg bg-gold px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-gold/90 disabled:opacity-50"
              >
                {creating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                Crear reserva
              </button>
            </div>
          </form>
        )}
      </motion.div>
    </div>
  );
}

const modalInput =
  "mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800/50 px-3 py-2 text-sm text-foreground focus:border-gold/50 focus:outline-none";

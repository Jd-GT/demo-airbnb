"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { NewReservationModal } from "@/components/new-reservation-modal";
import {
  Reservation,
  fetchReservations,
  toNumber,
} from "@/lib/api";
import { motion } from "framer-motion";
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Filter,
  Loader2,
  Plus,
  Search,
  ShieldAlert,
} from "lucide-react";

const STATUS_LABEL: Record<string, string> = {
  DRAFT: "Borrador",
  CONFIRMED: "Confirmada",
  CHECKED_IN: "En casa",
  CHECKED_OUT: "Salida",
  CANCELLED: "Cancelada",
};

const STATUS_BADGE: Record<string, string> = {
  DRAFT: "bg-zinc-700 text-zinc-200",
  CONFIRMED: "bg-emerald-500/15 text-emerald-300",
  CHECKED_IN: "bg-blue-500/15 text-blue-300",
  CHECKED_OUT: "bg-purple-500/15 text-purple-300",
  CANCELLED: "bg-red-500/15 text-red-300",
};

const PAYMENT_BADGE: Record<string, string> = {
  PENDING: "bg-red-500/10 text-red-300",
  PARTIAL: "bg-yellow-500/10 text-yellow-300",
  PAID: "bg-emerald-500/10 text-emerald-300",
  OVERPAID: "bg-purple-500/10 text-purple-300",
};

const PAYMENT_LABEL: Record<string, string> = {
  PENDING: "Sin pagar",
  PARTIAL: "Parcial",
  PAID: "Pagada",
  OVERPAID: "Sobrepagada",
};

export default function ReservasPage() {
  const { can, loading: authLoading } = useAuth();
  const canRead = can("booking", "read");
  const canWrite = can("booking", "write");

  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  // filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [paymentFilter, setPaymentFilter] = useState<string>("ALL");
  const [monthsBack, setMonthsBack] = useState(6);
  const [monthsForward, setMonthsForward] = useState(6);

  const load = useCallback(async () => {
    if (!canRead) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const today = new Date();
      const from = new Date(
        today.getFullYear(),
        today.getMonth() - monthsBack,
        1
      )
        .toISOString()
        .slice(0, 10);
      const to = new Date(
        today.getFullYear(),
        today.getMonth() + monthsForward,
        1
      )
        .toISOString()
        .slice(0, 10);
      const data = await fetchReservations({ from, to });
      setReservations(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error cargando reservas");
    } finally {
      setLoading(false);
    }
  }, [canRead, monthsBack, monthsForward]);

  useEffect(() => {
    if (!authLoading) load();
  }, [authLoading, load]);

  const filtered = useMemo(() => {
    return reservations
      .filter((r) => {
        if (statusFilter !== "ALL" && r.status !== statusFilter) return false;
        if (
          paymentFilter !== "ALL" &&
          (r.payment_status ?? "PENDING") !== paymentFilter
        )
          return false;
        if (search) {
          const q = search.toLowerCase();
          if (
            !r.guest_name.toLowerCase().includes(q) &&
            !r.property_name.toLowerCase().includes(q)
          )
            return false;
        }
        return true;
      })
      .sort((a, b) => (a.check_in < b.check_in ? 1 : -1));
  }, [reservations, statusFilter, paymentFilter, search]);

  const counts = useMemo(() => {
    const acc = {
      total: reservations.length,
      confirmed: 0,
      cancelled: 0,
      pending_payment: 0,
      revenue: 0,
    };
    for (const r of reservations) {
      if (r.status === "CONFIRMED" || r.status === "CHECKED_IN" || r.status === "CHECKED_OUT") {
        acc.confirmed++;
        acc.revenue += toNumber(r.total_amount);
      }
      if (r.status === "CANCELLED") acc.cancelled++;
      const ps = r.payment_status ?? "PENDING";
      if (ps === "PENDING" || ps === "PARTIAL") acc.pending_payment++;
    }
    return acc;
  }, [reservations]);

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
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="font-serif text-3xl font-semibold text-gold-gradient">
              Reservas
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Listado completo de reservas. Crea desde aquí o desde el
              calendario.
            </p>
          </div>
          {canWrite && (
            <button
              onClick={() => setShowCreate(true)}
              className="flex items-center gap-2 rounded-lg bg-gold px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-gold/90"
            >
              <Plus className="h-4 w-4" />
              Nueva reserva
            </button>
          )}
        </div>

        {error && (
          <p className="text-sm text-red-400 bg-red-500/10 p-3 rounded-lg mb-4">
            {error}
          </p>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <Stat label="Total visibles" value={counts.total} icon={ClipboardList} />
          <Stat
            label="Confirmadas"
            value={counts.confirmed}
            icon={CalendarDays}
            positive
          />
          <Stat
            label="Con saldo pendiente"
            value={counts.pending_payment}
            icon={ChevronRight}
            highlight
          />
          <Stat
            label="Ingresos esperados"
            value={`$${counts.revenue.toLocaleString("es-CO", {
              maximumFractionDigits: 0,
            })}`}
            icon={Plus}
          />
        </div>

        <div className="glass-card rounded-xl p-4 mb-4 grid grid-cols-1 md:grid-cols-5 gap-2">
          <div className="md:col-span-2 flex items-center gap-2">
            <Search className="h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar huésped o propiedad…"
              className="flex-1 bg-transparent border-0 outline-none text-sm text-foreground placeholder:text-muted-foreground"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className={inputClass}
          >
            <option value="ALL">Todos los estados</option>
            <option value="DRAFT">Borrador</option>
            <option value="CONFIRMED">Confirmada</option>
            <option value="CHECKED_IN">En casa</option>
            <option value="CHECKED_OUT">Salida</option>
            <option value="CANCELLED">Cancelada</option>
          </select>
          <select
            value={paymentFilter}
            onChange={(e) => setPaymentFilter(e.target.value)}
            className={inputClass}
          >
            <option value="ALL">Cualquier estado de pago</option>
            <option value="PENDING">Sin pagar</option>
            <option value="PARTIAL">Pago parcial</option>
            <option value="PAID">Pagada</option>
            <option value="OVERPAID">Sobrepagada</option>
          </select>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Filter className="h-3 w-3" />
            <button
              onClick={() => {
                setMonthsBack((b) => b + 6);
              }}
              className="rounded border border-zinc-700 px-2 py-1 hover:bg-zinc-800"
            >
              + meses pasados
            </button>
            <button
              onClick={() => setMonthsForward((b) => b + 6)}
              className="rounded border border-zinc-700 px-2 py-1 hover:bg-zinc-800"
            >
              + meses futuros
            </button>
          </div>
        </div>

        <div className="glass-card rounded-xl overflow-hidden">
          {filtered.length === 0 ? (
            <p className="p-6 text-sm text-muted-foreground text-center">
              No hay reservas en los filtros actuales.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wider text-muted-foreground border-b border-zinc-800 bg-zinc-900/40">
                    <th className="py-3 px-4">Check-in / Check-out</th>
                    <th className="px-4">Propiedad</th>
                    <th className="px-4">Titular</th>
                    <th className="px-4">Noches</th>
                    <th className="px-4 text-right">Total</th>
                    <th className="px-4 text-right">Pagado</th>
                    <th className="px-4 text-right">Saldo</th>
                    <th className="px-4">Estado</th>
                    <th className="px-4">Pago</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r) => {
                    const paid = parseFloat(r.amount_paid ?? "0");
                    const balance = parseFloat(r.balance_due ?? r.total_amount);
                    return (
                      <tr
                        key={r.id}
                        className="border-b border-zinc-900/40 hover:bg-zinc-800/20"
                      >
                        <td className="py-3 px-4 whitespace-nowrap">
                          <div>{r.check_in}</div>
                          <div className="text-xs text-muted-foreground">
                            → {r.check_out}
                          </div>
                        </td>
                        <td className="px-4">{r.property_name}</td>
                        <td className="px-4">{r.guest_name}</td>
                        <td className="px-4 text-center">{r.nights}</td>
                        <td className="px-4 text-right font-medium">
                          ${r.total_amount}
                        </td>
                        <td className="px-4 text-right text-emerald-300">
                          ${paid.toFixed(2)}
                        </td>
                        <td className="px-4 text-right">
                          {balance > 0 ? (
                            <span className="text-gold">
                              ${balance.toFixed(2)}
                            </span>
                          ) : (
                            <span className="text-emerald-300">$0.00</span>
                          )}
                        </td>
                        <td className="px-4">
                          <span
                            className={`text-xs px-2 py-0.5 rounded ${STATUS_BADGE[r.status] || ""}`}
                          >
                            {STATUS_LABEL[r.status] || r.status}
                          </span>
                        </td>
                        <td className="px-4">
                          <span
                            className={`text-xs px-2 py-0.5 rounded ${PAYMENT_BADGE[r.payment_status ?? "PENDING"] || ""}`}
                          >
                            {PAYMENT_LABEL[r.payment_status ?? "PENDING"]}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {showCreate && (
          <NewReservationModal
            onClose={() => setShowCreate(false)}
            onCreated={() => {
              setShowCreate(false);
              load();
            }}
          />
        )}
      </motion.div>
    </AppShell>
  );
}

const inputClass =
  "px-3 py-2 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground text-sm focus:border-gold/50 focus:outline-none";

function Stat({
  label,
  value,
  icon: Icon,
  positive,
  highlight,
}: {
  label: string;
  value: number | string;
  icon: React.ComponentType<{ className?: string }>;
  positive?: boolean;
  highlight?: boolean;
}) {
  const colour = highlight
    ? "text-gold"
    : positive
      ? "text-emerald-300"
      : "text-foreground";
  return (
    <div className="glass-card rounded-xl p-4 flex items-center gap-3">
      <Icon className="h-6 w-6 text-gold" />
      <div>
        <p className="text-xs uppercase tracking-wide text-muted-foreground">
          {label}
        </p>
        <p className={`font-serif text-2xl ${colour}`}>{value}</p>
      </div>
    </div>
  );
}

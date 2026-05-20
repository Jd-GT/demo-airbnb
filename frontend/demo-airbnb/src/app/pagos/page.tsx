"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import {
  PaymentItem,
  PaymentTypeValue,
  Reservation,
  createPayment,
  deletePayment,
  downloadPaymentsXlsx,
  fetchPayments,
  fetchReservations,
} from "@/lib/api";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Check,
  Download,
  Loader2,
  Plus,
  ShieldAlert,
  Trash2,
  Wallet,
} from "lucide-react";

const TYPE_LABEL: Record<PaymentTypeValue, string> = {
  ADVANCE: "Anticipo (alojamiento)",
  BALANCE: "Saldo (alojamiento)",
  EXTRA: "Pago extra (daños/servicios)",
  REFUND: "Reembolso",
};

const TYPE_BADGE: Record<PaymentTypeValue, string> = {
  ADVANCE: "bg-blue-500/15 text-blue-300",
  BALANCE: "bg-emerald-500/15 text-emerald-300",
  EXTRA: "bg-purple-500/15 text-purple-300",
  REFUND: "bg-red-500/15 text-red-300",
};

const METHOD_LABEL: Record<PaymentItem["method"], string> = {
  CASH: "Efectivo",
  TRANSFER: "Transferencia",
  OTHER: "Otro",
};

const PAY_STATUS_LABEL: Record<string, string> = {
  PENDING: "Sin pagar",
  PARTIAL: "Pago parcial",
  PAID: "Pagado",
  OVERPAID: "Sobrepagado",
};

export default function PagosPage() {
  const { can, loading: authLoading } = useAuth();
  const canRead = can("finance", "read");
  const canWrite = can("finance", "write");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [payments, setPayments] = useState<PaymentItem[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);

  // form
  const [reservationId, setReservationId] = useState("");
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [amount, setAmount] = useState("");
  const [type, setType] = useState<PaymentTypeValue>("ADVANCE");
  const [method, setMethod] = useState<PaymentItem["method"]>("CASH");
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");

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
      const [pays, resv] = await Promise.all([
        fetchPayments(),
        fetchReservations({ from, to }),
      ]);
      setPayments(pays);
      setReservations(resv);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error cargando pagos");
    } finally {
      setLoading(false);
    }
  }, [canRead]);

  useEffect(() => {
    if (!authLoading) load();
  }, [authLoading, load]);

  const lodgingTotal = useMemo(
    () =>
      payments
        .filter((p) => p.type === "ADVANCE" || p.type === "BALANCE")
        .reduce((acc, p) => acc + parseFloat(p.amount), 0),
    [payments]
  );
  const extrasTotal = useMemo(
    () =>
      payments
        .filter((p) => p.type === "EXTRA")
        .reduce((acc, p) => acc + parseFloat(p.amount), 0),
    [payments]
  );
  const refundsTotal = useMemo(
    () =>
      payments
        .filter((p) => p.type === "REFUND")
        .reduce((acc, p) => acc + parseFloat(p.amount), 0),
    [payments]
  );
  const netTotal = lodgingTotal + extrasTotal - refundsTotal;

  const selectedReservation = useMemo(
    () => reservations.find((r) => r.id === reservationId) || null,
    [reservationId, reservations]
  );

  const balanceDue = selectedReservation
    ? parseFloat(selectedReservation.balance_due ?? "0")
    : 0;
  const isLodgingType = type === "ADVANCE" || type === "BALANCE";
  const isRefundType = type === "REFUND";
  const exceedsBalance =
    isLodgingType &&
    !!amount &&
    parseFloat(amount) > balanceDue + 0.001;
  const exceedsRefund =
    isRefundType &&
    !!selectedReservation &&
    !!amount &&
    parseFloat(amount) > parseFloat(selectedReservation.amount_paid ?? "0") + 0.001;

  // Auto-suggest type based on context
  useEffect(() => {
    if (!selectedReservation) return;
    const balance = parseFloat(selectedReservation.balance_due ?? "0");
    const paid = parseFloat(selectedReservation.amount_paid ?? "0");
    if (balance <= 0.001 && paid > 0 && type !== "EXTRA" && type !== "REFUND") {
      // Already fully paid → default new payments to EXTRA
      setType("EXTRA");
    } else if (paid <= 0.001 && balance > 0 && type === "BALANCE") {
      // Nothing paid → default to ADVANCE
      setType("ADVANCE");
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reservationId]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!reservationId || !amount) {
      setError("Selecciona una reserva y un monto.");
      return;
    }
    if (exceedsBalance) {
      setError(
        `El monto excede el saldo de alojamiento ($${balanceDue.toFixed(2)}). ` +
          `Para cobrar más, cambia el tipo a "Pago extra" o reduce el monto.`
      );
      return;
    }
    if (exceedsRefund) {
      setError(
        `El reembolso excede lo pagado ($${selectedReservation?.amount_paid}).`
      );
      return;
    }
    setCreating(true);
    setError("");
    try {
      const created = await createPayment({
        reservation_id: reservationId,
        date,
        amount,
        type,
        method,
        reference,
        notes,
      });
      setPayments((prev) => [created, ...prev]);
      setAmount("");
      setReference("");
      setNotes("");
      // refresh reservation balances
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error registrando pago");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("¿Eliminar este pago? Se recalcula el estado de la reserva."))
      return;
    try {
      await deletePayment(id);
      setPayments((prev) => prev.filter((p) => p.id !== id));
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error eliminando pago");
    }
  }

  async function handleDownload() {
    try {
      await downloadPaymentsXlsx();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error descargando Excel");
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
          <p className="text-sm">No tienes permisos sobre finance.</p>
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
              Pagos
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Registro manual de pagos. Alojamiento se valida contra el saldo;
              los pagos extras (daños, servicios extras) son ilimitados.
            </p>
          </div>
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-zinc-700 text-sm hover:bg-zinc-800 transition-colors"
          >
            <Download className="h-4 w-4" /> Descargar Excel
          </button>
        </div>

        {error && (
          <p className="text-sm text-red-400 bg-red-500/10 p-3 rounded-lg mb-4">
            {error}
          </p>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <Stat label="Alojamiento neto" value={lodgingTotal - refundsTotal} positive />
          <Stat label="Extras" value={extrasTotal} positive />
          <Stat label="Reembolsos" value={refundsTotal} negative />
          <Stat label="Total entradas" value={netTotal} highlight />
        </div>

        {canWrite && (
          <div className="glass-card rounded-xl p-6 mb-8">
            <div className="flex items-center gap-2 mb-4">
              <Wallet className="h-5 w-5 text-gold" />
              <h2 className="font-serif text-xl font-semibold">
                Registrar pago manual
              </h2>
            </div>

            <form
              onSubmit={handleCreate}
              className="grid grid-cols-1 md:grid-cols-2 gap-3"
            >
              <label className="md:col-span-2 flex flex-col text-xs text-muted-foreground">
                Reserva *
                <select
                  value={reservationId}
                  onChange={(e) => setReservationId(e.target.value)}
                  className={inputClass}
                  required
                >
                  <option value="">Selecciona una reserva…</option>
                  {reservations.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.guest_name} — {r.property_name} ({r.check_in} →{" "}
                      {r.check_out}) — {PAY_STATUS_LABEL[r.payment_status ?? "PENDING"]}
                    </option>
                  ))}
                </select>
              </label>

              {selectedReservation && (
                <div className="md:col-span-2 grid grid-cols-2 md:grid-cols-4 gap-2 rounded-lg border border-zinc-700 bg-zinc-900/40 p-3 text-xs">
                  <ReservationStat
                    label="Total alojamiento"
                    value={parseFloat(selectedReservation.total_amount)}
                  />
                  <ReservationStat
                    label="Pagado"
                    value={parseFloat(selectedReservation.amount_paid ?? "0")}
                    positive
                  />
                  <ReservationStat
                    label="Saldo pendiente"
                    value={balanceDue}
                    highlight={balanceDue > 0}
                  />
                  <ReservationStat
                    label="Extras recibidos"
                    value={parseFloat(selectedReservation.extras_received ?? "0")}
                  />
                </div>
              )}

              <label className="flex flex-col text-xs text-muted-foreground">
                Fecha *
                <input
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  className={inputClass}
                  required
                />
              </label>
              <label className="flex flex-col text-xs text-muted-foreground">
                Monto *
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="100.00"
                  className={`${inputClass} ${
                    exceedsBalance || exceedsRefund
                      ? "border-red-500 focus:border-red-400"
                      : ""
                  }`}
                  required
                />
                {exceedsBalance && (
                  <span className="mt-1 flex items-center gap-1 text-red-300">
                    <AlertTriangle className="h-3 w-3" />
                    Excede el saldo (${balanceDue.toFixed(2)})
                  </span>
                )}
                {exceedsRefund && (
                  <span className="mt-1 flex items-center gap-1 text-red-300">
                    <AlertTriangle className="h-3 w-3" />
                    Excede lo pagado
                  </span>
                )}
              </label>

              <label className="flex flex-col text-xs text-muted-foreground">
                Tipo *
                <select
                  value={type}
                  onChange={(e) => setType(e.target.value as PaymentTypeValue)}
                  className={inputClass}
                >
                  <option value="ADVANCE">Anticipo (alojamiento)</option>
                  <option value="BALANCE">Saldo (alojamiento)</option>
                  <option value="EXTRA">Pago extra (daños/servicios)</option>
                  <option value="REFUND">Reembolso</option>
                </select>
                <span className="mt-1 text-zinc-500">
                  {isLodgingType
                    ? "Reduce el saldo. Máximo: el balance pendiente."
                    : type === "EXTRA"
                      ? "Sin tope. Para daños, servicios extra, etc."
                      : "Devuelve dinero. Máximo: lo que se ha pagado."}
                </span>
              </label>

              <label className="flex flex-col text-xs text-muted-foreground">
                Método *
                <select
                  value={method}
                  onChange={(e) =>
                    setMethod(e.target.value as PaymentItem["method"])
                  }
                  className={inputClass}
                >
                  <option value="CASH">Efectivo</option>
                  <option value="TRANSFER">Transferencia</option>
                  <option value="OTHER">Otro</option>
                </select>
              </label>

              <label className="flex flex-col text-xs text-muted-foreground">
                Referencia (opcional)
                <input
                  type="text"
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                  placeholder="Comprobante, último 4 de cuenta, etc."
                  className={inputClass}
                />
              </label>
              <label className="md:col-span-2 flex flex-col text-xs text-muted-foreground">
                Notas
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  className={inputClass}
                />
              </label>

              <button
                type="submit"
                disabled={
                  creating ||
                  !reservationId ||
                  !amount ||
                  exceedsBalance ||
                  exceedsRefund
                }
                className="md:col-span-2 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-gold text-zinc-900 font-medium hover:bg-gold/90 disabled:opacity-50"
              >
                {creating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                Registrar pago
              </button>
            </form>
          </div>
        )}

        <div className="glass-card rounded-xl p-6">
          <h2 className="font-serif text-xl font-semibold mb-4">
            Historial ({payments.length})
          </h2>
          {payments.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Aún no hay pagos registrados.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground border-b border-zinc-800">
                    <th className="py-2 pr-4">Fecha</th>
                    <th className="pr-4">Reserva</th>
                    <th className="pr-4 text-right">Monto</th>
                    <th className="pr-4">Tipo</th>
                    <th className="pr-4">Método</th>
                    <th className="pr-4">Referencia</th>
                    {canWrite && <th></th>}
                  </tr>
                </thead>
                <tbody>
                  {payments.map((p) => (
                    <tr
                      key={p.id}
                      className="border-b border-zinc-900/40 hover:bg-zinc-800/20"
                    >
                      <td className="py-2 pr-4 whitespace-nowrap">{p.date}</td>
                      <td className="pr-4">{p.reservation_label}</td>
                      <td className="pr-4 text-right font-medium">
                        {p.type === "REFUND" ? "−" : ""}${p.amount}
                      </td>
                      <td className="pr-4">
                        <span
                          className={`text-xs px-2 py-0.5 rounded ${TYPE_BADGE[p.type]}`}
                        >
                          {TYPE_LABEL[p.type]}
                        </span>
                      </td>
                      <td className="pr-4">{METHOD_LABEL[p.method]}</td>
                      <td className="pr-4 text-xs text-muted-foreground">
                        {p.reference || "—"}
                      </td>
                      {canWrite && (
                        <td className="pr-2 text-right">
                          <button
                            onClick={() => handleDelete(p.id)}
                            className="p-1 rounded text-red-400 hover:bg-red-500/10"
                            title="Eliminar"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </motion.div>
    </AppShell>
  );
}

const inputClass =
  "mt-1 w-full px-3 py-2 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none";

function Stat({
  label,
  value,
  positive,
  negative,
  highlight,
}: {
  label: string;
  value: number;
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
    <div className="glass-card rounded-xl p-4">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className={`font-serif text-2xl mt-1 ${colour}`}>
        ${value.toLocaleString("es-CO", { maximumFractionDigits: 2 })}
      </p>
    </div>
  );
}

function ReservationStat({
  label,
  value,
  positive,
  highlight,
}: {
  label: string;
  value: number;
  positive?: boolean;
  highlight?: boolean;
}) {
  const colour = highlight
    ? "text-gold"
    : positive
      ? "text-emerald-300"
      : "text-foreground";
  return (
    <div>
      <p className="text-zinc-500">{label}</p>
      <p className={`font-medium ${colour}`}>
        ${value.toLocaleString("es-CO", { maximumFractionDigits: 2 })}
        {label === "Saldo pendiente" && value <= 0.001 && (
          <Check className="inline h-3 w-3 ml-1 text-emerald-300" />
        )}
      </p>
    </div>
  );
}

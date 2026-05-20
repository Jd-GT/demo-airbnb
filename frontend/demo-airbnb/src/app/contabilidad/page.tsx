"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import {
  AnalyticLineItem,
  CostCenter,
  ExpenseCategory,
  ProfitAndLoss,
  createCostCenter,
  createExpense,
  downloadOccupancyXlsx,
  downloadPnLXlsx,
  fetchAnalyticLines,
  fetchCostCenters,
  fetchProfitAndLoss,
} from "@/lib/api";
import { motion } from "framer-motion";
import {
  BookOpen,
  Download,
  Info,
  Loader2,
  Plus,
  ShieldAlert,
  Wallet,
} from "lucide-react";

const CATEGORY_LABELS: Record<string, string> = {
  INCOME: "Ingreso por alquiler",
  CLEANING_COST: "Costo de limpieza",
  MAINTENANCE: "Mantenimiento / reparación",
  UTILITIES: "Servicios públicos",
  COMMISSION: "Comisión a intermediarios",
  OTHER_EXPENSE: "Otro gasto",
  OTHER_INCOME: "Otro ingreso",
};

const EXPENSE_OPTIONS: { value: ExpenseCategory; label: string }[] = [
  { value: "CLEANING_COST", label: CATEGORY_LABELS.CLEANING_COST },
  { value: "MAINTENANCE", label: CATEGORY_LABELS.MAINTENANCE },
  { value: "UTILITIES", label: CATEGORY_LABELS.UTILITIES },
  { value: "COMMISSION", label: CATEGORY_LABELS.COMMISSION },
  { value: "OTHER_EXPENSE", label: CATEGORY_LABELS.OTHER_EXPENSE },
];

export default function ContabilidadPage() {
  const { can, loading: authLoading } = useAuth();
  const canRead = can("finance", "read");
  const canWrite = can("finance", "write");

  const [year, setYear] = useState(new Date().getFullYear());
  const [accounts, setAccounts] = useState<CostCenter[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<string>("");
  const [pnl, setPnl] = useState<ProfitAndLoss | null>(null);
  const [lines, setLines] = useState<AnalyticLineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // expense form
  const [expenseDate, setExpenseDate] = useState(() =>
    new Date().toISOString().slice(0, 10)
  );
  const [expenseAmount, setExpenseAmount] = useState("");
  const [expenseCategory, setExpenseCategory] = useState<ExpenseCategory>("MAINTENANCE");
  const [expenseDescription, setExpenseDescription] = useState("");
  const [expenseAccountId, setExpenseAccountId] = useState<string>("");
  const [creatingExpense, setCreatingExpense] = useState(false);

  // create cost center inline
  const [showCreateCC, setShowCreateCC] = useState(false);
  const [newCCName, setNewCCName] = useState("");
  const [creatingCC, setCreatingCC] = useState(false);

  const load = useCallback(async () => {
    if (!canRead) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const accs = await fetchCostCenters();
      setAccounts(accs);
      const fromDate = `${year}-01-01`;
      const toDate = `${year}-12-31`;
      const [pnlData, linesData] = await Promise.all([
        fetchProfitAndLoss({
          account_id: selectedAccount || undefined,
          from_date: fromDate,
          to_date: toDate,
        }),
        fetchAnalyticLines({
          account_id: selectedAccount || undefined,
          from: fromDate,
          to: toDate,
        }),
      ]);
      setPnl(pnlData);
      setLines(linesData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error cargando contabilidad");
    } finally {
      setLoading(false);
    }
  }, [canRead, selectedAccount, year]);

  useEffect(() => {
    if (!authLoading) load();
  }, [authLoading, load]);

  const sortedLines = useMemo(
    () => [...lines].sort((a, b) => (a.date < b.date ? 1 : -1)),
    [lines]
  );

  async function handleCreateExpense(e: React.FormEvent) {
    e.preventDefault();
    const target = expenseAccountId || selectedAccount;
    if (!target) {
      setError("Elige a qué centro de costo cargar el gasto.");
      return;
    }
    if (!expenseAmount) {
      setError("Indica el monto del gasto.");
      return;
    }
    setCreatingExpense(true);
    setError("");
    try {
      await createExpense({
        account_id: target,
        date: expenseDate,
        amount: expenseAmount,
        category: expenseCategory,
        description: expenseDescription,
      });
      setExpenseAmount("");
      setExpenseDescription("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error registrando gasto");
    } finally {
      setCreatingExpense(false);
    }
  }

  async function handleCreateCostCenter(e: React.FormEvent) {
    e.preventDefault();
    if (!newCCName.trim()) {
      setError("Pon un nombre al centro de costo.");
      return;
    }
    setCreatingCC(true);
    setError("");
    try {
      const created = await createCostCenter({ name: newCCName.trim() });
      setAccounts((prev) => [...prev, created]);
      setExpenseAccountId(created.id);
      setNewCCName("");
      setShowCreateCC(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error creando centro de costo");
    } finally {
      setCreatingCC(false);
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
          <div>
            <p className="text-sm text-foreground font-medium">
              No tienes permisos de finanzas
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Pídele al propietario que te conceda acceso al módulo
              &quot;finance&quot;.
            </p>
          </div>
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
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div>
            <h1 className="font-serif text-3xl font-semibold text-gold-gradient">
              Contabilidad analítica
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              P&amp;L por centro de costo (propiedad). Ingresos vienen de
              reservas confirmadas; gastos se registran manualmente.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedAccount}
              onChange={(e) => setSelectedAccount(e.target.value)}
              className={inputClass}
            >
              <option value="">Todos los centros</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
            <input
              type="number"
              min="2000"
              max="2100"
              value={year}
              onChange={(e) => setYear(parseInt(e.target.value, 10) || year)}
              className={`${inputClass} w-24`}
            />
            <button
              onClick={() => downloadPnLXlsx(year)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg border border-zinc-700 text-sm hover:bg-zinc-800 transition-colors"
            >
              <Download className="h-4 w-4" /> P&amp;L Excel
            </button>
            <button
              onClick={() => downloadOccupancyXlsx(year)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg border border-zinc-700 text-sm hover:bg-zinc-800 transition-colors"
            >
              <Download className="h-4 w-4" /> Ocupación Excel
            </button>
          </div>
        </div>

        {error && (
          <p className="text-sm text-red-400 bg-red-500/10 p-3 rounded-lg mb-4">
            {error}
          </p>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
          <PnLCard label="Ingresos" value={pnl?.income ?? "0"} positive />
          <PnLCard label="Gastos" value={pnl?.expenses ?? "0"} />
          <PnLCard label="Resultado neto" value={pnl?.net ?? "0"} highlight />
        </div>

        {pnl && Object.keys(pnl.by_category).length > 0 && (
          <div className="glass-card rounded-xl p-6 mb-8">
            <div className="flex items-center gap-2 mb-4">
              <BookOpen className="h-5 w-5 text-gold" />
              <h2 className="font-serif text-xl font-semibold">
                Desglose por categoría
              </h2>
            </div>
            <ul className="divide-y divide-zinc-800">
              {Object.entries(pnl.by_category).map(([category, amount]) => (
                <li
                  key={category}
                  className="py-2 flex items-center justify-between"
                >
                  <span className="text-sm text-muted-foreground">
                    {CATEGORY_LABELS[category] ?? category}
                  </span>
                  <span
                    className={`font-medium ${
                      parseFloat(amount) >= 0 ? "text-emerald-300" : "text-red-300"
                    }`}
                  >
                    ${amount}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {canWrite && (
          <div className="glass-card rounded-xl p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Wallet className="h-5 w-5 text-gold" />
                <h2 className="font-serif text-xl font-semibold">
                  Registrar gasto operativo
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setShowCreateCC((v) => !v)}
                className="flex items-center gap-1 rounded-lg border border-zinc-700 px-3 py-1.5 text-xs hover:bg-zinc-800"
              >
                <Plus className="h-3 w-3" /> Nuevo centro de costo
              </button>
            </div>

            {accounts.length === 0 && (
              <div className="mb-3 flex items-start gap-2 rounded-lg bg-yellow-500/10 p-3 text-xs text-yellow-300">
                <Info className="h-4 w-4 shrink-0 mt-0.5" />
                <p>
                  Aún no hay centros de costo. Cada propiedad nueva crea uno
                  automáticamente, o crea uno general con el botón &quot;Nuevo
                  centro de costo&quot;.
                </p>
              </div>
            )}

            {showCreateCC && (
              <form
                onSubmit={handleCreateCostCenter}
                className="mb-4 flex gap-2"
              >
                <input
                  type="text"
                  value={newCCName}
                  onChange={(e) => setNewCCName(e.target.value)}
                  placeholder="Nombre del centro (ej: Gastos generales)"
                  className={inputClass}
                  required
                />
                <button
                  type="submit"
                  disabled={creatingCC}
                  className="flex items-center gap-1 rounded-lg bg-gold px-3 py-2 text-xs font-medium text-zinc-900 hover:bg-gold/90 disabled:opacity-50"
                >
                  {creatingCC ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Plus className="h-3 w-3" />
                  )}
                  Crear
                </button>
              </form>
            )}

            <form
              onSubmit={handleCreateExpense}
              className="grid grid-cols-1 md:grid-cols-2 gap-3"
            >
              <label className="flex flex-col text-xs text-muted-foreground md:col-span-2">
                Centro de costo *
                <select
                  value={expenseAccountId || selectedAccount}
                  onChange={(e) => setExpenseAccountId(e.target.value)}
                  className={inputClass}
                  required
                >
                  <option value="">Selecciona un centro de costo…</option>
                  {accounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col text-xs text-muted-foreground">
                Fecha *
                <input
                  type="date"
                  value={expenseDate}
                  onChange={(e) => setExpenseDate(e.target.value)}
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
                  value={expenseAmount}
                  onChange={(e) => setExpenseAmount(e.target.value)}
                  placeholder="120.00"
                  className={inputClass}
                  required
                />
              </label>
              <label className="flex flex-col text-xs text-muted-foreground">
                Categoría
                <select
                  value={expenseCategory}
                  onChange={(e) =>
                    setExpenseCategory(e.target.value as ExpenseCategory)
                  }
                  className={inputClass}
                >
                  {EXPENSE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col text-xs text-muted-foreground">
                Descripción
                <input
                  type="text"
                  value={expenseDescription}
                  onChange={(e) => setExpenseDescription(e.target.value)}
                  placeholder="Cambio de bombilla en Apto 301"
                  className={inputClass}
                />
              </label>
              <button
                type="submit"
                disabled={creatingExpense || accounts.length === 0}
                className="md:col-span-2 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-gold text-zinc-900 font-medium hover:bg-gold/90 disabled:opacity-50"
              >
                {creatingExpense ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                Registrar gasto
              </button>
            </form>
          </div>
        )}

        <div className="glass-card rounded-xl p-6">
          <h2 className="font-serif text-xl font-semibold mb-4">
            Movimientos del período ({sortedLines.length})
          </h2>
          {sortedLines.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Sin movimientos en el rango seleccionado.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground border-b border-zinc-800">
                    <th className="py-2 pr-4">Fecha</th>
                    <th className="pr-4">Centro</th>
                    <th className="pr-4">Categoría</th>
                    <th className="pr-4">Descripción</th>
                    <th className="pr-4 text-right">Monto</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedLines.map((line) => (
                    <tr
                      key={line.id}
                      className="border-b border-zinc-900/40 hover:bg-zinc-800/20"
                    >
                      <td className="py-2 pr-4 whitespace-nowrap">
                        {line.date}
                      </td>
                      <td className="pr-4">{line.account_name}</td>
                      <td className="pr-4">
                        {CATEGORY_LABELS[line.category] ?? line.category}
                      </td>
                      <td className="pr-4 text-xs text-muted-foreground">
                        {line.description || "—"}
                      </td>
                      <td
                        className={`pr-4 text-right font-medium ${
                          parseFloat(line.amount) >= 0
                            ? "text-emerald-300"
                            : "text-red-300"
                        }`}
                      >
                        ${line.amount}
                      </td>
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
  "px-3 py-2 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none";

function PnLCard({
  label,
  value,
  positive,
  highlight,
}: {
  label: string;
  value: string;
  positive?: boolean;
  highlight?: boolean;
}) {
  const numeric = parseFloat(value);
  const colour = highlight
    ? numeric >= 0
      ? "text-emerald-300"
      : "text-red-300"
    : positive
    ? "text-emerald-300"
    : "text-red-300";
  return (
    <div className="glass-card rounded-xl p-4">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className={`font-serif text-3xl mt-1 ${colour}`}>${value}</p>
    </div>
  );
}

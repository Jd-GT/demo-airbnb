"use client";

import AppShell from "@/components/app-shell";
import { ErrorCard, LoadingCard } from "@/components/page-feedback";
import { useAsyncData } from "@/hooks/use-async-data";
import { fetchFinanceAnalytics, downloadPropertyReport, shiftMonth, toNumber } from "@/lib/api";
import { motion } from "framer-motion";
import { ArrowUpRight, Download, TrendingDown } from "lucide-react";
import { useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

// TODO [NO_ENDPOINT]: gastos operativos — No existe endpoint ni modelo en el back para este dato. Requiere implementación completa.
const propertyExpenseFallback: Record<string, number> = {
  "Beach House": 18200000,
  "Beach Town": 21400000,
  "Beach Dúplex": 28600000,
  "Santo Domingo": 19200000,
};

// TODO [NO_ENDPOINT]: ingresos por plataforma — No existe endpoint ni modelo en el back para este dato. Requiere implementación completa.
const revenueByPlatformFallback = [
  { name: "Airbnb", value: 152000000, color: "#EF4444" },
  { name: "Booking", value: 118000000, color: "#3B82F6" },
  { name: "Directo", value: 66200000, color: "#10B981" },
];

// TODO [NO_ENDPOINT]: comisiones de plataformas — No existe endpoint ni modelo en el back para este dato. Requiere implementación completa.
const platformCommissionFallback = 27000000;

// TODO [NO_ENDPOINT]: utilidad neta — No existe endpoint ni modelo en el back para este dato. Requiere implementación completa.
const netProfitFallback = 221800000;

// TODO [NO_ENDPOINT]: gastos operativos — No existe endpoint ni modelo en el back para este dato. Requiere implementación completa.
const expenseBreakdownFallback = [
  { category: "Limpieza", amount: 12600000, pct: 22 },
  { category: "Mantenimiento", amount: 8100000, pct: 14 },
  { category: "Comisiones Airbnb", amount: 15200000, pct: 26 },
  { category: "Comisiones Booking", amount: 11800000, pct: 20 },
  { category: "Suministros", amount: 5800000, pct: 10 },
  { category: "Seguros", amount: 4600000, pct: 8 },
];

function formatCOP(value: number) {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatCOPShort(value: number) {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(0)}M`;
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `$${value}`;
}

function formatTrend(current: number, previous: number) {
  if (previous === 0) {
    return {
      label: current === 0 ? "0.0%" : "+100.0%",
      trend: current >= previous ? "up" : "down",
    } as const;
  }

  const delta = ((current - previous) / previous) * 100;
  return {
    label: `${delta >= 0 ? "+" : ""}${delta.toFixed(1)}%`,
    trend: delta >= 0 ? "up" : "down",
  } as const;
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  label?: string;
  payload?: Array<{ color?: string; fill?: string; name?: string; value?: number }>;
}) {
  if (!active || !payload) {
    return null;
  }

  return (
    <div className="glass-card rounded-lg px-4 py-3 shadow-xl">
      <p className="mb-1 text-xs text-muted-foreground">{label}</p>
      {payload.map((entry, index) => (
        <p
          key={`${entry.name ?? "serie"}-${index}`}
          className="text-sm font-medium"
          style={{ color: entry.color || entry.fill }}
        >
          {entry.name}: {formatCOP(entry.value ?? 0)}
        </p>
      ))}
    </div>
  );
}

export default function FinanzasPage() {
  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;
  const previousMonth = shiftMonth(currentYear, currentMonth, -1);
  const [isDownloading, setIsDownloading] = useState(false);

  const { data, error, loading } = useAsyncData(async () => {
    const [analytics, previousAnalytics] = await Promise.all([
      fetchFinanceAnalytics({ year: currentYear, month: currentMonth }),
      fetchFinanceAnalytics({
        year: previousMonth.year,
        month: previousMonth.month,
      }),
    ]);

    const monthlyRevenue = toNumber(analytics.monthly_revenue_total);
    const previousMonthlyRevenue = toNumber(previousAnalytics.monthly_revenue_total);
    const annualRevenue = toNumber(analytics.annual_revenue_total);
    const annualTrend = formatTrend(
      annualRevenue,
      Math.max(annualRevenue - monthlyRevenue, 0),
    );
    const monthlyTrend = formatTrend(monthlyRevenue, previousMonthlyRevenue);

    const revenueByProperty = analytics.revenue_by_property.map((item) => ({
      name: item.name,
      ingresos: toNumber(item.ingresos),
      gastos: propertyExpenseFallback[item.name] ?? 0,
    }));

    const operatingExpenses = expenseBreakdownFallback.reduce(
      (sum, expense) => sum + expense.amount,
      0,
    );
    const expenseTrend = formatTrend(operatingExpenses, operatingExpenses * 0.96);
    const commissionTrend = formatTrend(
      platformCommissionFallback,
      platformCommissionFallback * 1.021,
    );
    const netProfitTrend = formatTrend(netProfitFallback, netProfitFallback * 0.816);

    return {
      revenueByProperty,
      growthData: analytics.monthly_revenue_series.map((item) => ({
        month: item.month,
        value: toNumber(item.ingresos),
      })),
      financeKPIs: [
        {
          title: "Ingresos Totales",
          value: formatCOP(annualRevenue),
          change: annualTrend.label,
          trend: annualTrend.trend,
        },
        {
          title: "Gastos Operativos",
          value: formatCOP(operatingExpenses),
          change: expenseTrend.label,
          trend: expenseTrend.trend,
        },
        {
          title: "Comisiones Plataformas",
          value: formatCOP(platformCommissionFallback),
          change: commissionTrend.label,
          trend: commissionTrend.trend,
        },
        {
          title: "Utilidad Neta",
          value: formatCOP(netProfitFallback),
          change: netProfitTrend.label,
          trend: netProfitTrend.trend,
        },
      ],
      revenueByPlatform: revenueByPlatformFallback,
      expenseBreakdown: expenseBreakdownFallback,
      monthlyTrend,
    };
  }, [currentMonth, currentYear, previousMonth.month, previousMonth.year]);

  return (
    <AppShell>
      <motion.div variants={containerVariants} initial="hidden" animate="show">
        <motion.div variants={itemVariants} className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="font-serif text-3xl font-semibold text-gold-gradient">
              Finanzas
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Analisis financiero detallado de tu cartera
            </p>
          </div>
          <button 
            onClick={async () => {
              const tenantId = localStorage.getItem("tenant_id") || "unknown";
              const reportId = localStorage.getItem("current_report_id") || "default";
              setIsDownloading(true);
              await downloadPropertyReport(tenantId, reportId);
              setIsDownloading(false);
            }}
            disabled={isDownloading}
            className="flex items-center gap-2 rounded-lg border border-gold/20 bg-gold/10 px-4 py-2.5 text-sm font-medium text-gold transition-colors hover:bg-gold/20 disabled:opacity-50 disabled:cursor-not-allowed">
            <Download className="h-4 w-4" />
            {isDownloading ? "Descargando..." : "Exportar Reporte"}
          </button>
        </motion.div>

        {loading && !data ? (
          <LoadingCard
            title="Cargando datos financieros"
            message="Consultando analytics reales y manteniendo solo los fallbacks no soportados por Sprint 1."
          />
        ) : null}

        {!loading && error && !data ? (
          <ErrorCard
            title="No fue posible cargar finanzas"
            message={error}
          />
        ) : null}

        {data ? (
          <>
            <motion.div variants={itemVariants} className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {data.financeKPIs.map((kpi) => (
                <motion.div
                  key={kpi.title}
                  whileHover={{ y: -4 }}
                  className="glass-card glass-card-hover rounded-xl p-5"
                >
                  <div className="mb-2 flex items-center justify-between">
                    <p className="text-xs text-muted-foreground">{kpi.title}</p>
                    <span
                      className={`flex items-center gap-0.5 text-xs font-medium ${
                        kpi.trend === "down" ? "text-red-400" : "text-emerald-400"
                      }`}
                    >
                      {kpi.trend === "down" ? (
                        <TrendingDown className="h-3 w-3" />
                      ) : (
                        <ArrowUpRight className="h-3 w-3" />
                      )}
                      {kpi.change}
                    </span>
                  </div>
                  <p className="text-2xl font-semibold text-foreground">{kpi.value}</p>
                </motion.div>
              ))}
            </motion.div>

            <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
              <motion.div variants={itemVariants} className="glass-card rounded-xl p-6 lg:col-span-2">
                <h2 className="mb-1 font-serif text-xl font-semibold text-foreground">
                  Ingresos por Propiedad
                </h2>
                <p className="mb-6 text-xs text-muted-foreground">
                  Ingresos reales vs gastos operativos fallback
                </p>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.revenueByProperty} barGap={4}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(201,162,39,0.06)" />
                      <XAxis
                        dataKey="name"
                        tick={{ fill: "#8A9A9B", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fill: "#8A9A9B", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={(value) => formatCOPShort(value)}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar
                        dataKey="ingresos"
                        fill="#C9A227"
                        radius={[4, 4, 0, 0]}
                        name="Ingresos"
                        barSize={24}
                      />
                      <Bar
                        dataKey="gastos"
                        fill="#1A4A4B"
                        radius={[4, 4, 0, 0]}
                        name="Gastos"
                        barSize={24}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </motion.div>

              <motion.div variants={itemVariants} className="glass-card rounded-xl p-6">
                <h2 className="mb-1 font-serif text-xl font-semibold text-foreground">
                  Por Plataforma
                </h2>
                <p className="mb-4 text-xs text-muted-foreground">
                  Distribucion de ingresos fallback
                </p>
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={data.revenueByPlatform}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={80}
                        paddingAngle={3}
                        dataKey="value"
                        strokeWidth={0}
                      >
                        {data.revenueByPlatform.map((entry) => (
                          <Cell key={entry.name} fill={entry.color} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-2 space-y-2">
                  {data.revenueByPlatform.map((platform) => (
                    <div key={platform.name} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div
                          className="h-2.5 w-2.5 rounded-full"
                          style={{ backgroundColor: platform.color }}
                        />
                        <span className="text-xs text-muted-foreground">
                          {platform.name}
                        </span>
                      </div>
                      <span className="text-xs font-medium text-foreground">
                        {formatCOPShort(platform.value)}
                      </span>
                    </div>
                  ))}
                </div>
              </motion.div>
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <motion.div variants={itemVariants} className="glass-card rounded-xl p-6">
                <h2 className="mb-1 font-serif text-xl font-semibold text-foreground">
                  Crecimiento
                </h2>
                <p className="mb-6 text-xs text-muted-foreground">
                  Linea temporal de ingresos reales - {currentYear}
                </p>
                <div className="h-[250px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data.growthData}>
                      <defs>
                        <linearGradient id="growthGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#C9A227" stopOpacity={0.2} />
                          <stop offset="100%" stopColor="#C9A227" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(201,162,39,0.06)" />
                      <XAxis
                        dataKey="month"
                        tick={{ fill: "#8A9A9B", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fill: "#8A9A9B", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={(value) => formatCOPShort(value)}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Area
                        type="monotone"
                        dataKey="value"
                        stroke="#C9A227"
                        strokeWidth={2}
                        fill="url(#growthGrad)"
                        name="Ingresos"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </motion.div>

              <motion.div variants={itemVariants} className="glass-card rounded-xl p-6">
                <h2 className="mb-1 font-serif text-xl font-semibold text-foreground">
                  Gastos Operativos
                </h2>
                <p className="mb-6 text-xs text-muted-foreground">
                  Desglose fallback mientras no exista ledger real
                </p>
                <div className="space-y-4">
                  {data.expenseBreakdown.map((expense) => (
                    <div key={expense.category}>
                      <div className="mb-1.5 flex items-center justify-between">
                        <span className="text-sm text-foreground">{expense.category}</span>
                        <span className="text-sm font-medium text-foreground">
                          {formatCOP(expense.amount)}
                        </span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-muted/50">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${expense.pct}%` }}
                          transition={{ duration: 0.8, delay: 0.3 }}
                          className="h-full rounded-full bg-gradient-to-r from-gold/60 to-gold"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            </div>
          </>
        ) : null}
      </motion.div>
    </AppShell>
  );
}

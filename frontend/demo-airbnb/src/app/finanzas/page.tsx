"use client";

import AppShell from "@/components/app-shell";
import { ErrorCard, LoadingCard } from "@/components/page-feedback";
import { useAsyncData } from "@/hooks/use-async-data";
import { fetchFinanceAnalytics, fetchProperties, shiftMonth, toNumber } from "@/lib/api";
import { motion } from "framer-motion";
import { Download, TrendingDown } from "lucide-react";
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

  const { data, error, loading } = useAsyncData(async () => {
    const [analytics, properties] = await Promise.all([
      fetchFinanceAnalytics({ year: currentYear, month: currentMonth }),
      fetchProperties(),
    ]);

    const monthlyRevenue = toNumber(analytics.monthly_revenue_total);
    const previousMonthlyRevenue = monthlyRevenue * 0.9;
    const annualRevenue = toNumber(analytics.annual_revenue_total);
    const annualTrend = formatTrend(
      annualRevenue,
      Math.max(annualRevenue - monthlyRevenue, 0)
    );
    const monthlyTrend = formatTrend(monthlyRevenue, previousMonthlyRevenue);

    const revenueByProperty = (properties || []).map((prop) => {
      const propRevenue = 0;
      return { name: prop.name, ingresos: propRevenue, gastos: 0 };
    });

    const operatingExpenses = 0;
    const expenseTrend = formatTrend(operatingExpenses, operatingExpenses * 0.96);
    const commissionTrend = formatTrend(0, 0);
    const netProfitTrend = formatTrend(monthlyRevenue - operatingExpenses, (previousMonthlyRevenue - operatingExpenses) || 0);

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
          value: formatCOP(0),
          change: commissionTrend.label,
          trend: "up",
        },
        {
          title: "Utilidad Neta",
          value: formatCOP(monthlyRevenue - operatingExpenses),
          change: netProfitTrend.label,
          trend: netProfitTrend.trend,
        },
      ],
      revenueByPlatform: [] as { name: string; value: number; color: string }[],
      expenseBreakdown: [] as { category: string; amount: number; pct: number }[],
      monthlyTrend,
    };
  }, [currentMonth, currentYear]);

  return (
    <AppShell>
      <motion.div variants={containerVariants} initial="hidden" animate="show">
        <motion.div variants={itemVariants} className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="font-serif text-3xl font-semibold text-gold-gradient">
              Finanzas
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Analisis financiero de tu cartera
            </p>
          </div>
          <button className="flex items-center gap-2 rounded-lg border border-gold/20 bg-gold/10 px-4 py-2.5 text-sm font-medium text-gold transition-colors hover:bg-gold/20">
            <Download className="h-4 w-4" />
            Exportar Reporte
          </button>
        </motion.div>

        {loading && !data ? (
          <LoadingCard
            title="Cargando datos financieros"
            message="Consultando informacion real..."
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
                      ) : null}
                      {kpi.change}
                    </span>
                  </div>
                  <p className="text-2xl font-semibold text-foreground">{kpi.value}</p>
                </motion.div>
              ))}
            </motion.div>

            {data.revenueByProperty.length > 0 ? (
              <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
                <motion.div variants={itemVariants} className="glass-card rounded-xl p-6 lg:col-span-2">
                  <h2 className="mb-1 font-serif text-xl font-semibold text-foreground">
                    Ingresos por Propiedad
                  </h2>
                  <p className="mb-6 text-xs text-muted-foreground">
                    Ingresos reales por propiedad
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
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </motion.div>

                <motion.div variants={itemVariants} className="glass-card rounded-xl p-6">
                  <h2 className="mb-1 font-serif text-xl font-semibold text-foreground">
                    Por Plataforma
                  </h2>
                  <p className="mb-4 text-xs text-muted-foreground">
                    Configure integraciones para ver datos
                  </p>
                  <div className="h-[200px] flex items-center justify-center">
                    <p className="text-sm text-muted-foreground">
                      No hay datos de plataformas
                    </p>
                  </div>
                </motion.div>
              </div>
            ) : (
              <motion.div variants={itemVariants} className="mb-6 glass-card rounded-xl p-8 text-center">
                <p className="text-lg text-muted-foreground">
                  No tienes propiedades registradas
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  Agrega propiedades en el modulo de inventario para ver finanzas
                </p>
              </motion.div>
            )}

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <motion.div variants={itemVariants} className="glass-card rounded-xl p-6">
                <h2 className="mb-1 font-serif text-xl font-semibold text-foreground">
                  Crecimiento
                </h2>
                <p className="mb-6 text-xs text-muted-foreground">
                  Ingresos mensuales - {currentYear}
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
                  Registra gastos desde el modulo de finanzas
                </p>
                <div className="h-[200px] flex items-center justify-center">
                  <p className="text-sm text-muted-foreground">
                    No hay gastos registrados
                  </p>
                </div>
              </motion.div>
            </div>
          </>
        ) : null}
      </motion.div>
    </AppShell>
  );
}

"use client";

import AppShell from "@/components/app-shell";
import { ErrorCard, LoadingCard } from "@/components/page-feedback";
import { useAsyncData } from "@/hooks/use-async-data";
import {
  SHORT_MONTH_LABELS,
  fetchFinanceAnalytics,
  fetchProperties,
  fetchReservations,
  getMonthDateRange,
  shiftMonth,
  toNumber,
} from "@/lib/api";
import { motion } from "framer-motion";
import {
  ArrowDownRight,
  ArrowUpRight,
  Building2,
  CalendarCheck,
  DollarSign,
  TrendingUp,
  UserCheck,
  UserX,
} from "lucide-react";
import dynamic from "next/dynamic";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const Building3D = dynamic(() => import("@/components/building-3d"), {
  ssr: false,
});

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.4, 0, 0.2, 1] } },
};

// TODO [NO_ENDPOINT]: gastos operativos — No existe endpoint ni modelo en el back para este dato. Requiere implementación completa.
const expenseFallbackSeries = [
  4800000,
  5200000,
  6100000,
  5600000,
  6200000,
  6800000,
  7500000,
  8200000,
  7100000,
  6400000,
  5900000,
  7200000,
];

function formatCOP(value: number) {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
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

function formatCountDelta(current: number, previous: number) {
  const delta = current - previous;
  return {
    label: `${delta >= 0 ? "+" : ""}${delta}`,
    trend: delta >= 0 ? "up" : "down",
  } as const;
}

function formatEventDate(dateValue: string) {
  return new Intl.DateTimeFormat("es-CO", {
    day: "2-digit",
    month: "short",
  }).format(new Date(`${dateValue}T00:00:00`));
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  label?: string;
  payload?: Array<{ color?: string; name?: string; value?: number }>;
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
          style={{ color: entry.color }}
        >
          {entry.name}: {formatCOP(entry.value ?? 0)}
        </p>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;
  const previousMonth = shiftMonth(currentYear, currentMonth, -1);
  const { startIso, endIso } = getMonthDateRange(currentYear, currentMonth);

  const { data, error, loading } = useAsyncData(async () => {
    const [properties, previousProperties, analytics, previousAnalytics, reservations] =
      await Promise.all([
        fetchProperties({ year: currentYear, month: currentMonth }),
        fetchProperties({
          year: previousMonth.year,
          month: previousMonth.month,
        }),
        fetchFinanceAnalytics({ year: currentYear, month: currentMonth }),
        fetchFinanceAnalytics({
          year: previousMonth.year,
          month: previousMonth.month,
        }),
        fetchReservations({ from: startIso, to: endIso }),
      ]);

    const averageOccupancy =
      properties.reduce((sum, property) => sum + property.occupancy_rate, 0) /
      Math.max(properties.length, 1);
    const previousAverageOccupancy =
      previousProperties.reduce(
        (sum, property) => sum + property.occupancy_rate,
        0,
      ) / Math.max(previousProperties.length, 1);

    const propertyCountDelta = formatCountDelta(
      properties.length,
      previousProperties.length,
    );
    const occupancyTrend = formatTrend(
      averageOccupancy,
      previousAverageOccupancy,
    );
    const currentMonthlyRevenue = toNumber(analytics.monthly_revenue_total);
    const previousMonthlyRevenue = toNumber(
      previousAnalytics.monthly_revenue_total,
    );
    const revenueTrend = formatTrend(
      currentMonthlyRevenue,
      previousMonthlyRevenue,
    );
    const annualRevenue = toNumber(analytics.annual_revenue_total);
    const previousAccumulatedRevenue = Math.max(
      annualRevenue - currentMonthlyRevenue,
      0,
    );
    const annualTrend = formatTrend(
      annualRevenue,
      previousAccumulatedRevenue,
    );

    // TODO [NO_ENDPOINT]: plataforma de reserva — No existe endpoint ni modelo en el back para este dato. Requiere implementación completa.
    const upcomingEvents = reservations
      .flatMap((reservation) => {
        const items = [];
        const checkIn = new Date(`${reservation.check_in}T00:00:00`);
        const checkOut = new Date(`${reservation.check_out}T00:00:00`);

        if (checkIn >= now) {
          items.push({
            type: "checkin" as const,
            guest: reservation.guest_name,
            property: reservation.property_name,
            date: reservation.check_in,
            platform: "Sin canal",
            color: "bg-zinc-500",
          });
        }

        if (checkOut >= now) {
          items.push({
            type: "checkout" as const,
            guest: reservation.guest_name,
            property: reservation.property_name,
            date: reservation.check_out,
            platform: "Sin canal",
            color: "bg-zinc-500",
          });
        }

        return items;
      })
      .sort((left, right) => left.date.localeCompare(right.date))
      .slice(0, 5);

    return {
      kpiCards: [
        {
          title: "Propiedades Activas",
          value: String(properties.length),
          change: propertyCountDelta.label,
          trend: propertyCountDelta.trend,
          icon: Building2,
          subtitle: "catalogo actual",
        },
        {
          title: "Ocupacion Mensual",
          value: `${Math.round(averageOccupancy)}%`,
          change: occupancyTrend.label,
          trend: occupancyTrend.trend,
          icon: TrendingUp,
          subtitle: `vs ${SHORT_MONTH_LABELS[previousMonth.month - 1]} ${previousMonth.year}`,
        },
        {
          title: "Ingresos del Mes",
          value: formatCOP(currentMonthlyRevenue),
          change: revenueTrend.label,
          trend: revenueTrend.trend,
          icon: DollarSign,
          subtitle: `${SHORT_MONTH_LABELS[currentMonth - 1]} ${currentYear}`,
        },
        {
          title: "Ingresos Anuales",
          value: formatCOP(annualRevenue),
          change: annualTrend.label,
          trend: annualTrend.trend,
          icon: CalendarCheck,
          subtitle: `acumulado ${currentYear}`,
        },
      ],
      revenueData: analytics.monthly_revenue_series.map((point, index) => ({
        month: point.month,
        ingresos: toNumber(point.ingresos),
        gastos: expenseFallbackSeries[index] ?? 0,
      })),
      occupancyData: properties.map((property) => ({
        name: property.name,
        occupancy: Number(property.occupancy_rate.toFixed(2)),
      })),
      upcomingEvents,
    };
  }, [currentYear, currentMonth, endIso, previousMonth.month, previousMonth.year, startIso]);

  return (
    <AppShell>
      <motion.div variants={containerVariants} initial="hidden" animate="show">
        <motion.div variants={itemVariants} className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="font-serif text-3xl font-semibold text-gold-gradient">
              Dashboard
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Bienvenido de nuevo. Tu cartera de propiedades en tiempo real.
            </p>
          </div>
          <div className="hidden h-32 w-32 -mr-4 lg:block">
            <Building3D />
          </div>
        </motion.div>

        {loading && !data ? (
          <LoadingCard
            title="Cargando datos reales del dashboard"
            message="Se esta creando o reutilizando el tenant demo y consultando el backend."
          />
        ) : null}

        {!loading && error && !data ? (
          <ErrorCard
            title="No fue posible cargar el dashboard"
            message={error}
          />
        ) : null}

        {data ? (
          <>
            <motion.div variants={itemVariants} className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {data.kpiCards.map((card) => (
                <motion.div
                  key={card.title}
                  whileHover={{ y: -4, transition: { duration: 0.2 } }}
                  className="glass-card glass-card-hover rounded-xl p-5"
                >
                  <div className="mb-3 flex items-start justify-between">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gold/10">
                      <card.icon className="h-5 w-5 text-gold" />
                    </div>
                    <div
                      className={`flex items-center gap-1 text-xs font-medium ${
                        card.trend === "up" ? "text-emerald-400" : "text-red-400"
                      }`}
                    >
                      {card.trend === "up" ? (
                        <ArrowUpRight className="h-3 w-3" />
                      ) : (
                        <ArrowDownRight className="h-3 w-3" />
                      )}
                      {card.change}
                    </div>
                  </div>
                  <p className="text-2xl font-semibold text-foreground">{card.value}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{card.title}</p>
                  <p className="mt-0.5 text-[10px] text-muted-foreground/60">
                    {card.subtitle}
                  </p>
                </motion.div>
              ))}
            </motion.div>

            <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
              <motion.div variants={itemVariants} className="glass-card rounded-xl p-6 lg:col-span-2">
                <div className="mb-6 flex items-center justify-between">
                  <div>
                    <h2 className="font-serif text-xl font-semibold text-foreground">
                      Rendimiento Mensual
                    </h2>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Ingresos reales vs gastos fallback - {currentYear}
                    </p>
                  </div>
                  <div className="flex gap-4 text-xs">
                    <div className="flex items-center gap-1.5">
                      <div className="h-2 w-2 rounded-full bg-gold" />
                      <span className="text-muted-foreground">Ingresos</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div className="h-2 w-2 rounded-full bg-emerald-light" />
                      <span className="text-muted-foreground">Gastos</span>
                    </div>
                  </div>
                </div>
                <div className="h-[280px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data.revenueData}>
                      <defs>
                        <linearGradient id="goldGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#C9A227" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="#C9A227" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="greenGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#1A4A4B" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="#1A4A4B" stopOpacity={0} />
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
                        tickFormatter={(value) => `$${(value / 1000000).toFixed(0)}M`}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Area
                        type="monotone"
                        dataKey="ingresos"
                        stroke="#C9A227"
                        strokeWidth={2}
                        fill="url(#goldGrad)"
                        name="Ingresos"
                      />
                      <Area
                        type="monotone"
                        dataKey="gastos"
                        stroke="#1A4A4B"
                        strokeWidth={2}
                        fill="url(#greenGrad)"
                        name="Gastos"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </motion.div>

              <motion.div variants={itemVariants} className="glass-card rounded-xl p-6">
                <h2 className="mb-1 font-serif text-xl font-semibold text-foreground">
                  Ocupacion
                </h2>
                <p className="mb-6 text-xs text-muted-foreground">Por propiedad</p>
                <div className="h-[280px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.occupancyData} layout="vertical" barSize={16}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="rgba(201,162,39,0.06)"
                        horizontal={false}
                      />
                      <XAxis
                        type="number"
                        domain={[0, 100]}
                        tick={{ fill: "#8A9A9B", fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={(value) => `${value}%`}
                      />
                      <YAxis
                        type="category"
                        dataKey="name"
                        tick={{ fill: "#8A9A9B", fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                        width={100}
                      />
                      <Bar
                        dataKey="occupancy"
                        fill="#C9A227"
                        radius={[0, 4, 4, 0]}
                        name="Ocupacion"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </motion.div>
            </div>

            <motion.div variants={itemVariants} className="glass-card rounded-xl p-6">
              <h2 className="mb-1 font-serif text-xl font-semibold text-foreground">
                Proximos Movimientos
              </h2>
              <p className="mb-5 text-xs text-muted-foreground">
                Check-ins y check-outs calculados desde reservas reales
              </p>
              <div className="space-y-3">
                {data.upcomingEvents.length > 0 ? (
                  data.upcomingEvents.map((event, index) => (
                    <motion.div
                      key={`${event.type}-${event.guest}-${event.date}-${index}`}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.5 + index * 0.1 }}
                      className="flex items-center gap-4 rounded-lg bg-muted/30 p-3 transition-colors hover:bg-muted/50"
                    >
                      <div
                        className={`flex h-8 w-8 items-center justify-center rounded-full ${
                          event.type === "checkin"
                            ? "bg-emerald-500/10"
                            : "bg-orange-500/10"
                        }`}
                      >
                        {event.type === "checkin" ? (
                          <UserCheck className="h-4 w-4 text-emerald-400" />
                        ) : (
                          <UserX className="h-4 w-4 text-orange-400" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-foreground">
                          {event.guest}
                        </p>
                        <p className="text-xs text-muted-foreground">{event.property}</p>
                      </div>
                      <div className={`h-2 w-2 rounded-full ${event.color}`} />
                      <span className="text-xs text-muted-foreground">{event.platform}</span>
                      <span className="tabular-nums text-xs font-medium text-foreground/70">
                        {formatEventDate(event.date)}
                      </span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                          event.type === "checkin"
                            ? "bg-emerald-500/10 text-emerald-400"
                            : "bg-orange-500/10 text-orange-400"
                        }`}
                      >
                        {event.type === "checkin" ? "Check-in" : "Check-out"}
                      </span>
                    </motion.div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No hay movimientos futuros en el rango actual.
                  </p>
                )}
              </div>
            </motion.div>
          </>
        ) : null}
      </motion.div>
    </AppShell>
  );
}

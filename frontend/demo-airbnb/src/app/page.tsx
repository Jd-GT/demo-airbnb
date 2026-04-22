"use client";

import AppShell from "@/components/app-shell";
import { ErrorCard, LoadingCard } from "@/components/page-feedback";
import { useAsyncData } from "@/hooks/use-async-data";
import {
  SHORT_MONTH_LABELS,
  fetchFinanceAnalytics,
  fetchIntegrations,
  fetchProperties,
  fetchReservations,
  getMonthDateRange,
  shiftMonth,
  toNumber,
} from "@/lib/api";
import { motion, useReducedMotion, type Variants } from "framer-motion";
import {
  Activity,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Building2,
  CalendarCheck,
  DollarSign,
  Link2,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  UserCheck,
  UserX,
  Zap,
  type LucideIcon,
} from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import {
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  type RefObject,
  useEffect,
  useMemo,
  useRef,
} from "react";
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

const user = {
  firstName: "Emilamar",
};

type Trend = "up" | "down";

type HeroStat = {
  label: string;
  value: string;
  detail: string;
  icon: LucideIcon;
  trend?: {
    label: string;
    direction: Trend;
  };
};

type QuickAction = {
  title: string;
  eyebrow: string;
  description: string;
  href: string;
  value: string;
  detail: string;
  cta: string;
  icon: LucideIcon;
  accentClass: string;
  iconClass: string;
};

type ProgressMetric = {
  label: string;
  value: string;
  detail: string;
  percentage: number;
  icon: LucideIcon;
};

type UpcomingEvent = {
  type: "checkin" | "checkout";
  guest: string;
  property: string;
  date: string;
  platform: string;
  color: string;
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

function clampPercentage(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function getScrollParent(element: HTMLElement): HTMLElement | Window {
  let parent = element.parentElement;

  while (parent) {
    const style = window.getComputedStyle(parent);

    if (
      /(auto|scroll|overlay)/.test(style.overflowY) &&
      parent.scrollHeight > parent.clientHeight
    ) {
      return parent;
    }

    parent = parent.parentElement;
  }

  return window;
}

function useHeroParallax(
  heroRef: RefObject<HTMLElement | null>,
  disabled: boolean,
) {
  useEffect(() => {
    const element = heroRef.current;

    if (!element) {
      return;
    }

    const reset = () => {
      element.style.setProperty("--hero-bg-y", "0px");
      element.style.setProperty("--hero-fg-y", "0px");
      element.style.setProperty("--hero-depth-y", "0px");
    };

    if (disabled) {
      reset();
      return;
    }

    const mobileQuery = window.matchMedia("(max-width: 767px)");
    const scrollTarget =
      element.closest<HTMLElement>("[data-app-scroll-area]") ??
      getScrollParent(element);
    let frameId: number | null = null;

    const update = () => {
      frameId = null;

      if (mobileQuery.matches) {
        reset();
        return;
      }

      const rect = element.getBoundingClientRect();
      const progress = Math.max(-180, Math.min(180, -rect.top));
      element.style.setProperty("--hero-bg-y", `${progress * 0.18}px`);
      element.style.setProperty("--hero-depth-y", `${progress * 0.1}px`);
      element.style.setProperty("--hero-fg-y", `${progress * -0.04}px`);
    };

    const scheduleUpdate = () => {
      if (frameId !== null) {
        return;
      }

      frameId = window.requestAnimationFrame(update);
    };

    scrollTarget.addEventListener("scroll", scheduleUpdate, { passive: true });
    window.addEventListener("resize", scheduleUpdate);
    mobileQuery.addEventListener("change", scheduleUpdate);
    update();

    return () => {
      if (frameId !== null) {
        window.cancelAnimationFrame(frameId);
      }

      scrollTarget.removeEventListener("scroll", scheduleUpdate);
      window.removeEventListener("resize", scheduleUpdate);
      mobileQuery.removeEventListener("change", scheduleUpdate);
    };
  }, [disabled, heroRef]);
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

function QuickActionCard({
  action,
  index,
  reducedMotion,
}: {
  action: QuickAction;
  index: number;
  reducedMotion: boolean;
}) {
  const Icon = action.icon;
  const cardVariants: Variants = {
    hidden: { opacity: reducedMotion ? 1 : 0, y: reducedMotion ? 0 : 16 },
    show: {
      opacity: 1,
      y: 0,
      transition: {
        delay: reducedMotion ? 0 : index * 0.04,
        duration: reducedMotion ? 0 : 0.45,
        ease: [0.4, 0, 0.2, 1] as const,
      },
    },
  };

  const handlePointerMove = (event: ReactPointerEvent<HTMLAnchorElement>) => {
    if (
      reducedMotion ||
      event.pointerType !== "mouse" ||
      window.matchMedia("(max-width: 767px)").matches
    ) {
      return;
    }

    const element = event.currentTarget;
    const rect = element.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    const rotateX = (0.5 - y) * 8;
    const rotateY = (x - 0.5) * 10;

    element.style.setProperty("--tilt-rotate-x", `${rotateX.toFixed(2)}deg`);
    element.style.setProperty("--tilt-rotate-y", `${rotateY.toFixed(2)}deg`);
    element.style.setProperty("--tilt-glow-x", `${(x * 100).toFixed(0)}%`);
    element.style.setProperty("--tilt-glow-y", `${(y * 100).toFixed(0)}%`);
  };

  const handlePointerLeave = (event: ReactPointerEvent<HTMLAnchorElement>) => {
    const element = event.currentTarget;
    element.style.setProperty("--tilt-rotate-x", "0deg");
    element.style.setProperty("--tilt-rotate-y", "0deg");
    element.style.setProperty("--tilt-glow-x", "50%");
    element.style.setProperty("--tilt-glow-y", "50%");
  };

  return (
    <motion.div
      variants={cardVariants}
      className="[perspective:900px]"
    >
      <Link
        href={action.href}
        onPointerMove={handlePointerMove}
        onPointerLeave={handlePointerLeave}
        className="group relative block h-full min-h-[220px] overflow-hidden rounded-xl border border-border/70 bg-card/75 p-5 shadow-xl shadow-black/10 transition-[transform,border-color,box-shadow] duration-300 ease-out [transform-style:preserve-3d] hover:border-gold/30 hover:shadow-gold/10 motion-reduce:transition-none md:min-h-[236px]"
        style={
          {
            transform:
              "rotateX(var(--tilt-rotate-x, 0deg)) rotateY(var(--tilt-rotate-y, 0deg))",
          } as CSSProperties
        }
      >
        <div
          aria-hidden="true"
          className={`absolute inset-0 bg-gradient-to-br opacity-80 ${action.accentClass}`}
        />
        <div
          aria-hidden="true"
          className="absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100 motion-reduce:transition-none"
          style={{
            background:
              "radial-gradient(circle at var(--tilt-glow-x, 50%) var(--tilt-glow-y, 50%), rgba(232, 212, 139, 0.18), transparent 32%)",
            transform: "translateZ(12px)",
          }}
        />

        <div
          className="relative z-10 flex h-full flex-col"
          style={{ transform: "translateZ(34px)" }}
        >
          <div className="mb-5 flex items-start justify-between gap-3">
            <div className={`flex h-11 w-11 items-center justify-center rounded-lg ${action.iconClass}`}>
              <Icon className="h-5 w-5" />
            </div>
            <span className="rounded-full border border-border/60 bg-background/30 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
              {action.eyebrow}
            </span>
          </div>

          <div className="flex-1">
            <h3 className="text-lg font-semibold text-foreground">{action.title}</h3>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {action.description}
            </p>
          </div>

          <div className="mt-6 flex items-end justify-between gap-4">
            <div>
              <p className="text-xl font-semibold text-foreground">{action.value}</p>
              <p className="text-xs text-muted-foreground">{action.detail}</p>
            </div>
            <span className="flex items-center gap-1 text-sm font-medium text-gold">
              {action.cta}
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 motion-reduce:transition-none" />
            </span>
          </div>
        </div>
      </Link>
    </motion.div>
  );
}

function WelcomeHero({
  stats,
  reducedMotion,
}: {
  stats: HeroStat[];
  reducedMotion: boolean;
}) {
  const heroRef = useRef<HTMLElement | null>(null);
  const heroTextVariants: Variants = {
    hidden: { opacity: reducedMotion ? 1 : 0, y: reducedMotion ? 0 : 18 },
    show: {
      opacity: 1,
      y: 0,
      transition: { duration: reducedMotion ? 0 : 0.5 },
    },
  };
  const heroStatsVariants: Variants = {
    hidden: { opacity: reducedMotion ? 1 : 0, y: reducedMotion ? 0 : 16 },
    show: {
      opacity: 1,
      y: 0,
      transition: { duration: reducedMotion ? 0 : 0.5 },
    },
  };

  useHeroParallax(heroRef, reducedMotion);

  return (
    <section
      ref={heroRef}
      className="relative isolate mb-10 min-h-[430px] overflow-hidden rounded-2xl border border-border/70 bg-card/60 px-6 py-8 shadow-2xl shadow-black/20 [perspective:1200px] [transform-style:preserve-3d] sm:px-8 lg:px-10"
    >
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_15%_15%,rgba(201,162,39,0.20),transparent_26%),radial-gradient(circle_at_84%_20%,rgba(45,212,191,0.11),transparent_28%),linear-gradient(135deg,rgba(9,24,24,0.95),rgba(15,46,47,0.80)_45%,rgba(9,24,24,0.96))]"
        style={{
          transform:
            "translate3d(0, var(--hero-bg-y, 0px), -120px) scale(1.16)",
        }}
      />
      <div
        aria-hidden="true"
        className="absolute -right-24 top-0 h-[130%] w-[54%] -skew-x-12 bg-gradient-to-b from-gold/20 via-gold/5 to-transparent opacity-90"
        style={{
          transform: "translate3d(0, var(--hero-depth-y, 0px), -30px)",
        }}
      />
      <div
        aria-hidden="true"
        className="absolute left-8 top-40 hidden h-36 w-1 rounded-full bg-foreground/20 sm:block"
        style={{ transform: "translateZ(42px)" }}
      >
        <span className="absolute -left-1.5 -top-2 h-4 w-4 rounded bg-foreground/80" />
        <span className="absolute -bottom-2 -left-1.5 h-4 w-4 rounded bg-foreground/80" />
      </div>
      <div
        aria-hidden="true"
        className="absolute right-20 top-24 hidden h-52 w-52 opacity-75 lg:block xl:right-28"
        style={{
          transform: "translate3d(0, var(--hero-fg-y, 0px), 56px)",
        }}
      >
        {reducedMotion ? (
          <div className="flex h-full w-full items-center justify-center rounded-full border border-gold/20 bg-gold/10">
            <Building2 className="h-16 w-16 text-gold" />
          </div>
        ) : (
          <Building3D />
        )}
      </div>
      <div
        className="relative z-10 flex min-h-[374px] flex-col justify-end pt-28 sm:pt-32"
        style={{ transform: "translateZ(24px)" }}
      >
        <motion.div
          variants={heroTextVariants}
          className="flex max-w-3xl flex-col items-start gap-4"
        >
          <span className="inline-flex items-center gap-2 rounded-full border border-gold/20 bg-gold/10 px-3 py-1 text-xs font-medium text-gold">
            <Sparkles className="h-3.5 w-3.5" />
            Panel principal
          </span>
          <h1 className="font-serif text-4xl font-semibold leading-tight text-foreground sm:text-5xl lg:text-6xl">
            Bienvenido,{" "}
            <span className="text-gold-gradient">{user.firstName}</span>
          </h1>
          <p className="max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
            Tienes una vista clara de tu operacion: reservas, ingresos,
            propiedades e integraciones listas para mover el dia con precision.
          </p>
        </motion.div>

        <motion.div
          variants={heroStatsVariants}
          className="mt-10 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
        >
          {stats.map((stat) => {
            const Icon = stat.icon;

            return (
              <div
                key={stat.label}
                className="rounded-xl border border-white/10 bg-background/40 p-5 backdrop-blur-md"
              >
                <div className="mb-4 flex items-start justify-between gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gold/10">
                    <Icon className="h-4 w-4 text-gold" />
                  </div>
                  {stat.trend ? (
                    <span
                      className={`flex items-center gap-1 text-xs font-medium ${
                        stat.trend.direction === "up"
                          ? "text-emerald-400"
                          : "text-red-400"
                      }`}
                    >
                      {stat.trend.direction === "up" ? (
                        <ArrowUpRight className="h-3 w-3" />
                      ) : (
                        <ArrowDownRight className="h-3 w-3" />
                      )}
                      {stat.trend.label}
                    </span>
                  ) : null}
                </div>
                <p className="text-2xl font-semibold text-foreground">{stat.value}</p>
                <p className="mt-1 text-xs text-muted-foreground">{stat.label}</p>
                <p className="mt-0.5 text-[10px] text-muted-foreground/70">
                  {stat.detail}
                </p>
              </div>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
}

export default function DashboardPage() {
  const reducedMotion = Boolean(useReducedMotion());
  const now = useMemo(() => new Date(), []);
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;
  const previousMonth = shiftMonth(currentYear, currentMonth, -1);
  const { startIso, endIso } = getMonthDateRange(currentYear, currentMonth);
  const containerVariants: Variants = {
    hidden: { opacity: reducedMotion ? 1 : 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: reducedMotion ? 0 : 0.08 },
    },
  };
  const itemVariants: Variants = {
    hidden: { opacity: reducedMotion ? 1 : 0, y: reducedMotion ? 0 : 20 },
    show: {
      opacity: 1,
      y: 0,
      transition: {
        duration: reducedMotion ? 0 : 0.5,
        ease: [0.4, 0, 0.2, 1] as const,
      },
    },
  };

  const { data, error, loading } = useAsyncData(async () => {
    const [
      properties,
      previousProperties,
      analytics,
      previousAnalytics,
      reservations,
      integrations,
    ] = await Promise.all([
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
      fetchIntegrations().catch(() => []),
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
    const connectedIntegrations = integrations.filter(
      (integration) => integration.status === "connected",
    );
    const integrationIssues = integrations.filter(
      (integration) => integration.status === "error",
    );
    const totalIntegrations = integrations.length;
    const integrationStatusLabel = `${connectedIntegrations.length}/${totalIntegrations}`;
    const integrationHealth =
      totalIntegrations === 0
        ? 0
        : (connectedIntegrations.length / totalIntegrations) * 100;
    const integrationSummaryDetail =
      totalIntegrations === 0
        ? "sin conexiones cargadas"
        : integrationIssues.length > 0
          ? `${integrationIssues.length} requiere atencion`
          : "ecosistema sincronizado";
    const integrationProgressDetail =
      totalIntegrations === 0
        ? "sin conexiones cargadas"
        : integrationIssues.length > 0
          ? "hay conexiones por revisar"
          : "sin alertas activas";
    const todayStart = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate(),
    );

    // TODO [NO_ENDPOINT]: plataforma de reserva - No existe endpoint ni modelo en el back para este dato. Requiere implementacion completa.
    const upcomingEvents: UpcomingEvent[] = reservations
      .flatMap((reservation) => {
        const items: UpcomingEvent[] = [];
        const checkIn = new Date(`${reservation.check_in}T00:00:00`);
        const checkOut = new Date(`${reservation.check_out}T00:00:00`);

        if (checkIn >= todayStart) {
          items.push({
            type: "checkin",
            guest: reservation.guest_name,
            property: reservation.property_name,
            date: reservation.check_in,
            platform: "Sin canal",
            color: "bg-zinc-500",
          });
        }

        if (checkOut >= todayStart) {
          items.push({
            type: "checkout",
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

    const activityEvents: UpcomingEvent[] = reservations
      .flatMap((reservation) => [
        {
          type: "checkin" as const,
          guest: reservation.guest_name,
          property: reservation.property_name,
          date: reservation.check_in,
          platform: "Sin canal",
          color: "bg-zinc-500",
        },
        {
          type: "checkout" as const,
          guest: reservation.guest_name,
          property: reservation.property_name,
          date: reservation.check_out,
          platform: "Sin canal",
          color: "bg-zinc-500",
        },
      ])
      .sort((left, right) => right.date.localeCompare(left.date))
      .slice(0, 5);

    const revenueData = analytics.monthly_revenue_series.map((point, index) => ({
      month: point.month,
      ingresos: toNumber(point.ingresos),
      gastos: expenseFallbackSeries[index] ?? 0,
    }));
    const bestMonthlyRevenue = Math.max(
      ...revenueData.map((point) => point.ingresos),
      currentMonthlyRevenue,
      1,
    );

    const heroStats: HeroStat[] = [
      {
        label: "Ingresos del mes",
        value: formatCOPShort(currentMonthlyRevenue),
        detail: `${SHORT_MONTH_LABELS[currentMonth - 1]} ${currentYear}`,
        icon: DollarSign,
        trend: {
          label: revenueTrend.label,
          direction: revenueTrend.trend,
        },
      },
      {
        label: "Ocupacion promedio",
        value: `${Math.round(averageOccupancy)}%`,
        detail: `vs ${SHORT_MONTH_LABELS[previousMonth.month - 1]} ${previousMonth.year}`,
        icon: TrendingUp,
        trend: {
          label: occupancyTrend.label,
          direction: occupancyTrend.trend,
        },
      },
      {
        label: "Propiedades activas",
        value: String(properties.length),
        detail: "catalogo actual",
        icon: Building2,
        trend: {
          label: propertyCountDelta.label,
          direction: propertyCountDelta.trend,
        },
      },
      {
        label: "Conexiones listas",
        value: integrationStatusLabel,
        detail: integrationSummaryDetail,
        icon: ShieldCheck,
      },
    ];

    const quickActions: QuickAction[] = [
      {
        title: "Calendario",
        eyebrow: "Operar",
        description: "Revisa entradas, salidas y disponibilidad de todas las propiedades.",
        href: "/calendario",
        value: `${upcomingEvents.length}`,
        detail: "movimientos proximos",
        cta: "Abrir",
        icon: CalendarCheck,
        accentClass: "from-sky-500/20 via-sky-500/5 to-transparent",
        iconClass: "bg-sky-500/10 text-sky-300",
      },
      {
        title: "Propiedades",
        eyebrow: "Portafolio",
        description: "Administra capacidad, ubicacion, rendimiento y estado del inventario.",
        href: "/propiedades",
        value: String(properties.length),
        detail: "activos publicados",
        cta: "Gestionar",
        icon: Building2,
        accentClass: "from-gold/20 via-gold/5 to-transparent",
        iconClass: "bg-gold/10 text-gold",
      },
      {
        title: "Finanzas",
        eyebrow: "Control",
        description: "Consulta ingresos, gastos y utilidad con datos consolidados del mes.",
        href: "/finanzas",
        value: formatCOPShort(currentMonthlyRevenue),
        detail: "ingreso mensual",
        cta: "Analizar",
        icon: DollarSign,
        accentClass: "from-emerald-500/20 via-emerald-500/5 to-transparent",
        iconClass: "bg-emerald-500/10 text-emerald-300",
      },
      {
        title: "Integraciones",
        eyebrow: "Sincronizar",
        description: "Supervisa canales, pagos y servicios conectados a la operacion.",
        href: "/integraciones",
        value: integrationStatusLabel,
        detail: totalIntegrations === 0 ? "sin datos" : "conectadas",
        cta: "Revisar",
        icon: Link2,
        accentClass: "from-violet-500/20 via-violet-500/5 to-transparent",
        iconClass: "bg-violet-500/10 text-violet-300",
      },
    ];

    const progressMetrics: ProgressMetric[] = [
      {
        label: "Ocupacion del portafolio",
        value: `${Math.round(averageOccupancy)}%`,
        detail: "promedio ponderado del mes actual",
        percentage: clampPercentage(averageOccupancy),
        icon: Activity,
      },
      {
        label: "Ritmo de ingresos",
        value: formatCOPShort(currentMonthlyRevenue),
        detail: "comparado con el mejor mes del ano",
        percentage: clampPercentage((currentMonthlyRevenue / bestMonthlyRevenue) * 100),
        icon: BarChart3,
      },
      {
        label: "Salud de integraciones",
        value: integrationStatusLabel,
        detail: integrationProgressDetail,
        percentage: clampPercentage(integrationHealth),
        icon: Zap,
      },
    ];

    return {
      heroStats,
      quickActions,
      progressMetrics,
      revenueData,
      occupancyData: properties.map((property) => ({
        name: property.name,
        occupancy: Number(property.occupancy_rate.toFixed(2)),
      })),
      upcomingEvents,
      activityEvents,
    };
  }, [
    currentYear,
    currentMonth,
    endIso,
    now,
    previousMonth.month,
    previousMonth.year,
    startIso,
  ]);

  return (
    <AppShell>
      <motion.div variants={containerVariants} initial="hidden" animate="show">
        <WelcomeHero
          stats={data?.heroStats ?? []}
          reducedMotion={reducedMotion}
        />

        {loading && !data ? (
          <motion.div variants={itemVariants} className="mb-8">
            <LoadingCard
              title="Cargando datos reales del dashboard"
              message="Se esta creando o reutilizando el tenant demo y consultando el backend."
            />
          </motion.div>
        ) : null}

        {!loading && error && !data ? (
          <motion.div variants={itemVariants} className="mb-8">
            <ErrorCard
              title="No fue posible cargar el dashboard"
              message={error}
            />
          </motion.div>
        ) : null}

        {data ? (
          <>
            <motion.section variants={itemVariants} className="mb-10">
              <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
                <div>
                  <h2 className="font-serif text-2xl font-semibold text-foreground">
                    Accesos rapidos
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Las acciones principales del sistema, listas para entrar.
                  </p>
                </div>
                <p className="text-xs text-muted-foreground">
                  Datos del mes actual
                </p>
              </div>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 2xl:grid-cols-4">
                {data.quickActions.map((action, index) => (
                  <QuickActionCard
                    key={action.title}
                    action={action}
                    index={index}
                    reducedMotion={reducedMotion}
                  />
                ))}
              </div>
            </motion.section>

            <div className="mb-10 grid grid-cols-1 gap-6 xl:grid-cols-[1.1fr_0.9fr]">
              <motion.section variants={itemVariants} className="glass-card rounded-xl p-6">
                <div className="mb-6 flex items-center justify-between gap-4">
                  <div>
                    <h2 className="font-serif text-xl font-semibold text-foreground">
                      Progreso del mes
                    </h2>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Resumen operativo con senales clave.
                    </p>
                  </div>
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gold/10">
                    <RefreshCw className="h-5 w-5 text-gold" />
                  </div>
                </div>

                <div className="space-y-5">
                  {data.progressMetrics.map((metric) => {
                    const Icon = metric.icon;

                    return (
                      <div key={metric.label}>
                        <div className="mb-2 flex items-center justify-between gap-4">
                          <div className="flex min-w-0 items-center gap-3">
                            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted/60">
                              <Icon className="h-4 w-4 text-gold" />
                            </div>
                            <div className="min-w-0">
                              <p className="truncate text-sm font-medium text-foreground">
                                {metric.label}
                              </p>
                              <p className="truncate text-xs text-muted-foreground">
                                {metric.detail}
                              </p>
                            </div>
                          </div>
                          <span className="shrink-0 text-sm font-semibold text-foreground">
                            {metric.value}
                          </span>
                        </div>
                        <div className="h-2 overflow-hidden rounded-full bg-muted">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-gold to-emerald-300 transition-[width] duration-700 motion-reduce:transition-none"
                            style={{ width: `${metric.percentage}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </motion.section>

              <motion.section variants={itemVariants} className="glass-card rounded-xl p-6">
                <div className="mb-5 flex items-center justify-between gap-4">
                  <div>
                    <h2 className="font-serif text-xl font-semibold text-foreground">
                      Actividad reciente
                    </h2>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Ultimos check-ins y check-outs calculados desde reservas reales.
                    </p>
                  </div>
                  <Link
                    href="/calendario"
                    className="rounded-md border border-gold/20 bg-gold/10 px-3 py-2 text-xs font-medium text-gold transition-colors hover:bg-gold/20 motion-reduce:transition-none"
                  >
                    Ver calendario
                  </Link>
                </div>

                <div className="space-y-3">
                  {data.activityEvents.length > 0 ? (
                    data.activityEvents.map((event, index) => (
                      <motion.div
                        key={`${event.type}-${event.guest}-${event.date}-${index}`}
                        initial={
                          reducedMotion ? { opacity: 1, x: 0 } : { opacity: 0, x: -10 }
                        }
                        animate={{ opacity: 1, x: 0 }}
                        transition={{
                          delay: reducedMotion ? 0 : 0.25 + index * 0.06,
                          duration: reducedMotion ? 0 : 0.3,
                        }}
                        className="flex items-center gap-4 rounded-lg bg-muted/30 p-3 transition-colors hover:bg-muted/50 motion-reduce:transition-none"
                      >
                        <div
                          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${
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
                          <p className="truncate text-xs text-muted-foreground">
                            {event.property}
                          </p>
                        </div>
                        <div className={`hidden h-2 w-2 rounded-full sm:block ${event.color}`} />
                        <span className="hidden text-xs text-muted-foreground sm:inline">
                          {event.platform}
                        </span>
                        <span className="shrink-0 tabular-nums text-xs font-medium text-foreground/70">
                          {formatEventDate(event.date)}
                        </span>
                        <span
                          className={`hidden rounded-full px-2 py-0.5 text-[10px] font-medium sm:inline ${
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
                    <p className="rounded-lg bg-muted/30 p-4 text-sm text-muted-foreground">
                      No hay actividad registrada en el rango actual.
                    </p>
                  )}
                </div>
              </motion.section>
            </div>

            <div className="mb-10 grid grid-cols-1 gap-6 lg:grid-cols-3">
              <motion.section variants={itemVariants} className="glass-card rounded-xl p-6 lg:col-span-2">
                <div className="mb-6 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                  <div>
                    <h2 className="font-serif text-xl font-semibold text-foreground">
                      Rendimiento mensual
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
                        tickFormatter={(value) => `$${(Number(value) / 1000000).toFixed(0)}M`}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Area
                        type="monotone"
                        dataKey="ingresos"
                        stroke="#C9A227"
                        strokeWidth={2}
                        fill="url(#goldGrad)"
                        name="Ingresos"
                        isAnimationActive={!reducedMotion}
                      />
                      <Area
                        type="monotone"
                        dataKey="gastos"
                        stroke="#1A4A4B"
                        strokeWidth={2}
                        fill="url(#greenGrad)"
                        name="Gastos"
                        isAnimationActive={!reducedMotion}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </motion.section>

              <motion.section variants={itemVariants} className="glass-card rounded-xl p-6">
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
                        isAnimationActive={!reducedMotion}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </motion.section>
            </div>
          </>
        ) : null}
      </motion.div>
    </AppShell>
  );
}

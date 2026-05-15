"use client";

import AppShell from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { NewReservationModal } from "@/components/new-reservation-modal";
import { ErrorCard, LoadingCard } from "@/components/page-feedback";
import { useAsyncData } from "@/hooks/use-async-data";
import {
  LONG_MONTH_LABELS,
  fetchReservations,
  getMonthDateRange,
  shiftMonth,
  toNumber,
} from "@/lib/api";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Plus,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";

type Booking = {
  id: string;
  guest: string;
  property: string;
  platform: "airbnb" | "booking" | "directo" | "blocked";
  startDate: Date;
  endDate: Date;
  price: number;
  status: "confirmed" | "pending" | "blocked";
};

const platformColors: Record<
  Booking["platform"],
  { bg: string; text: string; dot: string; label: string }
> = {
  airbnb: {
    bg: "bg-red-500/15",
    text: "text-red-400",
    dot: "bg-red-500",
    label: "Airbnb",
  },
  booking: {
    bg: "bg-blue-500/15",
    text: "text-blue-400",
    dot: "bg-blue-500",
    label: "Booking",
  },
  directo: {
    bg: "bg-emerald-500/15",
    text: "text-emerald-400",
    dot: "bg-emerald-500",
    label: "Directo",
  },
  blocked: {
    bg: "bg-zinc-500/15",
    text: "text-zinc-400",
    dot: "bg-zinc-500",
    label: "Bloqueado",
  },
};

const weekdays = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"];

function formatCOP(value: number) {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDateLabel(value: Date) {
  return new Intl.DateTimeFormat("es-CO", {
    day: "2-digit",
    month: "short",
  }).format(value);
}

function dayStart(year: number, monthIndex: number, day: number) {
  return new Date(year, monthIndex, day);
}

export default function CalendarioPage() {
  const { can } = useAuth();
  const canWrite = can("booking", "write");
  const today = new Date();
  const [currentMonth, setCurrentMonth] = useState(today.getMonth());
  const [currentYear, setCurrentYear] = useState(today.getFullYear());
  const [selectedBooking, setSelectedBooking] = useState<Booking | null>(null);
  const [viewMode, setViewMode] = useState<"month" | "week">("month");
  const [showNewModal, setShowNewModal] = useState<string | null>(null); // ISO date or "open"

  const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
  const firstDayOfMonth = (new Date(currentYear, currentMonth, 1).getDay() + 6) % 7;
  const monthRange = getMonthDateRange(currentYear, currentMonth + 1);

  const { data, error, loading, reload } = useAsyncData(async () => {
    const reservations = await fetchReservations({
      from: monthRange.startIso,
      to: monthRange.endIso,
    });

    // TODO [NO_ENDPOINT]: plataforma de reserva — No existe endpoint ni modelo en el back para este dato. Requiere implementación completa.
    // TODO [NO_ENDPOINT]: bloqueos manuales de calendario — No existe endpoint ni modelo en el back para este dato. Requiere implementación completa.
    return reservations.map<Booking>((reservation) => ({
      id: reservation.id,
      guest: reservation.guest_name,
      property: reservation.property_name,
      platform: "directo",
      startDate: new Date(`${reservation.check_in}T00:00:00`),
      endDate: new Date(`${reservation.check_out}T00:00:00`),
      price: toNumber(reservation.total_amount),
      status:
        reservation.status === "CONFIRMED"
          ? "confirmed"
          : reservation.status === "DRAFT"
            ? "pending"
            : "blocked",
    }));
  }, [currentMonth, currentYear, monthRange.endIso, monthRange.startIso]);

  const bookings = data ?? [];

  const prevMonth = () => {
    if (currentMonth === 0) {
      const previous = shiftMonth(currentYear, currentMonth + 1, -1);
      setCurrentMonth(previous.month - 1);
      setCurrentYear(previous.year);
      return;
    }
    setCurrentMonth((value) => value - 1);
  };

  const nextMonth = () => {
    if (currentMonth === 11) {
      const next = shiftMonth(currentYear, currentMonth + 1, 1);
      setCurrentMonth(next.month - 1);
      setCurrentYear(next.year);
      return;
    }
    setCurrentMonth((value) => value + 1);
  };

  const overlaps = useMemo(() => {
    const overlapDays = new Set<number>();

    for (let leftIndex = 0; leftIndex < bookings.length; leftIndex += 1) {
      for (let rightIndex = leftIndex + 1; rightIndex < bookings.length; rightIndex += 1) {
        const left = bookings[leftIndex];
        const right = bookings[rightIndex];

        if (
          left.property !== right.property ||
          left.startDate >= right.endDate ||
          right.startDate >= left.endDate
        ) {
          continue;
        }

        const overlapStart = new Date(
          Math.max(left.startDate.getTime(), right.startDate.getTime()),
        );
        const overlapEnd = new Date(
          Math.min(left.endDate.getTime(), right.endDate.getTime()),
        );

        for (
          let cursor = new Date(overlapStart);
          cursor < overlapEnd;
          cursor.setDate(cursor.getDate() + 1)
        ) {
          if (
            cursor.getMonth() === currentMonth &&
            cursor.getFullYear() === currentYear
          ) {
            overlapDays.add(cursor.getDate());
          }
        }
      }
    }

    return overlapDays;
  }, [bookings, currentMonth, currentYear]);

  const getBookingsForDay = (day: number) => {
    const target = dayStart(currentYear, currentMonth, day);
    return bookings.filter(
      (booking) => target >= booking.startDate && target < booking.endDate,
    );
  };

  return (
    <AppShell>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="font-serif text-3xl font-semibold text-gold-gradient">
              Calendario
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Vista unificada de todas las reservas y disponibilidad
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex rounded-lg bg-muted/50 p-0.5">
              <button
                onClick={() => setViewMode("month")}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  viewMode === "month"
                    ? "bg-gold/20 text-gold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Mensual
              </button>
              <button
                onClick={() => setViewMode("week")}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  viewMode === "week"
                    ? "bg-gold/20 text-gold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Semanal
              </button>
            </div>
            {canWrite && (
              <button
                onClick={() => setShowNewModal("open")}
                className="flex items-center gap-2 rounded-lg bg-gold px-4 py-2 text-sm font-medium text-zinc-900 transition-colors hover:bg-gold/90"
              >
                <Plus className="h-4 w-4" />
                Nueva reserva
              </button>
            )}
          </div>
        </div>

        {showNewModal && (
          <NewReservationModal
            initialCheckIn={showNewModal !== "open" ? showNewModal : undefined}
            onClose={() => setShowNewModal(null)}
            onCreated={() => {
              setShowNewModal(null);
              reload();
            }}
          />
        )}

        {loading && !data ? (
          <LoadingCard
            title="Cargando reservas reales"
            message="Consultando el rango actual del calendario contra el backend."
          />
        ) : null}

        {!loading && error && !data ? (
          <ErrorCard
            title="No fue posible cargar el calendario"
            message={error}
          />
        ) : null}

        {data ? (
          <>
            <div className="mb-6 flex flex-wrap gap-4">
              {Object.entries(platformColors).map(([key, value]) => (
                <div key={key} className="flex items-center gap-2">
                  <div className={`h-2.5 w-2.5 rounded-full ${value.dot}`} />
                  <span className="text-xs text-muted-foreground">{value.label}</span>
                </div>
              ))}
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-3 w-3 text-red-400" />
                <span className="text-xs text-red-400">Sobreposicion</span>
              </div>
            </div>

            <div className="mb-6 flex items-center justify-between">
              <button
                onClick={prevMonth}
                className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <AnimatePresence mode="wait">
                <motion.h2
                  key={`${currentMonth}-${currentYear}`}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  transition={{ duration: 0.2 }}
                  className="font-serif text-2xl font-semibold text-foreground"
                >
                  {LONG_MONTH_LABELS[currentMonth]} {currentYear}
                </motion.h2>
              </AnimatePresence>
              <button
                onClick={nextMonth}
                className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>

            <motion.div
              key={`${currentMonth}-${currentYear}`}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3 }}
              className="glass-card overflow-hidden rounded-xl"
            >
              <div className="grid grid-cols-7 border-b border-border">
                {weekdays.map((weekday) => (
                  <div
                    key={weekday}
                    className="py-3 text-center text-xs font-medium uppercase tracking-wider text-muted-foreground"
                  >
                    {weekday}
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-7">
                {Array.from({ length: firstDayOfMonth }).map((_, index) => (
                  <div
                    key={`empty-${index}`}
                    className="min-h-[100px] border-b border-r border-border/50 bg-muted/10"
                  />
                ))}

                {Array.from({ length: daysInMonth }).map((_, index) => {
                  const day = index + 1;
                  const dayBookings = getBookingsForDay(day);
                  const hasOverlap = overlaps.has(day);
                  const isToday =
                    day === today.getDate() &&
                    currentMonth === today.getMonth() &&
                    currentYear === today.getFullYear();

                  return (
                    <div
                      key={day}
                      className={`relative min-h-[100px] border-b border-r border-border/50 p-1.5 transition-colors hover:bg-muted/20 ${
                        hasOverlap ? "bg-red-500/5" : ""
                      }`}
                    >
                      <div className="mb-1 flex items-center justify-between">
                        <span
                          className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium ${
                            isToday
                              ? "bg-gold text-primary-foreground"
                              : "text-muted-foreground"
                          }`}
                        >
                          {day}
                        </span>
                        {hasOverlap ? (
                          <AlertTriangle className="h-3 w-3 animate-pulse text-red-400" />
                        ) : null}
                      </div>
                      <div className="space-y-0.5">
                        {dayBookings.slice(0, 3).map((booking) => {
                          const palette = platformColors[booking.platform];
                          return (
                            <button
                              key={booking.id}
                              onClick={() => setSelectedBooking(booking)}
                              className={`w-full truncate rounded px-1.5 py-0.5 text-left text-[10px] font-medium transition-opacity hover:opacity-80 ${palette.bg} ${palette.text}`}
                            >
                              {booking.guest || "Bloqueado"}
                            </button>
                          );
                        })}
                        {dayBookings.length > 3 ? (
                          <p className="text-center text-[10px] text-muted-foreground">
                            +{dayBookings.length - 3} mas
                          </p>
                        ) : null}
                      </div>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          </>
        ) : null}

        <AnimatePresence>
          {selectedBooking ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
              onClick={() => setSelectedBooking(null)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                onClick={(event) => event.stopPropagation()}
                className="glass-card mx-4 w-full max-w-sm rounded-xl p-6 shadow-2xl"
              >
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="font-serif text-lg font-semibold text-foreground">
                    Detalle de Reserva
                  </h3>
                  <button
                    onClick={() => setSelectedBooking(null)}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <div className="space-y-3">
                  <div>
                    <p className="text-xs text-muted-foreground">Huesped</p>
                    <p className="text-sm font-medium text-foreground">
                      {selectedBooking.guest || "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Propiedad</p>
                    <p className="text-sm font-medium text-foreground">
                      {selectedBooking.property}
                    </p>
                  </div>
                  <div className="flex gap-4">
                    <div>
                      <p className="text-xs text-muted-foreground">Plataforma</p>
                      <div className="mt-0.5 flex items-center gap-1.5">
                        <div
                          className={`h-2 w-2 rounded-full ${
                            platformColors[selectedBooking.platform].dot
                          }`}
                        />
                        <p className="text-sm font-medium text-foreground">
                          {platformColors[selectedBooking.platform].label}
                        </p>
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Precio</p>
                      <p className="text-sm font-medium text-gold">
                        {selectedBooking.price > 0
                          ? formatCOP(selectedBooking.price)
                          : "—"}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-4">
                    <div>
                      <p className="text-xs text-muted-foreground">Fechas</p>
                      <p className="text-sm font-medium text-foreground">
                        {formatDateLabel(selectedBooking.startDate)} -{" "}
                        {formatDateLabel(
                          new Date(
                            selectedBooking.endDate.getFullYear(),
                            selectedBooking.endDate.getMonth(),
                            selectedBooking.endDate.getDate() - 1,
                          ),
                        )}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Estado</p>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          selectedBooking.status === "confirmed"
                            ? "bg-emerald-500/10 text-emerald-400"
                            : selectedBooking.status === "pending"
                              ? "bg-yellow-500/10 text-yellow-400"
                              : "bg-zinc-500/10 text-zinc-400"
                        }`}
                      >
                        {selectedBooking.status === "confirmed"
                          ? "Confirmada"
                          : selectedBooking.status === "pending"
                            ? "Pendiente"
                            : "Bloqueada"}
                      </span>
                    </div>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </motion.div>
    </AppShell>
  );
}

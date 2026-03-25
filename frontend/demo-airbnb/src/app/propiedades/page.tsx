"use client";

import AppShell from "@/components/app-shell";
import { ErrorCard, LoadingCard } from "@/components/page-feedback";
import { useAsyncData } from "@/hooks/use-async-data";
import { fetchProperties, toNumber } from "@/lib/api";
import { motion } from "framer-motion";
import {
  Bath,
  BedDouble,
  DollarSign,
  Eye,
  MapPin,
  MoreHorizontal,
  Pencil,
  Search,
  Users,
} from "lucide-react";
import { useMemo, useState } from "react";

type PropertyRow = {
  id: string;
  name: string;
  location: string;
  status: "active" | "inactive";
  monthlyRevenue: number;
  occupancy: number;
  image: string;
  capacity: number;
  floor: string;
  rooms: number;
  bathrooms: number;
};

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 },
};

// TODO [NO_ENDPOINT]: metadatos visuales de propiedad — No existe endpoint ni modelo en el back para este dato. Requiere implementación completa.
const propertyPresentationFallback: Record<
  string,
  Pick<PropertyRow, "image" | "floor" | "rooms" | "bathrooms" | "status">
> = {
  "Beach House": {
    image: "🏖️",
    floor: "3er piso",
    rooms: 1,
    bathrooms: 2,
    status: "active",
  },
  "Beach Town": {
    image: "🌴",
    floor: "2do piso",
    rooms: 2,
    bathrooms: 2,
    status: "active",
  },
  "Beach Dúplex": {
    image: "🏢",
    floor: "7mo y 8vo piso",
    rooms: 3,
    bathrooms: 3,
    status: "active",
  },
  "Santo Domingo": {
    image: "⛪",
    floor: "2do piso",
    rooms: 2,
    bathrooms: 2,
    status: "active",
  },
};

function formatCOP(value: number) {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export default function PropiedadesPage() {
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<"all" | "active" | "inactive">(
    "all",
  );
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;

  const { data, error, loading } = useAsyncData(async () => {
    const properties = await fetchProperties({
      year: currentYear,
      month: currentMonth,
    });

    return properties.map<PropertyRow>((property) => {
      const presentation = propertyPresentationFallback[property.name] ?? {
        image: "🏠",
        floor: "N/D",
        rooms: 1,
        bathrooms: 1,
        status: "active" as const,
      };

      return {
        id: property.id,
        name: property.name,
        location: property.address,
        status: presentation.status,
        monthlyRevenue: toNumber(property.monthly_revenue),
        occupancy: property.occupancy_rate,
        image: presentation.image,
        capacity: property.capacity_adults + property.capacity_kids,
        floor: presentation.floor,
        rooms: presentation.rooms,
        bathrooms: presentation.bathrooms,
      };
    });
  }, [currentMonth, currentYear]);

  const properties = data ?? [];

  const filtered = useMemo(
    () =>
      properties.filter((property) => {
        const matchSearch =
          property.name.toLowerCase().includes(search.toLowerCase()) ||
          property.location.toLowerCase().includes(search.toLowerCase());
        const matchStatus =
          filterStatus === "all" || property.status === filterStatus;
        return matchSearch && matchStatus;
      }),
    [filterStatus, properties, search],
  );

  const averageOccupancy =
    properties.reduce((sum, property) => sum + property.occupancy, 0) /
    Math.max(properties.length, 1);
  const totalMonthlyRevenue = properties.reduce(
    (sum, property) => sum + property.monthlyRevenue,
    0,
  );

  return (
    <AppShell>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="font-serif text-3xl font-semibold text-gold-gradient">
              Propiedades
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Gestion de tu cartera de alojamientos
            </p>
          </div>
          <button className="rounded-lg bg-gold px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-gold-dark">
            + Nueva Propiedad
          </button>
        </div>

        {loading && !data ? (
          <LoadingCard
            title="Cargando inventario real"
            message="Consultando propiedades y metricas del mes actual."
          />
        ) : null}

        {!loading && error && !data ? (
          <ErrorCard
            title="No fue posible cargar las propiedades"
            message={error}
          />
        ) : null}

        {data ? (
          <>
            <div className="mb-6 flex flex-col gap-3 sm:flex-row">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Buscar propiedad o ubicacion..."
                  className="w-full rounded-lg border border-border bg-muted/30 py-2.5 pl-10 pr-4 text-sm text-foreground transition-all placeholder:text-muted-foreground focus:border-gold/30 focus:outline-none focus:ring-1 focus:ring-gold/20"
                />
              </div>
              <div className="flex rounded-lg border border-border bg-muted/30 p-0.5">
                {(["all", "active", "inactive"] as const).map((status) => (
                  <button
                    key={status}
                    onClick={() => setFilterStatus(status)}
                    className={`rounded-md px-3 py-2 text-xs font-medium transition-colors ${
                      filterStatus === status
                        ? "bg-gold/20 text-gold"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {status === "all"
                      ? "Todas"
                      : status === "active"
                        ? "Activas"
                        : "Inactivas"}
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-6 grid grid-cols-3 gap-4">
              <div className="glass-card rounded-lg p-4">
                <p className="text-xs text-muted-foreground">Total Propiedades</p>
                <p className="mt-1 text-xl font-semibold text-foreground">
                  {properties.length}
                </p>
              </div>
              <div className="glass-card rounded-lg p-4">
                <p className="text-xs text-muted-foreground">Ocupacion Media</p>
                <p className="mt-1 text-xl font-semibold text-gold">
                  {Math.round(averageOccupancy)}%
                </p>
              </div>
              <div className="glass-card rounded-lg p-4">
                <p className="text-xs text-muted-foreground">Ingreso Mensual Total</p>
                <p className="mt-1 text-xl font-semibold text-foreground">
                  {formatCOP(totalMonthlyRevenue)}
                </p>
              </div>
            </div>

            <motion.div
              variants={containerVariants}
              initial="hidden"
              animate="show"
              className="glass-card overflow-hidden rounded-xl"
            >
              <div className="hidden grid-cols-[2fr_1.5fr_0.8fr_1fr_1fr_0.5fr] gap-4 border-b border-border bg-muted/20 px-6 py-3 lg:grid">
                <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Propiedad
                </span>
                <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Ubicacion
                </span>
                <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Estado
                </span>
                <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Rentabilidad
                </span>
                <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Ocupacion
                </span>
                <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Acciones
                </span>
              </div>

              {filtered.map((property) => (
                <motion.div
                  key={property.id}
                  variants={itemVariants}
                  className="border-b border-border/50 transition-colors hover:bg-muted/10"
                >
                  <div className="grid grid-cols-1 items-center gap-4 px-6 py-4 lg:grid-cols-[2fr_1.5fr_0.8fr_1fr_1fr_0.5fr]">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted/50 text-lg">
                        {property.image}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-foreground">
                          {property.name}
                        </p>
                        <p className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span className="flex items-center gap-0.5">
                            <Users className="h-3 w-3" />
                            {property.capacity}
                          </span>
                          <span className="flex items-center gap-0.5">
                            <BedDouble className="h-3 w-3" />
                            {property.rooms}
                          </span>
                          <span className="flex items-center gap-0.5">
                            <Bath className="h-3 w-3" />
                            {property.bathrooms}
                          </span>
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                      <MapPin className="h-3.5 w-3.5" />
                      {property.location}
                    </div>

                    <div>
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                          property.status === "active"
                            ? "bg-emerald-500/10 text-emerald-400"
                            : "bg-zinc-500/10 text-zinc-400"
                        }`}
                      >
                        {property.status === "active" ? "Activo" : "Inactivo"}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <DollarSign className="h-3.5 w-3.5 text-gold" />
                      <span className="text-sm font-medium text-foreground">
                        {property.monthlyRevenue > 0
                          ? `${formatCOP(property.monthlyRevenue)}/mes`
                          : "—"}
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="h-1.5 max-w-[100px] flex-1 overflow-hidden rounded-full bg-muted/50">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${property.occupancy}%` }}
                          transition={{ duration: 0.8 }}
                          className={`h-full rounded-full ${
                            property.occupancy >= 80
                              ? "bg-emerald-400"
                              : property.occupancy >= 50
                                ? "bg-gold"
                                : "bg-red-400"
                          }`}
                        />
                      </div>
                      <span className="tabular-nums text-xs font-medium text-foreground">
                        {Math.round(property.occupancy)}%
                      </span>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() =>
                          setExpandedRow(
                            expandedRow === property.id ? null : property.id,
                          )
                        }
                        className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
                      >
                        <MoreHorizontal className="h-4 w-4" />
                      </button>
                    </div>
                  </div>

                  {expandedRow === property.id ? (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="flex gap-2 px-6 pb-4"
                    >
                      <button className="flex items-center gap-1.5 rounded-md bg-muted/30 px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted/50">
                        <Eye className="h-3 w-3" />
                        Ver Calendario
                      </button>
                      <button className="flex items-center gap-1.5 rounded-md bg-muted/30 px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted/50">
                        <DollarSign className="h-3 w-3" />
                        Ver Finanzas
                      </button>
                      <button className="flex items-center gap-1.5 rounded-md bg-gold/10 px-3 py-1.5 text-xs font-medium text-gold transition-colors hover:bg-gold/20">
                        <Pencil className="h-3 w-3" />
                        Editar
                      </button>
                    </motion.div>
                  ) : null}
                </motion.div>
              ))}
            </motion.div>
          </>
        ) : null}
      </motion.div>
    </AppShell>
  );
}

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import {
  OpsTask,
  Property,
  TaskStatus,
  TaskType,
  completeTask,
  createTask,
  fetchProperties,
  fetchTasks,
  updateTask,
} from "@/lib/api";
import { motion } from "framer-motion";
import {
  Brush,
  CheckCircle2,
  Clock,
  Filter,
  Loader2,
  Plus,
  ShieldAlert,
  XCircle,
} from "lucide-react";

const STATUS_LABEL: Record<TaskStatus, string> = {
  PENDING: "Pendiente",
  IN_PROGRESS: "En curso",
  DONE: "Completada",
  CANCELLED: "Cancelada",
};

const STATUS_BADGE: Record<TaskStatus, string> = {
  PENDING: "bg-zinc-700 text-zinc-200",
  IN_PROGRESS: "bg-blue-500/20 text-blue-300",
  DONE: "bg-emerald-500/20 text-emerald-300",
  CANCELLED: "bg-red-500/20 text-red-300",
};

const TYPE_LABEL: Record<TaskType, string> = {
  CLEANING: "Limpieza",
  MAINTENANCE: "Mantenimiento",
  INSPECTION: "Inspección",
  OTHER: "Otra",
};

export default function TareasPage() {
  const { me, can, loading: authLoading } = useAuth();
  const isCleaner = me?.user.system_role === "CLEANER";
  // Booking module is the gating module for ops tasks (matches backend).
  const canRead = isCleaner || can("booking", "read");
  const canWrite = !isCleaner && can("booking", "write");

  const [tasks, setTasks] = useState<OpsTask[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState<TaskStatus | "">("");

  // create form
  const [creating, setCreating] = useState(false);
  const [propertyId, setPropertyId] = useState("");
  const [type, setType] = useState<TaskType>("CLEANING");
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");

  const load = useCallback(async () => {
    if (!canRead) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const params = isCleaner ? { assigned_to_me: true } : {};
      const [tasksData, propsData] = await Promise.all([
        fetchTasks(params),
        canWrite ? fetchProperties() : Promise.resolve([]),
      ]);
      setTasks(tasksData);
      setProperties(propsData as Property[]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error cargando tareas");
    } finally {
      setLoading(false);
    }
  }, [canRead, canWrite, isCleaner]);

  useEffect(() => {
    if (!authLoading) load();
  }, [authLoading, load]);

  const visibleTasks = useMemo(
    () =>
      statusFilter ? tasks.filter((t) => t.status === statusFilter) : tasks,
    [tasks, statusFilter]
  );

  const counts = useMemo(() => {
    const acc: Record<TaskStatus, number> = {
      PENDING: 0,
      IN_PROGRESS: 0,
      DONE: 0,
      CANCELLED: 0,
    };
    for (const t of tasks) acc[t.status] = (acc[t.status] || 0) + 1;
    return acc;
  }, [tasks]);

  async function handleComplete(id: string) {
    try {
      const updated = await completeTask(id);
      setTasks((prev) => prev.map((t) => (t.id === id ? updated : t)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error completando tarea");
    }
  }

  async function handleStart(id: string) {
    try {
      const updated = await updateTask(id, { status: "IN_PROGRESS" });
      setTasks((prev) => prev.map((t) => (t.id === id ? updated : t)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error actualizando tarea");
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!propertyId || !title || !dueDate) {
      setError("Completa propiedad, título y fecha.");
      return;
    }
    setCreating(true);
    setError("");
    try {
      const created = await createTask({
        property: propertyId,
        type,
        title,
        notes,
        due_date: dueDate,
      });
      setTasks((prev) => [created, ...prev]);
      setTitle("");
      setNotes("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error creando tarea");
    } finally {
      setCreating(false);
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
              No tienes permisos para ver tareas
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Pídele al propietario que te conceda permisos en
              &quot;booking&quot;.
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
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="font-serif text-3xl font-semibold text-gold-gradient">
              {isCleaner ? "Mis tareas" : "Tareas operativas"}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {isCleaner
                ? "Listado de tareas asignadas. Marca completadas al terminar."
                : "Limpiezas auto-generadas al hacer reservas + tareas manuales."}
            </p>
          </div>
        </div>

        {error && (
          <p className="text-sm text-red-400 bg-red-500/10 p-3 rounded-lg mb-4">
            {error}
          </p>
        )}

        {!isCleaner && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <Stat label="Pendientes" value={counts.PENDING} icon={Clock} />
            <Stat
              label="En curso"
              value={counts.IN_PROGRESS}
              icon={Loader2}
            />
            <Stat label="Hechas" value={counts.DONE} icon={CheckCircle2} />
            <Stat label="Canceladas" value={counts.CANCELLED} icon={XCircle} />
          </div>
        )}

        {!isCleaner && (
          <div className="flex items-center gap-2 mb-4">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as TaskStatus | "")}
              className={inputClass}
            >
              <option value="">Todas</option>
              <option value="PENDING">Pendientes</option>
              <option value="IN_PROGRESS">En curso</option>
              <option value="DONE">Completadas</option>
              <option value="CANCELLED">Canceladas</option>
            </select>
          </div>
        )}

        {canWrite && (
          <div className="glass-card rounded-xl p-6 mb-6">
            <div className="flex items-center gap-2 mb-3">
              <Brush className="h-5 w-5 text-gold" />
              <h2 className="font-serif text-xl font-semibold">
                Nueva tarea manual
              </h2>
            </div>
            <form
              onSubmit={handleCreate}
              className="grid grid-cols-1 md:grid-cols-3 gap-3"
            >
              <select
                value={propertyId}
                onChange={(e) => setPropertyId(e.target.value)}
                className={inputClass}
                required
              >
                <option value="">Propiedad…</option>
                {properties.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              <select
                value={type}
                onChange={(e) => setType(e.target.value as TaskType)}
                className={inputClass}
              >
                <option value="CLEANING">Limpieza</option>
                <option value="MAINTENANCE">Mantenimiento</option>
                <option value="INSPECTION">Inspección</option>
                <option value="OTHER">Otra</option>
              </select>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className={inputClass}
                required
              />
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Título de la tarea"
                className={`${inputClass} md:col-span-2`}
                required
              />
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Notas (opcional)"
                className={inputClass}
              />
              <button
                type="submit"
                disabled={creating}
                className="md:col-span-3 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-gold text-zinc-900 font-medium hover:bg-gold/90 disabled:opacity-50"
              >
                {creating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                Crear tarea
              </button>
            </form>
          </div>
        )}

        <div className="space-y-2">
          {visibleTasks.length === 0 ? (
            <div className="glass-card rounded-xl p-6 text-center text-muted-foreground text-sm">
              {isCleaner
                ? "No tienes tareas asignadas hoy."
                : "Sin tareas que mostrar."}
            </div>
          ) : (
            visibleTasks.map((task) => (
              <div
                key={task.id}
                className="glass-card rounded-xl p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-medium text-foreground">{task.title}</h3>
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${STATUS_BADGE[task.status]}`}
                    >
                      {STATUS_LABEL[task.status]}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded bg-zinc-800 text-zinc-300">
                      {TYPE_LABEL[task.type]}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {task.property_name} · vence {task.due_date}
                    {task.assigned_to_name && (
                      <span> · asignada a {task.assigned_to_name}</span>
                    )}
                  </p>
                  {task.notes && (
                    <p className="text-xs text-muted-foreground mt-2 whitespace-pre-line">
                      {task.notes}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {task.status === "PENDING" && (
                    <button
                      onClick={() => handleStart(task.id)}
                      className="px-3 py-1.5 rounded-lg border border-zinc-700 text-xs hover:bg-zinc-800"
                    >
                      Empezar
                    </button>
                  )}
                  {task.status !== "DONE" && task.status !== "CANCELLED" && (
                    <button
                      onClick={() => handleComplete(task.id)}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-gold text-zinc-900 text-xs font-medium hover:bg-gold/90"
                    >
                      <CheckCircle2 className="h-4 w-4" /> Marcar hecha
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </motion.div>
    </AppShell>
  );
}

const inputClass =
  "px-3 py-2 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none";

function Stat({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="glass-card rounded-xl p-4 flex items-center gap-3">
      <Icon className="h-6 w-6 text-gold" />
      <div>
        <p className="text-xs uppercase tracking-wide text-muted-foreground">
          {label}
        </p>
        <p className="font-serif text-2xl text-gold">{value}</p>
      </div>
    </div>
  );
}

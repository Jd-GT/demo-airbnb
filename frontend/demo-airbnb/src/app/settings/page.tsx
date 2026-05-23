"use client";

import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/app-shell";
import {
  createInvitationCode,
  deactivateInvitationCode,
  fetchInvitationCodes,
  fetchTenantUsers,
  InvitationCode,
  TenantUser,
} from "@/lib/api";
import { useAuth, useLogout } from "@/components/auth-provider";
import { motion } from "framer-motion";
import {
  Building2,
  Check,
  Copy,
  Loader2,
  LogOut,
  Plus,
  ShieldAlert,
  Trash2,
  Users,
} from "lucide-react";

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

export default function SettingsPage() {
  const logout = useLogout();
  const { me, loading: authLoading, can } = useAuth();

  const canManageUsers = can("users", "admin");

  const [users, setUsers] = useState<TenantUser[]>([]);
  const [codes, setCodes] = useState<InvitationCode[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [maxUses, setMaxUses] = useState(1);
  const [notes, setNotes] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const tasks: Promise<unknown>[] = [];
      if (canManageUsers) {
        tasks.push(fetchTenantUsers().then(setUsers));
        tasks.push(fetchInvitationCodes().then(setCodes));
      }
      await Promise.all(tasks);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cargando datos");
    } finally {
      setLoading(false);
    }
  }, [canManageUsers]);

  useEffect(() => {
    if (!authLoading) {
      loadData();
    }
  }, [authLoading, loadData]);

  async function handleCreateCode(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError("");
    try {
      const created = await createInvitationCode({ max_uses: maxUses, notes });
      setCodes((prev) => [created, ...prev]);
      setMaxUses(1);
      setNotes("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error creando código");
    } finally {
      setCreating(false);
    }
  }

  async function handleDeactivate(codeId: string) {
    if (!confirm("¿Desactivar este código? No se podrá usar más para invitar.")) return;
    try {
      await deactivateInvitationCode(codeId);
      setCodes((prev) =>
        prev.map((c) => (c.id === codeId ? { ...c, is_active: false } : c))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desactivando código");
    }
  }

  function handleCopy(code: string) {
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
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

  const tenant = me?.tenant;

  return (
    <AppShell>
      <motion.div variants={containerVariants} initial="hidden" animate="show">
        <motion.div variants={itemVariants} className="mb-8">
          <h1 className="font-serif text-3xl font-semibold text-gold-gradient">
            Configuración
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Información de tu empresa, equipo e invitaciones.
          </p>
        </motion.div>

        {error && (
          <motion.div variants={itemVariants} className="mb-6">
            <p className="text-sm text-red-400 bg-red-500/10 p-3 rounded-lg">
              {error}
            </p>
          </motion.div>
        )}

        <motion.div variants={itemVariants} className="mb-8">
          <div className="glass-card rounded-xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <Building2 className="h-5 w-5 text-gold" />
              <h2 className="font-serif text-xl font-semibold text-foreground">
                Empresa
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-muted-foreground">Nombre</label>
                <p className="text-foreground font-medium">{tenant?.name ?? "—"}</p>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Subdominio</label>
                <p className="text-foreground font-medium">
                  {tenant?.subdomain ?? "—"}
                </p>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Tu rol</label>
                <p className="text-foreground font-medium">
                  {me?.user.system_role === "OWNER"
                    ? "Propietario"
                    : me?.user.role?.name ?? "Miembro"}
                </p>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Tu email</label>
                <p className="text-foreground font-medium">{me?.user.email}</p>
              </div>
            </div>
          </div>
        </motion.div>

        {canManageUsers ? (
          <>
            <motion.div variants={itemVariants} className="mb-8">
              <div className="glass-card rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                  <Users className="h-5 w-5 text-gold" />
                  <h2 className="font-serif text-xl font-semibold text-foreground">
                    Códigos de Invitación
                  </h2>
                </div>
                <p className="text-sm text-muted-foreground mb-4">
                  Cada código permite que una persona se una a tu empresa. Puedes
                  fijar cuántos usos admite y, si quieres, dejar una nota para
                  recordar a quién se lo enviaste.
                </p>

                <form
                  onSubmit={handleCreateCode}
                  className="grid grid-cols-1 md:grid-cols-[100px_1fr_auto] gap-2 mb-6"
                >
                  <input
                    type="number"
                    min={1}
                    value={maxUses}
                    onChange={(e) =>
                      setMaxUses(Math.max(1, parseInt(e.target.value, 10) || 1))
                    }
                    className="px-3 py-2 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none"
                    placeholder="Usos"
                  />
                  <input
                    type="text"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="px-3 py-2 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none"
                    placeholder="Nota (ej: 'Para Carolina, recepcionista')"
                  />
                  <button
                    type="submit"
                    disabled={creating}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gold text-zinc-900 font-medium hover:bg-gold/90 transition-colors disabled:opacity-50"
                  >
                    {creating ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Plus className="h-4 w-4" />
                    )}
                    Generar código
                  </button>
                </form>

                {codes.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    Aún no has generado códigos. El primero lo puedes crear arriba.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {codes.map((code) => (
                      <div
                        key={code.id}
                        className={`flex flex-col md:flex-row md:items-center md:justify-between gap-3 p-3 rounded-lg border ${
                          code.is_usable
                            ? "border-zinc-700 bg-zinc-800/30"
                            : "border-zinc-800 bg-zinc-900/40 opacity-70"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <code className="font-mono text-sm tracking-wider text-gold">
                            {code.code}
                          </code>
                          <button
                            onClick={() => handleCopy(code.code)}
                            className="p-1 rounded text-muted-foreground hover:text-foreground transition-colors"
                            title="Copiar"
                          >
                            {copiedCode === code.code ? (
                              <Check className="h-4 w-4" />
                            ) : (
                              <Copy className="h-4 w-4" />
                            )}
                          </button>
                          <span className="text-xs text-muted-foreground">
                            {code.uses_count} / {code.max_uses} usos
                          </span>
                          {!code.is_active && (
                            <span className="text-xs px-2 py-0.5 rounded bg-red-500/15 text-red-300">
                              Desactivado
                            </span>
                          )}
                          {code.is_expired && (
                            <span className="text-xs px-2 py-0.5 rounded bg-yellow-500/15 text-yellow-300">
                              Expirado
                            </span>
                          )}
                          {code.is_exhausted && (
                            <span className="text-xs px-2 py-0.5 rounded bg-zinc-700 text-zinc-300">
                              Agotado
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-3">
                          {code.notes && (
                            <span className="text-xs text-muted-foreground italic max-w-[20rem] truncate">
                              {code.notes}
                            </span>
                          )}
                          {code.is_active && (
                            <button
                              onClick={() => handleDeactivate(code.id)}
                              className="p-1 rounded text-red-400 hover:bg-red-500/10 transition-colors"
                              title="Desactivar código"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>

            <motion.div variants={itemVariants} className="mb-8">
              <div className="glass-card rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                  <Users className="h-5 w-5 text-gold" />
                  <h2 className="font-serif text-xl font-semibold text-foreground">
                    Usuarios del equipo ({users.length})
                  </h2>
                </div>

                {users.length > 0 ? (
                  <div className="space-y-2">
                    {users.map((user) => (
                      <div
                        key={user.id}
                        className="flex items-center justify-between p-3 rounded-lg bg-zinc-800/30"
                      >
                        <div>
                          <p className="text-foreground font-medium">
                            {user.full_name}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {user.email}
                          </p>
                        </div>
                        <div className="text-right">
                          <span
                            className={`text-xs px-2 py-1 rounded ${
                              user.system_role === "OWNER"
                                ? "bg-gold/20 text-gold"
                                : "bg-zinc-700 text-zinc-300"
                            }`}
                          >
                            {user.system_role === "OWNER"
                              ? "Propietario"
                              : user.role?.name || "Miembro"}
                          </span>
                          {!user.is_active && (
                            <p className="text-xs text-red-400 mt-1">
                              Desactivado
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No hay otros usuarios todavía.
                  </p>
                )}
              </div>
            </motion.div>
          </>
        ) : (
          <motion.div variants={itemVariants} className="mb-8">
            <div className="glass-card rounded-xl p-6 flex items-start gap-3">
              <ShieldAlert className="h-5 w-5 text-zinc-400 mt-0.5" />
              <div>
                <p className="text-sm text-foreground font-medium">
                  Sólo los administradores ven el listado de usuarios y los
                  códigos de invitación
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Pídele al propietario de la empresa que ajuste tu rol si
                  necesitas acceso a estas opciones.
                </p>
              </div>
            </div>
          </motion.div>
        )}

        <motion.div variants={itemVariants}>
          <button
            onClick={logout}
            className="flex items-center gap-2 w-full justify-center px-4 py-3 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <LogOut className="h-5 w-5" />
            Cerrar Sesión
          </button>
        </motion.div>
      </motion.div>
    </AppShell>
  );
}

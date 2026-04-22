"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/app-shell";
import { fetchCurrentTenant, fetchTenantUsers, updateTenantInvitationCode, TenantUser } from "@/lib/api";
import { useLogout } from "@/components/auth-provider";
import { motion } from "framer-motion";
import {
  Building2,
  Copy,
  Check,
  Users,
  LogOut,
  Loader2,
  Save,
  Trash2,
  Plus,
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
  const router = useRouter();
  const logout = useLogout();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [tenant, setTenant] = useState<any>(null);
  const [users, setUsers] = useState<TenantUser[]>([]);
  const [invitationCode, setInvitationCode] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [tenantData, usersData] = await Promise.all([
        fetchCurrentTenant(),
        fetchTenantUsers(),
      ]);
      setTenant(tenantData);
      setUsers(usersData);
      setInvitationCode(tenantData.branding_config?.invitation_code || "");
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveCode() {
    setSaving(true);
    try {
      await updateTenantInvitationCode(invitationCode);
      const tenantData = await fetchCurrentTenant();
      setTenant(tenantData);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  }

  function handleCopyCode() {
    navigator.clipboard.writeText(invitationCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-gold" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <motion.div variants={containerVariants} initial="hidden" animate="show">
        <motion.div variants={itemVariants} className="mb-8">
          <h1 className="font-serif text-3xl font-semibold text-gold-gradient">
            Configuración
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Gestiona tu empresa y usuarios
          </p>
        </motion.div>

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
                <p className="text-foreground font-medium">{tenant?.name}</p>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Subdominio</label>
                <p className="text-foreground font-medium">{tenant?.subdomain}</p>
              </div>
            </div>
          </div>
        </motion.div>

        <motion.div variants={itemVariants} className="mb-8">
          <div className="glass-card rounded-xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <Users className="h-5 w-5 text-gold" />
              <h2 className="font-serif text-xl font-semibold text-foreground">
                Código de Invitación
              </h2>
            </div>
            
            <p className="text-sm text-muted-foreground mb-4">
              Comparte este código con personas que quieras que se unan a tu empresa.
            </p>
            
            <div className="flex gap-2">
              <input
                type="text"
                value={invitationCode}
                onChange={(e) => setInvitationCode(e.target.value.toUpperCase())}
                className="flex-1 px-4 py-3 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none transition-colors"
                placeholder="CODIGO123"
              />
              <button
                onClick={handleCopyCode}
                className="p-3 rounded-lg border border-zinc-700 text-muted-foreground hover:text-foreground transition-colors"
              >
                {copied ? <Check className="h-5 w-5" /> : <Copy className="h-5 w-5" />}
              </button>
              <button
                onClick={handleSaveCode}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-3 rounded-lg bg-gold text-zinc-900 font-medium hover:bg-gold/90 transition-colors disabled:opacity-50"
              >
                {saving ? <Loader2 className="h-5 w-5 animate-spin" /> : <Save className="h-5 w-5" />}
                Guardar
              </button>
            </div>
          </div>
        </motion.div>

        <motion.div variants={itemVariants} className="mb-8">
          <div className="glass-card rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Users className="h-5 w-5 text-gold" />
                <h2 className="font-serif text-xl font-semibold text-foreground">
                  Usuarios
                </h2>
              </div>
            </div>
            
            {users.length > 0 ? (
              <div className="space-y-2">
                {users.map((user) => (
                  <div
                    key={user.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-zinc-800/30"
                  >
                    <div>
                      <p className="text-foreground font-medium">{user.full_name}</p>
                      <p className="text-sm text-muted-foreground">{user.email}</p>
                    </div>
                    <div className="text-right">
                      <span className={`text-xs px-2 py-1 rounded ${
                        user.system_role === 'OWNER' 
                          ? 'bg-gold/20 text-gold' 
                          : 'bg-zinc-700 text-zinc-300'
                      }`}>
                        {user.system_role === 'OWNER' ? 'Propietario' : 'Miembro'}
                      </span>
                      {user.is_primary_owner && (
                        <p className="text-xs text-muted-foreground mt-1">Dueño de empresa</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No hay otros usuarios</p>
            )}
          </div>
        </motion.div>

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
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, registerNewTenant, registerJoinTenant } from "@/lib/api";
import { Building2, Loader2, LogIn, UserPlus } from "lucide-react";
import { motion } from "framer-motion";

type AuthMode = "login" | "register-new" | "register-join";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>("login");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [registerType, setRegisterType] = useState<"new_tenant" | "join_tenant">("new_tenant");
  const [fullName, setFullName] = useState("");
  const [tenantName, setTenantName] = useState("");
  const [tenantSubdomain, setTenantSubdomain] = useState("");
  const [tenantSubdomainJoin, setTenantSubdomainJoin] = useState("");
  const [invitationCode, setInvitationCode] = useState("");

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      await login(email, password);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      if (registerType === "new_tenant") {
        await registerNewTenant({
          email,
          full_name: fullName,
          password,
          tenant_name: tenantName,
          tenant_subdomain: tenantSubdomain.trim().toLowerCase().replace(/\s+/g, "-"),
        });
      } else {
        await registerJoinTenant({
          email,
          full_name: fullName,
          password,
          tenant_subdomain_join: tenantSubdomainJoin.trim().toLowerCase(),
          invitation_code: invitationCode.trim().toUpperCase(),
        });
      }
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-zinc-900 via-zinc-800 to-zinc-900 p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="glass-card rounded-2xl p-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gold/10 mb-4">
              <Building2 className="h-8 w-8 text-gold" />
            </div>
            <h1 className="font-serif text-2xl font-semibold text-gold-gradient">
              Demo Airbnb PMS
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              {mode === "login"
                ? "Inicia sesión en tu cuenta"
                : "Crea tu cuenta"}
            </p>
          </div>

          {mode === "login" ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="text-sm text-muted-foreground">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full mt-1 px-4 py-3 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none transition-colors"
                  placeholder="tu@email.com"
                  required
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Contraseña</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full mt-1 px-4 py-3 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none transition-colors"
                  placeholder="••••••••"
                  required
                />
              </div>

              {error && (
                <p className="text-sm text-red-400 bg-red-500/10 p-3 rounded-lg">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-lg bg-gold text-zinc-900 font-medium hover:bg-gold/90 transition-colors disabled:opacity-50"
              >
                {loading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <>
                    <LogIn className="h-5 w-5" />
                    Iniciar Sesión
                  </>
                )}
              </button>

              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-zinc-700" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="bg-zinc-800 px-2 text-muted-foreground">
                    o
                  </span>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setMode("register-new")}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-lg border border-zinc-700 text-foreground hover:bg-zinc-800 transition-colors"
              >
                <UserPlus className="h-5 w-5" />
                Crear cuenta nueva
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="space-y-4">
              <div>
                <label className="text-sm text-muted-foreground">
                  Tipo de cuenta
                </label>
                <div className="flex gap-2 mt-2">
                  <button
                    type="button"
                    onClick={() => setRegisterType("new_tenant")}
                    className={`flex-1 py-2 rounded-lg text-sm transition-colors ${
                      registerType === "new_tenant"
                        ? "bg-gold text-zinc-900"
                        : "bg-zinc-800 text-zinc-400 hover:text-foreground"
                    }`}
                  >
                   Nueva Empresa
                  </button>
                  <button
                    type="button"
                    onClick={() => setRegisterType("join_tenant")}
                    className={`flex-1 py-2 rounded-lg text-sm transition-colors ${
                      registerType === "join_tenant"
                        ? "bg-gold text-zinc-900"
                        : "bg-zinc-800 text-zinc-400 hover:text-foreground"
                    }`}
                  >
                    Unirse a Empresa
                  </button>
                </div>
              </div>

              <div>
                <label className="text-sm text-muted-foreground">
                  Nombre completo
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full mt-1 px-4 py-3 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none transition-colors"
                  placeholder="Juan Perez"
                  required
                />
              </div>

              <div>
                <label className="text-sm text-muted-foreground">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full mt-1 px-4 py-3 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none transition-colors"
                  placeholder="tu@email.com"
                  required
                />
              </div>

              <div>
                <label className="text-sm text-muted-foreground">
                  Contraseña
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full mt-1 px-4 py-3 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none transition-colors"
                  placeholder="Mínimo 8 caracteres"
                  minLength={8}
                  required
                />
              </div>

              {registerType === "new_tenant" ? (
                <>
                  <div>
                    <label className="text-sm text-muted-foreground">
                      Nombre de tu empresa
                    </label>
                    <input
                      type="text"
                      value={tenantName}
                      onChange={(e) => setTenantName(e.target.value)}
                      className="w-full mt-1 px-4 py-3 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none transition-colors"
                      placeholder="Caribe Rentals"
                      required
                    />
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">
                      Subdominio (URL)
                    </label>
                    <div className="flex items-center mt-1">
                      <span className="px-3 py-3 rounded-l-lg bg-zinc-800/50 border border-zinc-700 border-r-0 text-zinc-400 text-sm">
                        https://
                      </span>
                      <input
                        type="text"
                        value={tenantSubdomain}
                        onChange={(e) =>
                          setTenantSubdomain(
                            e.target.value.toLowerCase().replace(/\s+/g, "-")
                          )
                        }
                        className="flex-1 px-4 py-3 rounded-r-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none transition-colors"
                        placeholder="caribe-rentals"
                        required
                      />
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="text-sm text-muted-foreground">
                      Empresa a unirte
                    </label>
                    <input
                      type="text"
                      value={tenantSubdomainJoin}
                      onChange={(e) =>
                        setTenantSubdomainJoin(
                          e.target.value.toLowerCase()
                        )
                      }
                      className="w-full mt-1 px-4 py-3 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none transition-colors"
                      placeholder="caribe"
                      required
                    />
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">
                      Código de invitación
                    </label>
                    <input
                      type="text"
                      value={invitationCode}
                      onChange={(e) =>
                        setInvitationCode(
                          e.target.value.replace(/\s+/g, "").toUpperCase()
                        )
                      }
                      className="w-full mt-1 px-4 py-3 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none transition-colors"
                      placeholder="CODIGO123"
                      required
                    />
                  </div>
                </>
              )}

              {error && (
                <p className="text-sm text-red-400 bg-red-500/10 p-3 rounded-lg">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-lg bg-gold text-zinc-900 font-medium hover:bg-gold/90 transition-colors disabled:opacity-50"
              >
                {loading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <>
                    <UserPlus className="h-5 w-5" />
                    Crear Cuenta
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={() => setMode("login")}
                className="w-full text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                ¿Ya tienes cuenta? Inicia sesión
              </button>
            </form>
          )}
        </div>
      </motion.div>
    </div>
  );
}
"use client";

import { useMemo, useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { login, register } from "@/lib/api";
import {
  Building2,
  Info,
  KeyRound,
  Loader2,
  LogIn,
  UserPlus,
} from "lucide-react";
import { motion } from "framer-motion";

type AuthMode = "login" | "register";

const SUBDOMAIN_REGEX = /^[a-z0-9](?:[a-z0-9-]{1,38}[a-z0-9])?$/;

function normalizeSubdomain(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, "-");
}

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [mode, setMode] = useState<AuthMode>("login");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const modeParam = searchParams.get("mode");
    if (modeParam === "register") {
      setMode("register");
    }
  }, [searchParams]);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [fullName, setFullName] = useState("");
  const [invitationCode, setInvitationCode] = useState("");
  const [tenantName, setTenantName] = useState("");
  const [tenantSubdomain, setTenantSubdomain] = useState("");
  const [tenantSubdomainJoin, setTenantSubdomainJoin] = useState("");
  // The user explicitly chooses the type of code they were given.
  // The backend still validates against the actual purpose stored on
  // the code itself, so the UI choice is purely for collecting the
  // right extra fields and showing helpful copy.
  const [codeType, setCodeType] = useState<"new" | "join">("join");

  const subdomainError = useMemo(() => {
    if (!tenantSubdomain) return "";
    return SUBDOMAIN_REGEX.test(tenantSubdomain)
      ? ""
      : "Solo minúsculas, números y guiones. No incluyas '.com' ni espacios.";
  }, [tenantSubdomain]);

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
      const payload: Parameters<typeof register>[0] = {
        invitation_code: invitationCode.trim().toUpperCase(),
        email: email.trim(),
        full_name: fullName.trim(),
        password,
      };

      if (codeType === "new") {
        const subdomain = normalizeSubdomain(tenantSubdomain);
        if (!SUBDOMAIN_REGEX.test(subdomain)) {
          throw new Error(
            "El subdominio sólo puede tener minúsculas, números y guiones."
          );
        }
        payload.tenant_name = tenantName.trim();
        payload.tenant_subdomain = subdomain;
      } else if (tenantSubdomainJoin.trim()) {
        payload.tenant_subdomain_join = normalizeSubdomain(tenantSubdomainJoin);
      }

      await register(payload);
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
              {mode === "login" ? "Inicia sesión en tu cuenta" : "Crea tu cuenta"}
            </p>
          </div>

          {mode === "login" ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <Field label="Email">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputClass}
                  placeholder="tu@email.com"
                  autoComplete="email"
                  required
                />
              </Field>
              <Field label="Contraseña">
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={inputClass}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                />
              </Field>

              {error && <ErrorBanner message={error} />}

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
                onClick={() => {
                  setMode("register");
                  setError("");
                }}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-lg border border-zinc-700 text-foreground hover:bg-zinc-800 transition-colors"
              >
                <UserPlus className="h-5 w-5" />
                Tengo un código de invitación
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="space-y-4">
              <InfoBanner>
                Necesitas un <b>código de invitación</b>. Para abrir una
                empresa nueva, pídele uno al administrador de la plataforma.
                Para entrar al equipo de una empresa existente, pídeselo al
                dueño de esa empresa.
              </InfoBanner>

              <Field
                label="Código de invitación"
                hint="El código define a dónde te vas a registrar. Sin un código válido no se puede crear cuenta."
                icon={<KeyRound className="h-4 w-4" />}
              >
                <input
                  type="text"
                  value={invitationCode}
                  onChange={(e) =>
                    setInvitationCode(
                      e.target.value.replace(/\s+/g, "").toUpperCase()
                    )
                  }
                  className={`${inputClass} font-mono tracking-wider`}
                  placeholder="EJ: AB12CD34EF56"
                  required
                />
              </Field>

              <div>
                <label className="text-sm text-muted-foreground">
                  ¿Qué tipo de código tienes?
                </label>
                <div className="flex gap-2 mt-2">
                  <button
                    type="button"
                    onClick={() => setCodeType("join")}
                    className={`flex-1 py-2 rounded-lg text-sm transition-colors ${
                      codeType === "join"
                        ? "bg-gold text-zinc-900"
                        : "bg-zinc-800 text-zinc-400 hover:text-foreground"
                    }`}
                  >
                    Para entrar a una empresa
                  </button>
                  <button
                    type="button"
                    onClick={() => setCodeType("new")}
                    className={`flex-1 py-2 rounded-lg text-sm transition-colors ${
                      codeType === "new"
                        ? "bg-gold text-zinc-900"
                        : "bg-zinc-800 text-zinc-400 hover:text-foreground"
                    }`}
                  >
                    Para abrir una empresa nueva
                  </button>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Si te equivocas no pasa nada: el servidor te avisará si el
                  código es de otro tipo.
                </p>
              </div>

              <Field label="Nombre completo">
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className={inputClass}
                  placeholder="Juan Perez"
                  autoComplete="name"
                  required
                />
              </Field>

              <Field label="Email">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputClass}
                  placeholder="tu@email.com"
                  autoComplete="email"
                  required
                />
              </Field>

              <Field label="Contraseña">
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={inputClass}
                  placeholder="Mínimo 8 caracteres"
                  minLength={8}
                  autoComplete="new-password"
                  required
                />
              </Field>

              {codeType === "new" ? (
                <>
                  <Field label="Nombre comercial de tu empresa">
                    <input
                      type="text"
                      value={tenantName}
                      onChange={(e) => setTenantName(e.target.value)}
                      className={inputClass}
                      placeholder="Caribe Rentals"
                      required
                    />
                  </Field>
                  <Field
                    label="Subdominio para tu empresa"
                    hint="Este texto antecede a la URL de tu PMS. NO es un dominio completo: no escribas '.com' ni 'http://'. Solo letras, números y guiones."
                  >
                    <div className="flex items-center mt-1">
                      <span className="px-3 py-3 rounded-l-lg bg-zinc-800/50 border border-zinc-700 border-r-0 text-zinc-400 text-sm">
                        https://
                      </span>
                      <input
                        type="text"
                        value={tenantSubdomain}
                        onChange={(e) =>
                          setTenantSubdomain(normalizeSubdomain(e.target.value))
                        }
                        className="flex-1 px-4 py-3 bg-zinc-800/50 border-y border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none transition-colors"
                        placeholder="caribe-rentals"
                        required
                      />
                      <span className="px-3 py-3 rounded-r-lg bg-zinc-800/50 border border-zinc-700 border-l-0 text-zinc-400 text-sm">
                        .demoairbnb.app
                      </span>
                    </div>
                    {subdomainError && (
                      <p className="text-xs text-red-400 mt-1">{subdomainError}</p>
                    )}
                  </Field>
                </>
              ) : (
                <Field
                  label="Subdominio de la empresa (opcional)"
                  hint="No es obligatorio: el código ya identifica a la empresa. Llénalo solo si quieres confirmar visualmente que es la correcta."
                >
                  <input
                    type="text"
                    value={tenantSubdomainJoin}
                    onChange={(e) =>
                      setTenantSubdomainJoin(normalizeSubdomain(e.target.value))
                    }
                    className={inputClass}
                    placeholder="caribe-rentals"
                  />
                </Field>
              )}

              {error && <ErrorBanner message={error} />}

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
                onClick={() => {
                  setMode("login");
                  setError("");
                }}
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

const inputClass =
  "w-full mt-1 px-4 py-3 rounded-lg bg-zinc-800/50 border border-zinc-700 text-foreground focus:border-gold/50 focus:outline-none transition-colors";

function Field({
  label,
  hint,
  icon,
  children,
}: {
  label: string;
  hint?: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="text-sm text-muted-foreground flex items-center gap-2">
        {icon}
        {label}
      </label>
      {children}
      {hint && (
        <p className="text-xs text-muted-foreground mt-1 leading-snug">{hint}</p>
      )}
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <p className="text-sm text-red-400 bg-red-500/10 p-3 rounded-lg">
      {message}
    </p>
  );
}

function InfoBanner({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2 text-xs text-zinc-300 bg-zinc-800/50 border border-zinc-700 rounded-lg p-3">
      <Info className="h-4 w-4 shrink-0 mt-0.5 text-gold" />
      <p className="leading-snug">{children}</p>
    </div>
  );
}

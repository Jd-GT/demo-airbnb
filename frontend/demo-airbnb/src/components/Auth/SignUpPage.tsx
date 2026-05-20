"use client";

import { useEffect, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { UserPlus } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SUBDOMAIN_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

type AccountType = 'guest' | 'booking_agent';

type SignUpForm = {
  email: string;
  full_name: string;
  password: string;
  tenant_name: string;
  subdomain: string;
  account_type: AccountType;
};

type SignUpFormErrors = Partial<Record<keyof SignUpForm, string>>;

function slugifySubdomain(value: string) {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80);
}

function validateSignUpForm(form: SignUpForm) {
  const errors: SignUpFormErrors = {};

  if (!form.full_name.trim()) {
    errors.full_name = 'El nombre es requerido.';
  }

  if (!form.email.trim()) {
    errors.email = 'El email es requerido.';
  } else if (!EMAIL_PATTERN.test(form.email)) {
    errors.email = 'Ingresa un email valido.';
  }

  if (!form.password) {
    errors.password = 'La contrasena es requerida.';
  } else if (form.password.length < 8) {
    errors.password = 'La contrasena debe tener minimo 8 caracteres.';
  }

  if (!form.tenant_name.trim()) {
    errors.tenant_name = 'El nombre del tenant es requerido.';
  }

  if (!form.subdomain.trim()) {
    errors.subdomain = 'El subdominio es requerido.';
  } else if (!SUBDOMAIN_PATTERN.test(form.subdomain)) {
    errors.subdomain = 'Usa solo letras minusculas, numeros y guiones.';
  }

  if (!form.account_type) {
    errors.account_type = 'Selecciona un tipo de usuario.';
  }

  return errors;
}

export default function SignUpPage() {
  const router = useRouter();
  const { signup, isAuthenticated, loading, error, clearError } = useAuth();
  const [form, setForm] = useState<SignUpForm>({
    email: '',
    full_name: '',
    password: '',
    tenant_name: '',
    subdomain: '',
    account_type: 'guest',
  });
  const [fieldErrors, setFieldErrors] = useState<SignUpFormErrors>({});
  const [subdomainTouched, setSubdomainTouched] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace('/dashboard');
    }
  }, [isAuthenticated, router]);

  function updateField(field: keyof SignUpForm, value: string) {
    const nextValue = field === 'subdomain' ? slugifySubdomain(value) : value;

    setForm((current) => {
      const next = { ...current, [field]: nextValue };

      if (field === 'tenant_name' && !subdomainTouched) {
        next.subdomain = slugifySubdomain(value);
      }

      return next;
    });
    setFieldErrors((current) => ({ ...current, [field]: undefined }));
    clearError();

    if (field === 'subdomain') {
      setSubdomainTouched(true);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearError();

    const normalizedForm = {
      ...form,
      email: form.email.trim(),
      full_name: form.full_name.trim(),
      tenant_name: form.tenant_name.trim(),
      subdomain: slugifySubdomain(form.subdomain),
    };
    const validationErrors = validateSignUpForm(normalizedForm);
    setFieldErrors(validationErrors);

    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    try {
      await signup(normalizedForm);
      router.replace('/dashboard');
    } catch {
      // The auth context exposes the error message for the form.
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel auth-panel-wide" aria-labelledby="signup-title">
        <div className="auth-brand">
          <div className="auth-brand-mark" aria-hidden="true">
            EA
          </div>
          <div>
            <p className="auth-eyebrow">Nuevo tenant</p>
            <h1 id="signup-title">Crear cuenta</h1>
          </div>
        </div>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <div className="auth-grid">
            <label className="auth-field">
              <span>Nombre completo</span>
              <input
                type="text"
                name="full_name"
                autoComplete="name"
                value={form.full_name}
                onChange={(event) => updateField('full_name', event.target.value)}
                aria-invalid={Boolean(fieldErrors.full_name)}
                aria-describedby={fieldErrors.full_name ? 'signup-name-error' : undefined}
                required
              />
              {fieldErrors.full_name ? (
                <span id="signup-name-error" className="auth-field-error">
                  {fieldErrors.full_name}
                </span>
              ) : null}
            </label>

            <label className="auth-field">
              <span>Email</span>
              <input
                type="email"
                name="email"
                autoComplete="email"
                value={form.email}
                onChange={(event) => updateField('email', event.target.value)}
                aria-invalid={Boolean(fieldErrors.email)}
                aria-describedby={fieldErrors.email ? 'signup-email-error' : undefined}
                required
              />
              {fieldErrors.email ? (
                <span id="signup-email-error" className="auth-field-error">
                  {fieldErrors.email}
                </span>
              ) : null}
            </label>
          </div>

          <div className="auth-grid">
            <label className="auth-field">
              <span>Tipo de usuario</span>
              <select
                name="account_type"
                value={form.account_type}
                onChange={(event) => updateField('account_type', event.target.value as AccountType)}
                aria-invalid={Boolean(fieldErrors.account_type)}
                aria-describedby={fieldErrors.account_type ? 'signup-account-type-error' : undefined}
                required
              >
                <option value="guest">Huesped</option>
                <option value="booking_agent">Agente de reservas</option>
              </select>
              {fieldErrors.account_type ? (
                <span id="signup-account-type-error" className="auth-field-error">
                  {fieldErrors.account_type}
                </span>
              ) : null}
            </label>

            <label className="auth-field">
              <span>Contrasena</span>
              <input
                type="password"
                name="password"
                autoComplete="new-password"
                value={form.password}
                onChange={(event) => updateField('password', event.target.value)}
                aria-invalid={Boolean(fieldErrors.password)}
                aria-describedby={fieldErrors.password ? 'signup-password-error' : undefined}
                minLength={8}
                required
              />
              {fieldErrors.password ? (
                <span id="signup-password-error" className="auth-field-error">
                  {fieldErrors.password}
                </span>
              ) : null}
            </label>
          </div>

          <div className="auth-grid">
            <label className="auth-field">
              <span>Tenant</span>
              <input
                type="text"
                name="tenant_name"
                value={form.tenant_name}
                onChange={(event) => updateField('tenant_name', event.target.value)}
                aria-invalid={Boolean(fieldErrors.tenant_name)}
                aria-describedby={fieldErrors.tenant_name ? 'signup-tenant-error' : undefined}
                required
              />
              {fieldErrors.tenant_name ? (
                <span id="signup-tenant-error" className="auth-field-error">
                  {fieldErrors.tenant_name}
                </span>
              ) : null}
            </label>

            <label className="auth-field">
              <span>Subdominio</span>
              <input
                type="text"
                name="subdomain"
                value={form.subdomain}
                onChange={(event) => updateField('subdomain', event.target.value)}
                aria-invalid={Boolean(fieldErrors.subdomain)}
                aria-describedby={fieldErrors.subdomain ? 'signup-subdomain-error' : undefined}
                required
              />
              {fieldErrors.subdomain ? (
                <span id="signup-subdomain-error" className="auth-field-error">
                  {fieldErrors.subdomain}
                </span>
              ) : null}
            </label>
          </div>

          {error ? <div className="auth-alert">{error}</div> : null}

          <button className="auth-submit" type="submit" disabled={loading}>
            <UserPlus aria-hidden="true" size={18} />
            {loading ? 'Creando...' : 'Crear cuenta'}
          </button>
        </form>

        <p className="auth-switch">
          Ya tienes cuenta? <Link href="/login">Iniciar sesion</Link>
        </p>
      </section>
    </main>
  );
}

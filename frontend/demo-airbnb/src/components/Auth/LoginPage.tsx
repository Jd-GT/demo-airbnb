"use client";

import { useEffect, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { LogIn } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type LoginForm = {
  email: string;
  password: string;
};

type LoginFormErrors = Partial<Record<keyof LoginForm, string>>;

function normalizeRedirect(value: string | null) {
  if (value?.startsWith('/') && !value.startsWith('//')) {
    return value;
  }

  return '/dashboard';
}

function validateLoginForm(form: LoginForm) {
  const errors: LoginFormErrors = {};

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

  return errors;
}

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, loading, error, clearError } = useAuth();
  const [redirectTo] = useState(() =>
    typeof window === 'undefined'
      ? '/dashboard'
      : normalizeRedirect(new URLSearchParams(window.location.search).get('next')),
  );
  const [form, setForm] = useState<LoginForm>({ email: '', password: '' });
  const [fieldErrors, setFieldErrors] = useState<LoginFormErrors>({});

  useEffect(() => {
    if (isAuthenticated) {
      router.replace(redirectTo);
    }
  }, [isAuthenticated, redirectTo, router]);

  function updateField(field: keyof LoginForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setFieldErrors((current) => ({ ...current, [field]: undefined }));
    clearError();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearError();

    const validationErrors = validateLoginForm(form);
    setFieldErrors(validationErrors);

    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    try {
      await login(form.email.trim(), form.password);
      router.replace(redirectTo);
    } catch {
      // The auth context exposes the error message for the form.
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel" aria-labelledby="login-title">
        <div className="auth-brand">
          <div className="auth-brand-mark" aria-hidden="true">
            EA
          </div>
          <div>
            <p className="auth-eyebrow">Demo Airbnb</p>
            <h1 id="login-title">Iniciar sesion</h1>
          </div>
        </div>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <label className="auth-field">
            <span>Email</span>
            <input
              type="email"
              name="email"
              autoComplete="email"
              value={form.email}
              onChange={(event) => updateField('email', event.target.value)}
              aria-invalid={Boolean(fieldErrors.email)}
              aria-describedby={fieldErrors.email ? 'login-email-error' : undefined}
              required
            />
            {fieldErrors.email ? (
              <span id="login-email-error" className="auth-field-error">
                {fieldErrors.email}
              </span>
            ) : null}
          </label>

          <label className="auth-field">
            <span>Contrasena</span>
            <input
              type="password"
              name="password"
              autoComplete="current-password"
              value={form.password}
              onChange={(event) => updateField('password', event.target.value)}
              aria-invalid={Boolean(fieldErrors.password)}
              aria-describedby={fieldErrors.password ? 'login-password-error' : undefined}
              minLength={8}
              required
            />
            {fieldErrors.password ? (
              <span id="login-password-error" className="auth-field-error">
                {fieldErrors.password}
              </span>
            ) : null}
          </label>

          {error ? <div className="auth-alert">{error}</div> : null}

          <button className="auth-submit" type="submit" disabled={loading}>
            <LogIn aria-hidden="true" size={18} />
            {loading ? 'Ingresando...' : 'Entrar'}
          </button>
        </form>

        <p className="auth-switch">
          No tienes cuenta? <Link href="/signup">Crear cuenta</Link>
        </p>
      </section>
    </main>
  );
}

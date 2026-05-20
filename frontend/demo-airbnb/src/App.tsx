import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import type { ReactNode } from 'react';
import './App.css';
import LoginPage from './components/Auth/LoginPage';
import LogoutButton from './components/Auth/LogoutButton';
import SignUpPage from './components/Auth/SignUpPage';
import ProtectedRoute from './components/ProtectedRoute';
import { AuthProvider, useAuth } from './hooks/useAuth';

function PublicOnlyRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="auth-page">
        <div className="auth-status">Cargando sesion...</div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function DashboardPage() {
  const { user } = useAuth();

  return (
    <main className="dashboard-page">
      <header className="dashboard-header">
        <div>
          <p className="auth-eyebrow">Demo Airbnb</p>
          <h1>Dashboard</h1>
        </div>
        <LogoutButton />
      </header>

      <section className="dashboard-summary" aria-label="Sesion activa">
        <article>
          <span>Usuario</span>
          <strong>{user?.full_name}</strong>
          <p>{user?.email}</p>
        </article>
        <article>
          <span>Rol</span>
          <strong>{user?.system_role}</strong>
          <p>Permisos del sistema</p>
        </article>
        <article>
          <span>Tenant</span>
          <strong>{user?.tenant_id ?? 'Sin tenant'}</strong>
          <p>Contexto multi-tenant activo</p>
        </article>
      </section>
    </main>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicOnlyRoute>
            <LoginPage />
          </PublicOnlyRoute>
        }
      />
      <Route
        path="/signup"
        element={
          <PublicOnlyRoute>
            <SignUpPage />
          </PublicOnlyRoute>
        }
      />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;

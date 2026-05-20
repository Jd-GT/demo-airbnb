"use client";

import { LogOut } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

type LogoutButtonProps = {
  className?: string;
};

export default function LogoutButton({ className = '' }: LogoutButtonProps) {
  const { logout, loading } = useAuth();

  return (
    <button
      type="button"
      className={className || 'logout-button'}
      onClick={() => void logout()}
      disabled={loading}
    >
      <LogOut aria-hidden="true" size={18} />
      {loading ? 'Cerrando...' : 'Cerrar sesion'}
    </button>
  );
}

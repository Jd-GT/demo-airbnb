"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { isAuthenticated, logout as apiLogout } from "@/lib/api";

interface AuthContextType {
  isAuth: boolean | null;
  loading: boolean;
  checkAuth: () => void;
}

const AuthContext = createContext<AuthContextType>({
  isAuth: null,
  loading: true,
  checkAuth: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isAuth, setIsAuth] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = () => {
    const auth = isAuthenticated();
    setIsAuth(auth);
    setLoading(false);

    const isLoginPage = pathname === "/login";
    const isPublicPage = pathname.startsWith("/login");

    if (!auth && !isPublicPage) {
      router.push("/login");
    } else if (auth && isLoginPage) {
      router.push("/");
    }
  };

  useEffect(() => {
    checkAuth();
  }, [pathname]);

  return (
    <AuthContext.Provider value={{ isAuth, loading, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

export function useLogout() {
  const router = useRouter();
  return () => {
    apiLogout();
    router.push("/login");
  };
}
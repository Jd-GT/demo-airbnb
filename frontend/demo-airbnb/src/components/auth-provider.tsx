"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  CurrentUserResponse,
  fetchCurrentUser,
  hasPermission,
  isAuthenticated,
  logout as apiLogout,
  ModuleKey,
  PermissionLevel,
} from "@/lib/api";

interface AuthContextType {
  isAuth: boolean | null;
  loading: boolean;
  me: CurrentUserResponse | null;
  refreshMe: () => Promise<void>;
  can: (module: ModuleKey, required?: PermissionLevel) => boolean;
}

const AuthContext = createContext<AuthContextType>({
  isAuth: null,
  loading: true,
  me: null,
  refreshMe: async () => {},
  can: () => false,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isAuth, setIsAuth] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [me, setMe] = useState<CurrentUserResponse | null>(null);

  const refreshMe = useCallback(async () => {
    try {
      const data = await fetchCurrentUser();
      setMe(data);
    } catch {
      setMe(null);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      const auth = isAuthenticated();
      if (cancelled) return;
      setIsAuth(auth);
      if (auth) {
        await refreshMe();
      } else {
        setMe(null);
      }
      setLoading(false);

      // Public routes: landing y formularios de entrada. Cualquiera
      // (logueado o no) las puede ver, pero si ya estás logueado y
      // entras a login/signup te mandamos al dashboard.
      const publicPrefixes = ["/login", "/signup"];
      const landingExact = pathname === "/";
      const onPublicForm = publicPrefixes.some((p) => pathname.startsWith(p));

      if (!auth) {
        // Sin sesión: solo permitimos landing + public forms.
        if (!landingExact && !onPublicForm) {
          router.push("/login");
        }
      } else {
        // Con sesión: si está parado en login/signup → dashboard.
        // La landing "/" la dejamos pasar porque la lógica de redirect
        // a /dashboard la maneja el propio componente landing.
        if (onPublicForm) {
          router.push("/dashboard");
        }
      }
    }
    bootstrap();
    return () => {
      cancelled = true;
    };
  }, [pathname, refreshMe, router]);

  const can = useCallback(
    (module: ModuleKey, required: PermissionLevel = "read") =>
      hasPermission(me?.permissions, module, required),
    [me]
  );

  return (
    <AuthContext.Provider value={{ isAuth, loading, me, refreshMe, can }}>
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

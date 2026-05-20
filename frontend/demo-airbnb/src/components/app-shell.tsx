"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import {
  LayoutDashboard,
  CalendarDays,
  DollarSign,
  Building2,
  Link2,
  CreditCard,
  ChevronLeft,
  ChevronRight,
  Bell,
  LogOut,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { getActiveMembershipTier } from "@/lib/memberships";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/calendario", label: "Calendario", icon: CalendarDays },
  { href: "/finanzas", label: "Finanzas", icon: DollarSign },
  { href: "/propiedades", label: "Propiedades", icon: Building2 },
  { href: "/integraciones", label: "Integraciones", icon: Link2 },
  { href: "/memberships", label: "Memberships", icon: CreditCard },
];

function isNavItemActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function getInitials(name?: string | null) {
  if (!name) {
    return "US";
  }

  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "US";
}

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isAuthenticated, loading, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const shouldReduceMotion = useReducedMotion();
  const displayName = user?.full_name || user?.email || "Usuario";
  const initials = getInitials(user?.full_name || user?.email);
  const activeMembership = getActiveMembershipTier();
  const activeItem =
    navItems.find((item) => isNavItemActive(pathname, item.href)) ?? navItems[0];
  const sidebarTransition = shouldReduceMotion
    ? { duration: 0 }
    : { duration: 0.3, ease: [0.4, 0, 0.2, 1] as const };

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      const nextPath = pathname ? `?next=${encodeURIComponent(pathname)}` : "";
      router.replace(`/login${nextPath}`);
    }
  }, [isAuthenticated, loading, pathname, router]);

  if (loading) {
    return (
      <div className="auth-page">
        <div className="auth-status">Cargando sesion...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <motion.aside
        animate={{ width: collapsed ? 72 : 260 }}
        transition={sidebarTransition}
        className="relative hidden shrink-0 flex-col border-r border-border bg-sidebar lg:flex"
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 h-16 border-b border-border">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-gold to-gold-dark">
            <Building2 className="w-4 h-4 text-primary-foreground" />
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                transition={shouldReduceMotion ? { duration: 0 } : { duration: 0.2 }}
                className="overflow-hidden whitespace-nowrap"
              >
                <span className="font-serif text-lg font-semibold text-gold-gradient">
                  Emilamar
                </span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-3 space-y-1">
          {navItems.map((item) => {
            const isActive = isNavItemActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group relative flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 motion-reduce:transition-none ${
                  isActive
                    ? "bg-gold/10 text-gold"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                }`}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-gold rounded-full"
                    transition={
                      shouldReduceMotion
                        ? { duration: 0 }
                        : { type: "spring", stiffness: 500, damping: 30 }
                    }
                  />
                )}
                <item.icon className={`w-5 h-5 shrink-0 ${isActive ? "text-gold" : ""}`} />
                <AnimatePresence>
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={shouldReduceMotion ? { duration: 0 } : { duration: 0.15 }}
                      className="text-sm font-medium whitespace-nowrap"
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </Link>
            );
          })}
        </nav>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? "Expandir navegacion" : "Colapsar navegacion"}
          className="absolute -right-3 top-20 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-border bg-card text-muted-foreground transition-colors hover:border-gold/30 hover:text-gold motion-reduce:transition-none"
        >
          {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
        </button>

        {/* Bottom section */}
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={shouldReduceMotion ? { duration: 0 } : { duration: 0.2 }}
              className="p-4 border-t border-border"
            >
              <div className="glass-card rounded-lg p-3">
                <p className="text-xs text-muted-foreground">Property Manager</p>
                <p className="text-xs text-gold font-medium mt-0.5">
                  Plan {activeMembership.name}
                </p>
                <p className="mt-1 text-[10px] text-muted-foreground">
                  ${activeMembership.priceUsd} USD/mes
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.aside>

      {/* Main Content */}
      <main data-app-scroll-area className="flex-1 overflow-y-auto">
        <header className="sticky top-0 z-40 border-b border-border/70 bg-background/90 backdrop-blur-xl">
          <div className="mx-auto flex min-h-16 max-w-[1280px] items-center gap-4 px-6 sm:px-8">
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gold/10 lg:hidden">
                <Building2 className="h-4 w-4 text-gold" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-gold/80">
                  Emilamar
                </p>
                <p className="truncate text-sm text-muted-foreground">
                  {activeItem.label}
                </p>
              </div>
            </div>

            <nav aria-label="Navegacion principal" className="hidden items-center gap-1 xl:flex">
              {navItems.map((item) => {
                const isActive = isNavItemActive(pathname, item.href);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={isActive ? "page" : undefined}
                    className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors motion-reduce:transition-none ${
                      isActive
                        ? "bg-gold/10 text-gold"
                        : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                    }`}
                  >
                    <item.icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label="Notificaciones"
                className="relative rounded-full border border-border/70 bg-muted/30 text-muted-foreground hover:text-gold motion-reduce:transition-none"
              >
                <Bell className="h-4 w-4" />
                <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-gold" />
              </Button>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    aria-label="Abrir menu de usuario"
                    className="flex items-center gap-2 rounded-full border border-border/70 bg-muted/30 py-1 pl-1 pr-3 transition-colors hover:border-gold/30 hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 motion-reduce:transition-none"
                  >
                    <Avatar className="h-8 w-8 border border-gold/20">
                      <AvatarFallback className="bg-gold/15 text-xs font-semibold text-gold">
                        {initials}
                      </AvatarFallback>
                    </Avatar>
                    <span className="hidden text-sm font-medium text-foreground sm:inline">
                      {displayName}
                    </span>
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  align="end"
                  className="glass-card w-56 border-border/70"
                >
                  <DropdownMenuLabel>
                    <span className="block text-sm font-medium">{displayName}</span>
                    <span className="block text-xs font-normal text-muted-foreground">
                      {user?.email}
                    </span>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="text-red-300 focus:text-red-200"
                    onSelect={(event) => {
                      event.preventDefault();
                      void logout();
                    }}
                  >
                    <LogOut className="h-4 w-4" />
                    Cerrar sesion
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          <nav
            aria-label="Navegacion movil"
            className="flex gap-2 overflow-x-auto border-t border-border/60 px-6 py-3 lg:hidden"
          >
            {navItems.map((item) => {
              const isActive = isNavItemActive(pathname, item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={isActive ? "page" : undefined}
                  className={`flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-xs font-medium transition-colors motion-reduce:transition-none ${
                    isActive
                      ? "bg-gold/10 text-gold"
                      : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                  }`}
                >
                  <item.icon className="h-3.5 w-3.5" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </header>

        <div className="mx-auto max-w-[1280px] px-6 py-8 sm:px-8 lg:px-8">
          {children}
        </div>
      </main>
    </div>
  );
}

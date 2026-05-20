"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  BookOpen,
  Brush,
  Building2,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  DollarSign,
  LayoutDashboard,
  Link2,
  MessageSquare,
  Settings,
  Users,
  Wallet,
} from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/components/auth-provider";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/reservas", label: "Reservas", icon: ClipboardList },
  { href: "/calendario", label: "Calendario", icon: CalendarDays },
  { href: "/propiedades", label: "Propiedades", icon: Building2 },
  { href: "/clientes", label: "Clientes", icon: Users },
  { href: "/finanzas", label: "Finanzas", icon: DollarSign },
  { href: "/pagos", label: "Pagos", icon: Wallet },
  { href: "/contabilidad", label: "Contabilidad", icon: BookOpen },
  { href: "/tareas", label: "Tareas", icon: Brush },
  { href: "/plantillas", label: "Plantillas", icon: MessageSquare },
  { href: "/integraciones", label: "Integraciones", icon: Link2 },
  { href: "/settings", label: "Settings", icon: Settings },
];

const cleanerNavItems = [
  { href: "/tareas", label: "Mis tareas", icon: Brush },
  { href: "/settings", label: "Mi cuenta", icon: Settings },
];

function isNavItemActive(pathname: string, href: string) {
  return pathname === href || (href !== "/" && pathname.startsWith(`${href}/`));
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const { me } = useAuth();
  const isCleaner = me?.user.system_role === "CLEANER";
  const items = isCleaner ? cleanerNavItems : navItems;

  return (
    <div className="flex h-screen overflow-hidden">
      <motion.aside
        animate={{ width: collapsed ? 72 : 260 }}
        transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
        className="relative flex shrink-0 flex-col border-r border-border bg-sidebar"
      >
        <div className="flex h-16 items-center gap-3 border-b border-border px-5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-gold to-gold-dark">
            <Building2 className="h-4 w-4 text-primary-foreground" />
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden whitespace-nowrap"
              >
                <span className="font-serif text-lg font-semibold text-gold-gradient">
                  Emilamar
                </span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4">
          {items.map((item) => {
            const isActive = isNavItemActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group relative flex items-center gap-3 rounded-lg px-3 py-2.5 transition-all duration-200 ${
                  isActive
                    ? "bg-gold/10 text-gold"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                }`}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-gold"
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  />
                )}
                <item.icon className={`h-5 w-5 shrink-0 ${isActive ? "text-gold" : ""}`} />
                <AnimatePresence>
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.15 }}
                      className="whitespace-nowrap text-sm font-medium"
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </Link>
            );
          })}
        </nav>

        <button
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? "Expandir navegacion" : "Colapsar navegacion"}
          className="absolute -right-3 top-20 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-border bg-card text-muted-foreground transition-colors hover:border-gold/30 hover:text-gold"
        >
          {collapsed ? (
            <ChevronRight className="h-3 w-3" />
          ) : (
            <ChevronLeft className="h-3 w-3" />
          )}
        </button>

        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="border-t border-border p-4"
            >
              <div className="glass-card rounded-lg p-3">
                <p className="text-xs text-muted-foreground">Property Manager</p>
                <p className="mt-0.5 text-xs font-medium text-gold">Plan Premium</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.aside>

      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1600px] p-6 lg:p-8">{children}</div>
      </main>
    </div>
  );
}

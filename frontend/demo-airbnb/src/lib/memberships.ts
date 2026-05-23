import type { LucideIcon } from "lucide-react";
import { Building2, Crown, Sparkles } from "lucide-react";

export type MembershipTierId = "starter" | "growth" | "max";

export type MembershipTier = {
  id: MembershipTierId;
  name: string;
  priceUsd: number;
  summary: string;
  icon: LucideIcon;
  accentClass: string;
  limits: {
    properties: string;
    users: string;
    automations: string;
  };
  features: string[];
};

export const MEMBERSHIP_TIERS: MembershipTier[] = [
  {
    id: "starter",
    name: "Starter",
    priceUsd: 20,
    summary: "Operaciones basicas para una cartera pequena.",
    icon: Building2,
    accentClass: "border-emerald-400/20 bg-emerald-400/10 text-emerald-300",
    limits: {
      properties: "3 propiedades",
      users: "2 usuarios",
      automations: "1 integracion",
    },
    features: [
      "Dashboard operativo",
      "Calendario de reservas",
      "Inventario de propiedades",
      "Soporte por email",
    ],
  },
  {
    id: "growth",
    name: "Growth",
    priceUsd: 100,
    summary: "Gestion completa para equipos en expansion.",
    icon: Sparkles,
    accentClass: "border-blue-400/20 bg-blue-400/10 text-blue-300",
    limits: {
      properties: "20 propiedades",
      users: "8 usuarios",
      automations: "5 integraciones",
    },
    features: [
      "Todo Starter",
      "Finanzas y reportes",
      "Vouchers y PDFs",
      "Permisos por modulo",
    ],
  },
  {
    id: "max",
    name: "Max",
    priceUsd: 300,
    summary: "Capacidad maxima para testing y operaciones avanzadas.",
    icon: Crown,
    accentClass: "border-gold/35 bg-gold/15 text-gold",
    limits: {
      properties: "Sin limite operativo",
      users: "Usuarios ilimitados",
      automations: "Integraciones ilimitadas",
    },
    features: [
      "Todo Growth",
      "Acceso completo por defecto",
      "Sin limites durante testing",
      "Prioridad en nuevas integraciones",
    ],
  },
];

export const ACTIVE_TEST_MEMBERSHIP_TIER_ID: MembershipTierId = "max";

export function getActiveMembershipTier() {
  return (
    MEMBERSHIP_TIERS.find((tier) => tier.id === ACTIVE_TEST_MEMBERSHIP_TIER_ID) ??
    MEMBERSHIP_TIERS[MEMBERSHIP_TIERS.length - 1]
  );
}

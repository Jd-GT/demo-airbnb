"use client";

import AppShell from "@/components/app-shell";
import {
  ACTIVE_TEST_MEMBERSHIP_TIER_ID,
  MEMBERSHIP_TIERS,
  getActiveMembershipTier,
} from "@/lib/memberships";
import { motion } from "framer-motion";
import {
  BadgeCheck,
  Check,
  CreditCard,
  LockKeyhole,
  ShieldCheck,
  Users,
} from "lucide-react";
import { useMemo, useState } from "react";

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0 },
};

function formatUsd(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export default function MembershipsPage() {
  const activeTier = getActiveMembershipTier();
  const [selectedTierId, setSelectedTierId] = useState(activeTier.id);

  const selectedTier = useMemo(
    () =>
      MEMBERSHIP_TIERS.find((tier) => tier.id === selectedTierId) ?? activeTier,
    [activeTier, selectedTierId],
  );

  return (
    <AppShell>
      <motion.div variants={containerVariants} initial="hidden" animate="show">
        <motion.div
          variants={itemVariants}
          className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"
        >
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-gold/80">
              Billing
            </p>
            <h1 className="font-serif text-3xl font-semibold text-gold-gradient">
              Memberships
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Planes de acceso para equipos y carteras de propiedades.
            </p>
          </div>

          <div className="glass-card flex items-center gap-3 rounded-lg px-4 py-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gold/10 text-gold">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Testing activo</p>
              <p className="text-sm font-semibold text-foreground">
                Todos los usuarios tienen {activeTier.name}
              </p>
            </div>
          </div>
        </motion.div>

        <motion.div
          variants={itemVariants}
          className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3"
        >
          <div className="glass-card rounded-lg p-4">
            <p className="text-xs text-muted-foreground">Plan actual</p>
            <p className="mt-1 text-xl font-semibold text-gold">
              {activeTier.name}
            </p>
          </div>
          <div className="glass-card rounded-lg p-4">
            <p className="text-xs text-muted-foreground">Usuarios</p>
            <p className="mt-1 text-xl font-semibold text-foreground">
              {activeTier.limits.users}
            </p>
          </div>
          <div className="glass-card rounded-lg p-4">
            <p className="text-xs text-muted-foreground">Precio base</p>
            <p className="mt-1 text-xl font-semibold text-foreground">
              {formatUsd(activeTier.priceUsd)}
              <span className="ml-1 text-xs font-medium text-muted-foreground">
                /mes
              </span>
            </p>
          </div>
        </motion.div>

        <motion.div
          variants={containerVariants}
          className="grid grid-cols-1 gap-5 lg:grid-cols-3"
        >
          {MEMBERSHIP_TIERS.map((tier) => {
            const isActive = tier.id === ACTIVE_TEST_MEMBERSHIP_TIER_ID;
            const isSelected = selectedTier.id === tier.id;
            const TierIcon = tier.icon;

            return (
              <motion.article
                key={tier.id}
                variants={itemVariants}
                className={`glass-card glass-card-hover relative flex min-h-[520px] flex-col rounded-xl p-5 ${
                  isActive ? "border-gold/35 shadow-[0_18px_48px_rgba(201,162,39,0.08)]" : ""
                }`}
              >
                {isActive ? (
                  <div className="absolute right-4 top-4 flex items-center gap-1 rounded-full border border-gold/30 bg-gold/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-gold">
                    <BadgeCheck className="h-3 w-3" />
                    Activo
                  </div>
                ) : null}

                <div
                  className={`mb-5 flex h-11 w-11 items-center justify-center rounded-lg border ${tier.accentClass}`}
                >
                  <TierIcon className="h-5 w-5" />
                </div>

                <div className="mb-5">
                  <h2 className="text-lg font-semibold text-foreground">
                    {tier.name}
                  </h2>
                  <p className="mt-2 min-h-10 text-sm leading-relaxed text-muted-foreground">
                    {tier.summary}
                  </p>
                </div>

                <div className="mb-6 flex items-end gap-1">
                  <span className="text-4xl font-semibold tracking-normal text-foreground">
                    {formatUsd(tier.priceUsd)}
                  </span>
                  <span className="pb-1 text-sm text-muted-foreground">/mes</span>
                </div>

                <div className="mb-6 grid gap-2 rounded-lg border border-border bg-muted/20 p-3">
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span className="flex items-center gap-2 text-muted-foreground">
                      <CreditCard className="h-4 w-4" />
                      Propiedades
                    </span>
                    <span className="text-right font-medium text-foreground">
                      {tier.limits.properties}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span className="flex items-center gap-2 text-muted-foreground">
                      <Users className="h-4 w-4" />
                      Usuarios
                    </span>
                    <span className="text-right font-medium text-foreground">
                      {tier.limits.users}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span className="flex items-center gap-2 text-muted-foreground">
                      <LockKeyhole className="h-4 w-4" />
                      Integraciones
                    </span>
                    <span className="text-right font-medium text-foreground">
                      {tier.limits.automations}
                    </span>
                  </div>
                </div>

                <ul className="mb-6 space-y-3">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2 text-sm">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-gold" />
                      <span className="text-muted-foreground">{feature}</span>
                    </li>
                  ))}
                </ul>

                <button
                  type="button"
                  onClick={() => setSelectedTierId(tier.id)}
                  disabled={isActive}
                  className={`mt-auto rounded-lg px-4 py-2.5 text-sm font-medium transition-colors disabled:cursor-default ${
                    isActive
                      ? "bg-gold text-primary-foreground"
                      : isSelected
                        ? "border border-gold/30 bg-gold/10 text-gold hover:bg-gold/20"
                        : "border border-border bg-muted/20 text-foreground hover:bg-muted/40"
                  }`}
                >
                  {isActive ? "Activo en testing" : isSelected ? "Seleccionado" : "Ver detalle"}
                </button>
              </motion.article>
            );
          })}
        </motion.div>
      </motion.div>
    </AppShell>
  );
}

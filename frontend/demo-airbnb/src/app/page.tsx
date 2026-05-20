import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  CalendarCheck,
  ChartNoAxesCombined,
  House,
  ShieldCheck,
} from "lucide-react";

const heroImage =
  "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=1800&q=85";

const highlights = [
  {
    title: "Reservas centralizadas",
    detail: "Calendario, ocupacion y estados de reserva en un solo flujo.",
    icon: CalendarCheck,
  },
  {
    title: "Control financiero",
    detail: "Ingresos, rentabilidad y metricas por propiedad listos para operar.",
    icon: ChartNoAxesCombined,
  },
  {
    title: "Tenants seguros",
    detail: "Acceso por cuenta, roles y contexto multi-tenant desde el primer dia.",
    icon: ShieldCheck,
  },
];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <section className="relative flex min-h-[82svh] overflow-hidden">
        <Image
          src={heroImage}
          alt="Alojamiento turistico con piscina listo para reservas"
          fill
          priority
          sizes="100vw"
          className="object-cover"
        />
        <div className="absolute inset-0 bg-[rgba(7,18,19,0.68)]" />
        <div className="relative z-10 mx-auto flex w-full max-w-[1280px] flex-col px-6 py-6 sm:px-8">
          <header className="flex items-center justify-between gap-4">
            <Link href="/" className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-gold text-primary-foreground">
                <House className="h-5 w-5" />
              </span>
              <span className="font-serif text-xl font-semibold text-white">
                Emilamar
              </span>
            </Link>
            <nav className="flex items-center gap-2">
              <Link
                href="/login"
                className="rounded-md px-4 py-2 text-sm font-medium text-white/85 transition-colors hover:bg-white/10 hover:text-white"
              >
                Entrar
              </Link>
              <Link
                href="/signup"
                className="rounded-md bg-gold px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-gold-dark"
              >
                Crear cuenta
              </Link>
            </nav>
          </header>

          <div className="flex flex-1 items-center py-16">
            <div className="max-w-3xl">
              <p className="mb-4 text-sm font-semibold uppercase tracking-[0.22em] text-gold-light">
                Property Manager
              </p>
              <h1 className="font-serif text-5xl font-semibold leading-[0.98] text-white sm:text-6xl lg:text-7xl">
                Emilamar Alojamientos
              </h1>
              <p className="mt-6 max-w-2xl text-base leading-7 text-white/78 sm:text-lg">
                Gestiona propiedades, reservas e ingresos desde una plataforma
                multi-tenant disenada para equipos de alojamiento turistico.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  href="/signup"
                  className="inline-flex items-center gap-2 rounded-md bg-gold px-5 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-gold-dark"
                >
                  Crear cuenta
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 rounded-md border border-white/35 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-white/10"
                >
                  Iniciar sesion
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-border bg-background px-6 py-10 sm:px-8">
        <div className="mx-auto grid max-w-[1280px] gap-4 md:grid-cols-3">
          {highlights.map((item) => (
            <article
              key={item.title}
              className="rounded-lg border border-border bg-card p-5"
            >
              <item.icon className="h-5 w-5 text-gold" />
              <h2 className="mt-4 text-base font-semibold text-foreground">
                {item.title}
              </h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {item.detail}
              </p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

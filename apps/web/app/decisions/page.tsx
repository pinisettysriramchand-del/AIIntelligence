"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppNav } from "@/components/AppNav";
import { api, getTokens } from "@/lib/api";

type DecisionCard = {
  id: string;
  kpi_name: string;
  current_value: string;
  unit?: string | null;
  trend: string;
  health: string;
  recommendation: string;
  what_happened: string;
};

export default function DecisionsPage() {
  const router = useRouter();
  const [cards, setCards] = useState<DecisionCard[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getTokens()) {
      router.replace("/login");
      return;
    }
    api<DecisionCard[]>("/api/decisions/cards")
      .then(setCards)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, [router]);

  return (
    <main>
      <AppNav />
      <h1 className="hero-title">Decision Cards</h1>
      <p className="lead">What happened, why it happened, and what to do next for each KPI.</p>
      {error && <p className="error">{error}</p>}
      <section className="panel">
        {cards.length === 0 && <p className="muted">No cards yet. Generate from the dashboard.</p>}
        {cards.map((card) => (
          <div className="kpi-row" key={card.id}>
            <div>
              <Link href={`/decisions/${card.id}`}>
                <strong>{card.kpi_name}</strong>
              </Link>
              <div className="muted">
                {card.health} · {card.trend}
              </div>
              <div>{card.what_happened}</div>
            </div>
            <div>
              {card.current_value}
              {card.unit ? ` ${card.unit}` : ""}
            </div>
          </div>
        ))}
      </section>
    </main>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AppNav } from "@/components/AppNav";
import { api, getTokens } from "@/lib/api";

type DecisionCard = {
  id: string;
  kpi_name: string;
  current_value: string;
  unit?: string | null;
  period?: string | null;
  domain?: string | null;
  trend: string;
  health: string;
  what_happened: string;
  why_it_happened: string;
  risks: string[];
  opportunities: string[];
  recommendation: string;
  forecast_value?: string | null;
  forecast_horizon?: string | null;
  forecast_explanation?: string | null;
  evidence_chunk_ids: string[];
};

export default function DecisionCardPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [card, setCard] = useState<DecisionCard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getTokens()) {
      router.replace("/login");
      return;
    }
    api<DecisionCard>(`/api/decisions/cards/${params.id}`)
      .then(setCard)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, [params.id, router]);

  return (
    <main>
      <AppNav />
      {error && <p className="error">{error}</p>}
      {card && (
        <>
          <h1 className="hero-title">{card.kpi_name}</h1>
          <p className="lead">
            {card.current_value}
            {card.unit ? ` ${card.unit}` : ""} · {card.period || "n/a"} · {card.domain || "General"}
          </p>
          <section className="grid" style={{ marginTop: 20 }}>
            <div className="stat">
              <span className="muted">Trend</span>
              <strong>{card.trend}</strong>
            </div>
            <div className="stat">
              <span className="muted">Health</span>
              <strong>{card.health}</strong>
            </div>
          </section>
          <section className="panel">
            <h2>What happened</h2>
            <p>{card.what_happened}</p>
            <h2>Why it happened</h2>
            <p>{card.why_it_happened}</p>
            <h2>Risks</h2>
            <ul>
              {card.risks.map((risk) => (
                <li key={risk}>{risk}</li>
              ))}
            </ul>
            <h2>Opportunities</h2>
            <ul>
              {card.opportunities.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <h2>Recommendation</h2>
            <p>{card.recommendation}</p>
            <h2>Forecast</h2>
            <p>
              {card.forecast_value || "—"} ({card.forecast_horizon || "n/a"})
            </p>
            <p className="muted">{card.forecast_explanation}</p>
            <h2>Evidence</h2>
            <p className="muted">{card.evidence_chunk_ids.join(", ") || "None"}</p>
          </section>
        </>
      )}
    </main>
  );
}

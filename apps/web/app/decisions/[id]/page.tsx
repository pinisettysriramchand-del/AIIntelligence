"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AppNav } from "@/components/AppNav";
import { api, getTokens } from "@/lib/api";

type DecisionCard = {
  id: string;
  kpi_name: string;
  topic?: string;
  kpi_signal?: string;
  current_value: string;
  unit?: string | null;
  period?: string | null;
  domain?: string | null;
  trend: string;
  health: string;
  what_happened: string;
  why_it_happened: string;
  business_impact: string;
  risks: string[];
  opportunities: string[];
  recommendation: string;
  expected_outcome?: string;
  forecast_value?: string | null;
  forecast_horizon?: string | null;
  forecast_explanation?: string | null;
  confidence: number;
  evidence_mode: string;
  evidence_chunk_ids: string[];
};

export default function DecisionCardPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [card, setCard] = useState<DecisionCard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getTokens()) {
      router.replace("/login");
      return;
    }
    setLoading(true);
    api<DecisionCard>(`/api/v1/decisions/cards/${params.id}`)
      .then(setCard)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [params.id, router]);

  return (
    <main>
      <AppNav />
      {loading && <p className="muted">Loading decision card…</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && !card && <p className="muted">Decision card not found.</p>}
      {card && (
        <>
          <h1 className="hero-title">{card.topic || card.kpi_name}</h1>
          <p className="lead">{card.kpi_signal || `${card.kpi_name}: ${card.current_value}`}</p>
          {card.evidence_mode === "insufficient" && (
            <p className="error">Insufficient evidence for a fully grounded recommendation.</p>
          )}
          <section className="grid" style={{ marginTop: 20 }}>
            <div className="stat">
              <span className="muted">Trend</span>
              <strong>{card.trend}</strong>
            </div>
            <div className="stat">
              <span className="muted">Health</span>
              <strong>{card.health}</strong>
            </div>
            <div className="stat">
              <span className="muted">Confidence</span>
              <strong>{(card.confidence * 100).toFixed(0)}%</strong>
            </div>
            <div className="stat">
              <span className="muted">Evidence mode</span>
              <strong>{card.evidence_mode}</strong>
            </div>
          </section>
          <section className="panel">
            <h2>What happened</h2>
            <p>{card.what_happened}</p>
            <h2>Why it happened</h2>
            <p>{card.why_it_happened}</p>
            <h2>Business impact</h2>
            <p>{card.business_impact}</p>
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
            <h2>Expected outcome</h2>
            <p>{card.expected_outcome || "Outcome not specified from evidence."}</p>
            <h2>Forecast</h2>
            {card.forecast_value ? (
              <>
                <p>
                  {card.forecast_value} ({card.forecast_horizon || "n/a"})
                </p>
                <p className="muted">{card.forecast_explanation}</p>
              </>
            ) : (
              <p className="error">
                {card.forecast_explanation ||
                  "Insufficient historical data to produce a forecast."}
              </p>
            )}
            <h2>Evidence</h2>
            <p className="muted">{card.evidence_chunk_ids.join(", ") || "None"}</p>
          </section>
        </>
      )}
    </main>
  );
}

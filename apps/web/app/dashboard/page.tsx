"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppNav } from "@/components/AppNav";
import { api, getTokens } from "@/lib/api";

type DashboardApi = {
  total_kpis: number;
  domains: Array<{
    domain: string;
    kpi_count: number;
    kpis: Array<{
      id: string;
      name: string;
      value: string;
      unit?: string | null;
      period?: string | null;
      trend?: string;
      business_meaning?: string | null;
      confidence?: number;
      comparison?: {
        previous_period?: string | null;
        previous_value?: string;
        delta_label?: string;
        trend?: string;
      } | null;
    }>;
  }>;
};

type DocumentRow = {
  id: string;
  filename: string;
  status: string;
  domain?: string | null;
};

type DecisionCard = {
  id: string;
  kpi_name: string;
  current_value: string;
  unit?: string | null;
  trend: string;
  health: string;
  recommendation: string;
};

type Executive = {
  summary: string;
  health_score: number;
  health_label: string;
  timeline: Array<{ title: string; detail: string; severity?: string }>;
};

type DashboardView = {
  summary: {
    ready_documents: number;
    kpi_count: number;
    health_score?: number | null;
    health_label?: string | null;
    decision_card_count: number;
  };
  executive_summary?: string | null;
  timeline: Executive["timeline"];
  decision_cards: DecisionCard[];
  kpis: Array<{
    id: string;
    name: string;
    value: string;
    unit?: string | null;
    period?: string | null;
    domain?: string | null;
    trend?: string;
    business_meaning?: string | null;
    confidence?: number;
    comparison?: {
      previous_period?: string | null;
      previous_value?: string;
      delta_label?: string;
      trend?: string;
    } | null;
  }>;
};

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<DashboardView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

  async function load() {
    const [dashboard, documents, cards, executive] = await Promise.all([
      api<DashboardApi>("/api/v1/dashboard"),
      api<DocumentRow[]>("/api/v1/documents").catch(() => [] as DocumentRow[]),
      api<DecisionCard[]>("/api/v1/decisions/cards").catch(() => [] as DecisionCard[]),
      api<Executive>("/api/v1/decisions/executive").catch(() => null),
    ]);

    const kpis = dashboard.domains.flatMap((d) =>
      d.kpis.map((kpi) => ({
        ...kpi,
        domain: d.domain,
      })),
    );

    setData({
      summary: {
        ready_documents: documents.filter((d) => d.status === "ready").length,
        kpi_count: dashboard.total_kpis,
        health_score: executive?.health_score ?? null,
        health_label: executive?.health_label ?? null,
        decision_card_count: cards.length,
      },
      executive_summary: executive?.summary ?? null,
      timeline: executive?.timeline ?? [],
      decision_cards: cards,
      kpis,
    });
  }

  useEffect(() => {
    if (!getTokens()) {
      router.replace("/login");
      return;
    }
    load().catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, [router]);

  async function generateDecisions() {
    setGenerating(true);
    setError(null);
    try {
      await api("/api/v1/decisions/generate", { method: "POST", body: JSON.stringify({}) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <main>
      <AppNav />
      <h1 className="hero-title">Executive Dashboard</h1>
      <p className="lead">
        Business health, decision timeline, and KPI intelligence for leadership review.
      </p>

      {error && <p className="error">{error}</p>}

      {data && (
        <>
          <section className="grid" style={{ marginTop: 24 }}>
            <div className="stat">
              <span className="muted">Business Health</span>
              <strong>
                {data.summary.health_score != null
                  ? `${data.summary.health_score} · ${data.summary.health_label}`
                  : "—"}
              </strong>
            </div>
            <div className="stat">
              <span className="muted">Decision Cards</span>
              <strong>{data.summary.decision_card_count}</strong>
            </div>
            <div className="stat">
              <span className="muted">KPIs</span>
              <strong>{data.summary.kpi_count}</strong>
            </div>
            <div className="stat">
              <span className="muted">Ready Documents</span>
              <strong>{data.summary.ready_documents}</strong>
            </div>
          </section>

          <section className="panel">
            <div className="kpi-row">
              <h2 style={{ margin: 0 }}>Executive Summary</h2>
              <button onClick={generateDecisions} disabled={generating}>
                {generating ? "Generating…" : "Generate Decision Intelligence"}
              </button>
            </div>
            <p>
              {data.executive_summary ||
                "Generate Decision Intelligence to produce the executive summary."}
            </p>
          </section>

          <section className="panel">
            <h2>Decision Timeline</h2>
            {data.timeline.length === 0 && <p className="muted">No timeline events yet.</p>}
            {data.timeline.map((event, index) => (
              <div className="kpi-row" key={`${event.title}-${index}`}>
                <div>
                  <strong>{event.title}</strong>
                  <div className="muted">{event.detail}</div>
                </div>
                <div className="muted">{event.severity || "medium"}</div>
              </div>
            ))}
          </section>

          <section className="panel">
            <h2>Decision Cards</h2>
            {data.decision_cards.length === 0 && (
              <p className="muted">No decision cards yet.</p>
            )}
            {data.decision_cards.map((card) => (
              <div className="kpi-row" key={card.id}>
                <div>
                  <Link href={`/decisions/${card.id}`}>
                    <strong>{card.kpi_name}</strong>
                  </Link>
                  <div className="muted">
                    {card.trend} · {card.health}
                  </div>
                  <div className="muted">{card.recommendation}</div>
                </div>
                <div>
                  {card.current_value}
                  {card.unit ? ` ${card.unit}` : ""}
                </div>
              </div>
            ))}
          </section>

          <section className="panel">
            <h2>Top KPIs</h2>
            {data.kpis.length === 0 && <p className="muted">No KPIs extracted yet.</p>}
            {data.kpis.map((kpi) => (
              <div className="kpi-row" key={kpi.id}>
                <div>
                  <strong>{kpi.name}</strong>
                  <div className="muted">
                    {kpi.domain || "General"}
                    {kpi.period ? ` · ${kpi.period}` : ""}
                    {kpi.trend && kpi.trend !== "unknown" ? ` · trend ${kpi.trend}` : ""}
                    {kpi.confidence != null ? ` · conf ${(kpi.confidence * 100).toFixed(0)}%` : ""}
                  </div>
                  {kpi.business_meaning && <div className="muted">{kpi.business_meaning}</div>}
                  {kpi.comparison && (
                    <div className="muted">
                      vs {kpi.comparison.previous_period || "prior"}:{" "}
                      {kpi.comparison.previous_value}
                      {kpi.unit ? ` ${kpi.unit}` : ""} ({kpi.comparison.delta_label})
                    </div>
                  )}
                </div>
                <div>
                  {kpi.value}
                  {kpi.unit ? ` ${kpi.unit}` : ""}
                </div>
              </div>
            ))}
          </section>
        </>
      )}
    </main>
  );
}

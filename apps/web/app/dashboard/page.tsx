"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppNav } from "@/components/AppNav";
import { api, getTokens } from "@/lib/api";

type Dashboard = {
  summary: {
    document_count: number;
    ready_documents: number;
    processing_documents: number;
    failed_documents: number;
    kpi_count: number;
    domains: string[];
    health_score?: number | null;
    health_label?: string | null;
    decision_card_count?: number;
  };
  executive_summary?: string | null;
  timeline?: Array<{ title: string; detail: string; severity?: string }>;
  decision_cards?: Array<{
    id: string;
    kpi_name: string;
    current_value: string;
    unit?: string | null;
    trend: string;
    health: string;
    recommendation: string;
  }>;
  kpis: Array<{
    id: string;
    name: string;
    value: string;
    unit?: string | null;
    period?: string | null;
    domain?: string | null;
  }>;
  documents: Array<{
    id: string;
    filename: string;
    status: string;
    domain?: string | null;
  }>;
};

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

  async function load() {
    const dashboard = await api<Dashboard>("/api/v1/dashboard");
    setData(dashboard);
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
              <strong>{data.summary.decision_card_count ?? 0}</strong>
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
            <p>{data.executive_summary || "Generate Decision Intelligence to produce the executive summary."}</p>
          </section>

          <section className="panel">
            <h2>Decision Timeline</h2>
            {(data.timeline || []).length === 0 && <p className="muted">No timeline events yet.</p>}
            {(data.timeline || []).map((event, index) => (
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
            {(data.decision_cards || []).length === 0 && (
              <p className="muted">No decision cards yet.</p>
            )}
            {(data.decision_cards || []).map((card) => (
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
            {data.kpis.map((kpi) => (
              <div className="kpi-row" key={kpi.id}>
                <div>
                  <strong>{kpi.name}</strong>
                  <div className="muted">
                    {kpi.domain || "General"}
                    {kpi.period ? ` · ${kpi.period}` : ""}
                  </div>
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

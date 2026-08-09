"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AppNav } from "@/components/AppNav";
import { RankedBarChart } from "@/components/charts/BarChart";
import { HealthMeter } from "@/components/charts/HealthMeter";
import { SparkLine } from "@/components/charts/SparkLine";
import { api, getTokens } from "@/lib/api";
import { parseNumeric, trendPoints } from "@/lib/charts";

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
  data_quality_warnings?: Array<{
    code: string;
    message: string;
    kpi_name?: string | null;
    severity?: string;
    document_id?: string;
    document_filename?: string;
  }>;
};

type DocumentRow = {
  id: string;
  filename: string;
  status: string;
};

type DecisionCard = {
  id: string;
  kpi_name: string;
  topic?: string;
  kpi_signal?: string;
  current_value: string;
  unit?: string | null;
  trend: string;
  health: string;
  recommendation: string;
  expected_outcome?: string;
  risks?: string[];
  opportunities?: string[];
  business_impact?: string;
  confidence?: number;
  forecast_value?: string | null;
  forecast_horizon?: string | null;
};

type Executive = {
  summary: string;
  health_score: number;
  health_label: string;
  timeline: Array<{ title: string; detail: string; severity?: string }>;
};

type KpiRow = {
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
  data_quality_warnings: NonNullable<DashboardApi["data_quality_warnings"]>;
  kpis: KpiRow[];
  domainCounts: Array<{ domain: string; count: number }>;
};

function healthRank(health: string): number {
  if (health === "critical") return 0;
  if (health === "watch") return 1;
  return 2;
}

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<DashboardView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

  async function load() {
    const [dashboard, documents, cards, executive] = await Promise.all([
      api<DashboardApi>("/api/v1/dashboard"),
      api<{ items?: DocumentRow[] } | DocumentRow[]>("/api/v1/documents").catch(() => []),
      api<DecisionCard[]>("/api/v1/decisions/cards").catch(() => [] as DecisionCard[]),
      api<Executive>("/api/v1/decisions/executive").catch(() => null),
    ]);

    const docList = Array.isArray(documents)
      ? documents
      : Array.isArray(documents.items)
        ? documents.items
        : [];

    const kpis = dashboard.domains.flatMap((d) =>
      d.kpis.map((kpi) => ({
        ...kpi,
        domain: d.domain,
      })),
    );

    setData({
      summary: {
        ready_documents: docList.filter((d) => d.status === "ready").length,
        kpi_count: dashboard.total_kpis,
        health_score: executive?.health_score ?? null,
        health_label: executive?.health_label ?? null,
        decision_card_count: cards.length,
      },
      executive_summary: executive?.summary ?? null,
      timeline: executive?.timeline ?? [],
      decision_cards: cards,
      data_quality_warnings: dashboard.data_quality_warnings || [],
      kpis,
      domainCounts: dashboard.domains.map((d) => ({
        domain: d.domain,
        count: d.kpi_count,
      })),
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

  const primaryKpi = useMemo(() => {
    if (!data?.kpis.length) return null;
    const withCompare = data.kpis.find((k) => k.comparison?.previous_value);
    return withCompare || data.kpis[0];
  }, [data]);

  const majorRisk = useMemo(() => {
    if (!data?.decision_cards.length) return null;
    const sorted = [...data.decision_cards].sort(
      (a, b) => healthRank(a.health) - healthRank(b.health),
    );
    const card = sorted[0];
    const risk = card.risks?.[0];
    return { card, text: risk || card.business_impact || card.recommendation };
  }, [data]);

  const majorOpportunity = useMemo(() => {
    if (!data?.decision_cards.length) return null;
    const withOpp = data.decision_cards.find((c) => (c.opportunities?.length || 0) > 0);
    const card = withOpp || data.decision_cards[0];
    return {
      card,
      text: card.opportunities?.[0] || card.expected_outcome || card.recommendation,
    };
  }, [data]);

  const primaryTrend = useMemo(() => {
    if (!primaryKpi) return null;
    const card = data?.decision_cards.find(
      (c) => c.kpi_name.toLowerCase() === primaryKpi.name.toLowerCase(),
    );
    return trendPoints({
      name: primaryKpi.name,
      current: primaryKpi.value,
      previous: primaryKpi.comparison?.previous_value,
      previousPeriod: primaryKpi.comparison?.previous_period,
      period: primaryKpi.period,
      forecast: card?.forecast_value,
      forecastHorizon: card?.forecast_horizon,
    });
  }, [primaryKpi, data]);

  const driverBars = useMemo(() => {
    if (!data?.decision_cards.length) return [];
    return [...data.decision_cards]
      .slice(0, 5)
      .map((c) => ({
        label: c.topic || c.kpi_name,
        value: c.confidence != null ? c.confidence * 100 : healthRank(c.health) === 0 ? 90 : 55,
        hint: `${c.health}${c.confidence != null ? ` · ${(c.confidence * 100).toFixed(0)}%` : ""}`,
      }));
  }, [data]);

  const domainBars = useMemo(() => {
    if (!data?.domainCounts.length) return [];
    return data.domainCounts.map((d) => ({
      label: d.domain,
      value: d.count,
      hint: `${d.count} KPIs`,
    }));
  }, [data]);

  return (
    <main>
      <AppNav />
      <h1 className="hero-title">Executive Dashboard</h1>
      <p className="lead">
        Level 1 signal, Level 2 explanation, and Level 3 actions — with minimal charts for trends
        and composition.
      </p>

      {error && <p className="error">{error}</p>}

      {data && (
        <>
          {/* ── L1 Executive Signal ─────────────────────────────────────── */}
          <section className="panel layer-panel" aria-labelledby="l1-title">
            <p className="layer-eyebrow" id="l1-title">
              Level 1 — Executive Signal
            </p>
            <div className="l1-grid">
              <div>
                <h2 className="layer-heading">Business Health</h2>
                <HealthMeter
                  score={data.summary.health_score}
                  label={data.summary.health_label}
                />
                <p className="muted" style={{ marginTop: 12 }}>
                  {data.executive_summary ||
                    "Generate Decision Intelligence to produce the executive summary."}
                </p>
              </div>
              <div>
                <h2 className="layer-heading">Primary KPI</h2>
                {primaryKpi ? (
                  <>
                    <strong className="l1-kpi-name">{primaryKpi.name}</strong>
                    <div className="l1-kpi-value">
                      {primaryKpi.value}
                      {primaryKpi.unit ? ` ${primaryKpi.unit}` : ""}
                    </div>
                    <p className="muted">
                      {primaryKpi.business_meaning ||
                        `${primaryKpi.domain || "General"}${
                          primaryKpi.period ? ` · ${primaryKpi.period}` : ""
                        }`}
                    </p>
                  </>
                ) : (
                  <p className="muted">No KPIs extracted yet.</p>
                )}
              </div>
              <div className="l1-risk-opp">
                <div>
                  <h2 className="layer-heading">Major risk</h2>
                  {majorRisk ? (
                    <>
                      <p>{majorRisk.text}</p>
                      <Link className="text-link" href={`/decisions/${majorRisk.card.id}`}>
                        Open card
                      </Link>
                    </>
                  ) : (
                    <p className="muted">No risks surfaced yet.</p>
                  )}
                </div>
                <div>
                  <h2 className="layer-heading">Major opportunity</h2>
                  {majorOpportunity ? (
                    <>
                      <p>{majorOpportunity.text}</p>
                      <Link
                        className="text-link"
                        href={`/decisions/${majorOpportunity.card.id}`}
                      >
                        Open card
                      </Link>
                    </>
                  ) : (
                    <p className="muted">No opportunities surfaced yet.</p>
                  )}
                </div>
              </div>
            </div>
            <div className="grid" style={{ marginTop: 16 }}>
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
            </div>
          </section>

          {/* ── L2 Explanation ──────────────────────────────────────────── */}
          <section className="panel layer-panel" aria-labelledby="l2-title">
            <p className="layer-eyebrow" id="l2-title">
              Level 2 — Explanation
            </p>
            <h2 className="layer-heading">Trends, drivers, and evidence</h2>

            {data.data_quality_warnings.length > 0 && (
              <div className="alert-strip">
                <strong>Data quality</strong>
                {data.data_quality_warnings.slice(0, 3).map((w, index) => (
                  <p
                    key={`${w.code}-${w.kpi_name || ""}-${index}`}
                    className={w.severity === "info" ? "muted" : "error"}
                  >
                    [{w.code}] {w.message}
                    {w.document_filename ? ` (${w.document_filename})` : ""}
                  </p>
                ))}
              </div>
            )}

            <div className="chart-grid">
              <div>
                <h3 className="chart-title">Primary KPI trend</h3>
                {primaryTrend ? (
                  <SparkLine
                    points={primaryTrend.points}
                    forecastFromIndex={primaryTrend.forecastFromIndex}
                    ariaLabel={`${primaryKpi?.name || "KPI"} trend`}
                  />
                ) : (
                  <p className="muted">
                    Need a prior period or forecast to draw a trend for the primary KPI.
                  </p>
                )}
                {primaryKpi?.comparison && (
                  <p className="muted">
                    vs {primaryKpi.comparison.previous_period || "prior"}:{" "}
                    {primaryKpi.comparison.previous_value}
                    {primaryKpi.unit ? ` ${primaryKpi.unit}` : ""} (
                    {primaryKpi.comparison.delta_label})
                  </p>
                )}
              </div>
              <div>
                <h3 className="chart-title">Domain composition</h3>
                <RankedBarChart bars={domainBars} ariaLabel="KPI counts by domain" />
              </div>
              <div>
                <h3 className="chart-title">Decision drivers</h3>
                <RankedBarChart
                  bars={driverBars}
                  ariaLabel="Decision cards ranked by confidence"
                />
              </div>
            </div>

            <h3 className="chart-title" style={{ marginTop: 20 }}>
              Top KPIs
            </h3>
            {data.kpis.length === 0 && <p className="muted">No KPIs extracted yet.</p>}
            {data.kpis.slice(0, 8).map((kpi) => {
              const cur = parseNumeric(kpi.value);
              const prev = parseNumeric(kpi.comparison?.previous_value);
              return (
                <div className="kpi-row" key={kpi.id}>
                  <div>
                    <strong>{kpi.name}</strong>
                    <div className="muted">
                      {kpi.domain || "General"}
                      {kpi.period ? ` · ${kpi.period}` : ""}
                      {kpi.trend && kpi.trend !== "unknown" ? ` · trend ${kpi.trend}` : ""}
                      {kpi.confidence != null
                        ? ` · conf ${(kpi.confidence * 100).toFixed(0)}%`
                        : ""}
                    </div>
                    {kpi.business_meaning && (
                      <div className="muted">{kpi.business_meaning}</div>
                    )}
                    {kpi.comparison && (
                      <div className="muted">
                        vs {kpi.comparison.previous_period || "prior"}:{" "}
                        {kpi.comparison.previous_value}
                        {kpi.unit ? ` ${kpi.unit}` : ""} ({kpi.comparison.delta_label})
                      </div>
                    )}
                    {cur != null && prev != null && (
                      <div className="mini-compare" aria-hidden>
                        <span style={{ width: `${Math.min(100, (prev / Math.max(cur, prev, 1)) * 100)}%` }} />
                        <span style={{ width: `${Math.min(100, (cur / Math.max(cur, prev, 1)) * 100)}%` }} />
                      </div>
                    )}
                  </div>
                  <div>
                    {kpi.value}
                    {kpi.unit ? ` ${kpi.unit}` : ""}
                  </div>
                </div>
              );
            })}

            <h3 className="chart-title" style={{ marginTop: 20 }}>
              Decision timeline
            </h3>
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

          {/* ── L3 Action ───────────────────────────────────────────────── */}
          <section className="panel layer-panel" aria-labelledby="l3-title">
            <div className="kpi-row" style={{ borderBottom: 0, paddingTop: 0 }}>
              <div>
                <p className="layer-eyebrow" id="l3-title">
                  Level 3 — Action
                </p>
                <h2 className="layer-heading" style={{ marginTop: 0 }}>
                  Decision cards & next steps
                </h2>
              </div>
              <button onClick={generateDecisions} disabled={generating}>
                {generating ? "Generating…" : "Generate Decision Intelligence"}
              </button>
            </div>

            {data.decision_cards.length === 0 && (
              <p className="muted">No decision cards yet. Generate Decision Intelligence first.</p>
            )}
            {data.decision_cards.map((card) => (
              <div className="action-card" key={card.id}>
                <div className="kpi-row" style={{ borderBottom: 0, padding: 0 }}>
                  <div>
                    <Link href={`/decisions/${card.id}`}>
                      <strong>{card.topic || card.kpi_name}</strong>
                    </Link>
                    <div className="muted">
                      {card.kpi_signal || `${card.trend} · ${card.health}`}
                    </div>
                  </div>
                  <div>
                    {card.current_value}
                    {card.unit ? ` ${card.unit}` : ""}
                  </div>
                </div>
                <p>
                  <span className="muted">Recommendation · </span>
                  {card.recommendation}
                </p>
                <p>
                  <span className="muted">Expected outcome · </span>
                  {card.expected_outcome || "Outcome not specified from evidence."}
                </p>
                <Link className="text-link" href={`/decisions/${card.id}`}>
                  Next step: review evidence & act →
                </Link>
              </div>
            ))}
          </section>
        </>
      )}
    </main>
  );
}

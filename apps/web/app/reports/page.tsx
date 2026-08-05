"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppNav } from "@/components/AppNav";
import { api, getTokens } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Executive = {
  id: string;
  summary: string;
  health_score: number;
  health_label: string;
  timeline: Array<{ title: string; detail: string; severity?: string }>;
};

type Forecast = {
  kpi_name: string;
  current_value: string;
  unit?: string | null;
  forecast_value?: string | null;
  forecast_horizon?: string | null;
  forecast_explanation?: string | null;
  trend: string;
};

export default function ReportsPage() {
  const router = useRouter();
  const [report, setReport] = useState<Executive | null>(null);
  const [forecasts, setForecasts] = useState<Forecast[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getTokens()) {
      router.replace("/login");
      return;
    }
    Promise.all([
      api<Executive>("/api/decisions/executive"),
      api<Forecast[]>("/api/forecasts"),
    ])
      .then(([executive, forecastItems]) => {
        setReport(executive);
        setForecasts(forecastItems);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, [router]);

  async function downloadPdf() {
    const tokens = getTokens();
    if (!tokens) return;
    const response = await fetch(`${API_URL}/api/reports/executive.pdf`, {
      headers: { Authorization: `Bearer ${tokens.access_token}` },
    });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "stratiq-executive-report.pdf";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main>
      <AppNav />
      <h1 className="hero-title">Executive Reports</h1>
      <p className="lead">Export an executive-ready PDF with health, timeline, and recommendations.</p>
      {error && <p className="error">{error}</p>}

      {report && (
        <section className="panel">
          <div className="kpi-row">
            <div>
              <h2 style={{ margin: 0 }}>Business Health</h2>
              <p className="muted">
                {report.health_label} · {report.health_score}/100
              </p>
            </div>
            <button onClick={downloadPdf}>Download PDF</button>
          </div>
          <p>{report.summary}</p>
        </section>
      )}

      <section className="panel">
        <h2>Forecasts</h2>
        {forecasts.length === 0 && <p className="muted">No forecasts yet.</p>}
        {forecasts.map((item) => (
          <div className="kpi-row" key={item.kpi_name}>
            <div>
              <strong>{item.kpi_name}</strong>
              <div className="muted">{item.forecast_explanation}</div>
            </div>
            <div>
              {item.current_value}
              {item.unit ? ` ${item.unit}` : ""} → {item.forecast_value || "—"} (
              {item.forecast_horizon || "n/a"})
            </div>
          </div>
        ))}
      </section>
    </main>
  );
}

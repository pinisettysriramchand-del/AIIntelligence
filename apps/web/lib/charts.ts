/** Shared helpers for Stage 4H dashboard charts. */

export function parseNumeric(raw: string | null | undefined): number | null {
  if (raw == null) return null;
  const cleaned = String(raw).replace(/,/g, "").replace(/[^0-9.+-eE]/g, "");
  if (!cleaned) return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

export function trendPoints(args: {
  name: string;
  current: string;
  previous?: string | null;
  previousPeriod?: string | null;
  period?: string | null;
  forecast?: string | null;
  forecastHorizon?: string | null;
}): { points: Array<{ label: string; value: number }>; forecastFromIndex?: number } | null {
  const current = parseNumeric(args.current);
  if (current == null) return null;
  const points: Array<{ label: string; value: number }> = [];
  const prev = parseNumeric(args.previous ?? undefined);
  if (prev != null) {
    points.push({ label: args.previousPeriod || "Prior", value: prev });
  }
  points.push({ label: args.period || "Now", value: current });
  const forecast = parseNumeric(args.forecast ?? undefined);
  let forecastFromIndex: number | undefined;
  if (forecast != null) {
    forecastFromIndex = points.length - 1;
    points.push({ label: args.forecastHorizon || "Forecast", value: forecast });
  }
  if (points.length < 2) return null;
  return { points, forecastFromIndex };
}

"use client";

type Bar = { label: string; value: number; hint?: string };

type Props = {
  bars: Bar[];
  height?: number;
  ariaLabel?: string;
};

/** Minimal horizontal ranked bar chart (drivers / composition). */
export function RankedBarChart({ bars, height = 28, ariaLabel = "Bar chart" }: Props) {
  if (bars.length === 0) {
    return <p className="muted">No series to chart.</p>;
  }
  const max = Math.max(...bars.map((b) => Math.abs(b.value)), 1);

  return (
    <div className="ranked-bars" role="img" aria-label={ariaLabel}>
      {bars.map((bar) => {
        const pct = Math.max(4, (Math.abs(bar.value) / max) * 100);
        return (
          <div className="ranked-bar-row" key={bar.label}>
            <div className="ranked-bar-meta">
              <span>{bar.label}</span>
              <span className="muted">{bar.hint ?? bar.value}</span>
            </div>
            <div className="ranked-bar-track" style={{ height }}>
              <div className="ranked-bar-fill" style={{ width: `${pct}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

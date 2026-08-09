"use client";

type Point = { label: string; value: number };

type Props = {
  points: Point[];
  width?: number;
  height?: number;
  accent?: string;
  forecastFromIndex?: number;
  ariaLabel?: string;
};

/** Minimal SVG line chart for KPI trend / forecast distinction. */
export function SparkLine({
  points,
  width = 320,
  height = 120,
  accent = "var(--accent-2)",
  forecastFromIndex,
  ariaLabel = "Trend chart",
}: Props) {
  if (points.length < 2) {
    return <p className="muted">Not enough points for a trend.</p>;
  }

  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const padX = 12;
  const padY = 16;
  const innerW = width - padX * 2;
  const innerH = height - padY * 2;

  const coords = points.map((p, i) => {
    const x = padX + (i / (points.length - 1)) * innerW;
    const y = padY + (1 - (p.value - min) / span) * innerH;
    return { x, y, ...p };
  });

  const path = coords.map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`).join(" ");
  const split = forecastFromIndex != null && forecastFromIndex > 0 ? forecastFromIndex : null;

  return (
    <svg
      className="chart-svg"
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      role="img"
      aria-label={ariaLabel}
    >
      <line
        x1={padX}
        y1={height - padY}
        x2={width - padX}
        y2={height - padY}
        stroke="var(--border)"
        strokeWidth="1"
      />
      {split != null ? (
        <>
          <path
            d={coords
              .slice(0, split + 1)
              .map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`)
              .join(" ")}
            fill="none"
            stroke={accent}
            strokeWidth="2.5"
          />
          <path
            d={coords
              .slice(split)
              .map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`)
              .join(" ")}
            fill="none"
            stroke={accent}
            strokeWidth="2.5"
            strokeDasharray="6 4"
            opacity={0.85}
          />
        </>
      ) : (
        <path d={path} fill="none" stroke={accent} strokeWidth="2.5" />
      )}
      {coords.map((c) => (
        <circle key={`${c.label}-${c.x}`} cx={c.x} cy={c.y} r={3.5} fill={accent} />
      ))}
      {coords.map((c) => (
        <text
          key={`lbl-${c.label}`}
          x={c.x}
          y={height - 2}
          textAnchor="middle"
          className="chart-label"
        >
          {c.label}
        </text>
      ))}
    </svg>
  );
}

"use client";

type Props = {
  score: number | null | undefined;
  label?: string | null;
};

/** Compact health score meter for L1 executive signal. */
export function HealthMeter({ score, label }: Props) {
  if (score == null) {
    return <p className="muted">Generate Decision Intelligence to score business health.</p>;
  }
  const clamped = Math.max(0, Math.min(100, score));
  const tone =
    clamped >= 70 ? "healthy" : clamped >= 40 ? "watch" : "critical";

  return (
    <div className={`health-meter health-${tone}`} aria-label={`Business health ${clamped}`}>
      <div className="health-meter-top">
        <strong>{clamped}</strong>
        <span className="muted">{label || "score"}</span>
      </div>
      <div className="health-meter-track">
        <div className="health-meter-fill" style={{ width: `${clamped}%` }} />
      </div>
    </div>
  );
}

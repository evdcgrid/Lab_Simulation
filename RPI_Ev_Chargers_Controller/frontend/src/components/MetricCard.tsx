import { useDisplayValue } from "../hooks/useDisplayValue";

interface MetricCardProps {
  label: string;
  value: string;
  unit?: string;
  tone?: "default" | "good" | "warn" | "danger";
}

const tones = {
  default: "text-zinc-50",
  good: "text-signal-green",
  warn: "text-signal-amber",
  danger: "text-signal-red"
};

export function MetricCard({ label, value, unit, tone = "default" }: MetricCardProps) {
  const displayValue = useDisplayValue(value, 500);

  return (
    <section className="metric-card rounded-lg border border-white/10 bg-graphite-850 p-4 shadow-panel">
      <div className="text-sm text-zinc-400">{label}</div>
      <div className={`mt-2 flex items-baseline gap-2 font-mono ${tones[tone]}`}>
        <span className="text-3xl font-semibold">{displayValue}</span>
        {unit ? <span className="text-base text-zinc-400">{unit}</span> : null}
      </div>
    </section>
  );
}

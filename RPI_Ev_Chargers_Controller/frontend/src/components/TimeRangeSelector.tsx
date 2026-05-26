export type TimeRange = "1m" | "5m" | "15m" | "1h";

const ranges: TimeRange[] = ["1m", "5m", "15m", "1h"];

export function TimeRangeSelector({
  value,
  onChange
}: {
  value: TimeRange;
  onChange: (value: TimeRange) => void;
}) {
  return (
    <div className="grid grid-cols-4 rounded-lg border border-white/10 bg-graphite-900 p-1">
      {ranges.map((range) => (
        <button
          key={range}
          className={`h-12 rounded-md px-4 text-sm font-semibold ${
            value === range ? "bg-zinc-100 text-graphite-950" : "text-zinc-300"
          }`}
          onClick={() => onChange(range)}
        >
          {range}
        </button>
      ))}
    </div>
  );
}

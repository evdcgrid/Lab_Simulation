import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { useMemo } from "react";
import type { HistoryPoint } from "../types/telemetry";

export type ChartPoint = HistoryPoint | (HistoryPoint & Record<string, unknown>);

export interface ChartSeries {
  key: string;
  name: string;
  color: string;
  unit?: string;
  scale?: (value: number) => number;
}

interface TelemetryChartProps {
  points: ChartPoint[];
  series: ChartSeries[];
  height?: number;
  compact?: boolean;
  maxPoints?: number;
  bucketMs?: number;
  dropOpenBucket?: boolean;
  showDots?: boolean;
}

function formatTime(value: string) {
  const date = new Date(value);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function downsamplePoints(points: ChartPoint[], maxPoints: number, bucketMs?: number, dropOpenBucket = false) {
  if (points.length <= maxPoints && !bucketMs) return points;
  if (points.length === 0) return points;

  const firstTimestamp = new Date(points[0].timestamp).getTime();
  const lastTimestamp = new Date(points[points.length - 1].timestamp).getTime();
  const spanMs = Number.isFinite(firstTimestamp) && Number.isFinite(lastTimestamp)
    ? Math.max(1, lastTimestamp - firstTimestamp)
    : points.length;
  const effectiveBucketMs = bucketMs ?? Math.max(1, Math.ceil(spanMs / Math.max(1, maxPoints - 1)));
  const buckets = new Map<number, ChartPoint>();

  for (const point of points) {
    const timestampMs = new Date(point.timestamp).getTime();
    if (!Number.isFinite(timestampMs)) continue;
    const bucket = Math.floor(timestampMs / effectiveBucketMs) * effectiveBucketMs;
    const previous = buckets.get(bucket) ?? ({ timestamp: new Date(bucket).toISOString() } as ChartPoint);
    buckets.set(bucket, { ...previous, ...point, timestamp: new Date(bucket).toISOString() } as ChartPoint);
  }

  const bucketEntries = [...buckets.values()].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  if (dropOpenBucket && bucketMs && bucketEntries.length > 1) {
    const latestBucket = bucketEntries[bucketEntries.length - 1];
    const latestBucketMs = new Date(latestBucket.timestamp).getTime();
    if (Number.isFinite(latestBucketMs) && Date.now() < latestBucketMs + effectiveBucketMs) {
      bucketEntries.pop();
    }
  }

  if (bucketEntries.length <= maxPoints) return bucketEntries;
  return downsamplePoints(bucketEntries, maxPoints, undefined, false);
}

export function TelemetryChart({
  points,
  series,
  height = 230,
  compact = false,
  maxPoints,
  bucketMs,
  dropOpenBucket = false,
  showDots = !compact
}: TelemetryChartProps) {
  const pointLimit = maxPoints ?? (compact ? 240 : 900);
  const sampledPoints = useMemo(
    () => downsamplePoints(points, pointLimit, bucketMs, dropOpenBucket),
    [points, pointLimit, bucketMs, dropOpenBucket]
  );
  const data = useMemo(
    () =>
      sampledPoints.map((point) => {
        const row: Record<string, number | string | null | undefined> = {
          timestamp: point.timestamp,
          time: formatTime(point.timestamp)
        };
        for (const item of series) {
          const value = (point as Record<string, unknown>)[item.key];
          row[item.key] = typeof value === "number" ? (item.scale ? item.scale(value) : value) : null;
        }
        return row;
      }),
    [sampledPoints, series]
  );
  const drawDots = showDots && data.length <= 250;

  return (
    <div className="h-full min-h-0 w-full">
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={compact ? { top: 8, right: 10, left: 0, bottom: 0 } : { top: 12, right: 18, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
          <XAxis dataKey="time" tick={compact ? false : { fill: "#a7b0bc", fontSize: 12 }} minTickGap={24} />
          <YAxis tick={{ fill: "#a7b0bc", fontSize: compact ? 10 : 12 }} width={compact ? 34 : 44} />
          <Tooltip
            contentStyle={{
              background: "#12161b",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 8,
              color: "#f4f4f5"
            }}
            labelStyle={{ color: "#f4f4f5" }}
          />
          {!compact ? <Legend wrapperStyle={{ color: "#d4d4d8", fontSize: 12 }} /> : null}
          {series.map((item) => (
            <Line
              key={String(item.key)}
              type="monotone"
              dataKey={String(item.key)}
              name={item.unit ? `${item.name} (${item.unit})` : item.name}
              stroke={item.color}
              strokeWidth={3}
              dot={drawDots ? { r: 2 } : false}
              activeDot={showDots && !compact ? { r: 5 } : false}
              isAnimationActive={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

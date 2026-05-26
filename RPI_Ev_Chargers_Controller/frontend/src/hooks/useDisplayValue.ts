import { useEffect, useRef, useState } from "react";

export function useDisplayValue<T>(value: T, intervalMs = 500) {
  const latestValue = useRef(value);
  const [displayValue, setDisplayValue] = useState(value);

  useEffect(() => {
    latestValue.current = value;
  }, [value]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setDisplayValue(latestValue.current);
    }, intervalMs);

    return () => window.clearInterval(timer);
  }, [intervalMs]);

  return displayValue;
}

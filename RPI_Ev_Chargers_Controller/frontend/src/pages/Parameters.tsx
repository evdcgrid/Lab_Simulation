import { ChevronLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { getParameters, updateParameters } from "../api/client";
import { ParameterForm } from "../components/ParameterForm";
import type { ChargerParameters as ChargerParametersModel, ChargerParametersUpdate } from "../types/parameters";
import type { ChargerStatus } from "../types/telemetry";

export function Parameters({
  chargers,
  selectedChargerId,
  onSelectCharger,
  onBack
}: {
  chargers: ChargerStatus[];
  selectedChargerId?: string;
  onSelectCharger: (chargerId: string) => void;
  onBack: () => void;
}) {
  const [parameters, setParameters] = useState<ChargerParametersModel | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedChargerId) return;
    setLoading(true);
    setError(null);
    setSuccess(null);
    getParameters(selectedChargerId)
      .then(setParameters)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selectedChargerId]);

  const apply = async (update: ChargerParametersUpdate) => {
    if (!selectedChargerId) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await updateParameters(selectedChargerId, update);
      setParameters(response.parameters);
      setSuccess("Changes applied");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not apply changes");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="parameters-screen grid gap-4 xl:grid-cols-[260px_1fr]">
      <aside className="parameters-sidebar rounded-lg border border-white/10 bg-graphite-850 p-3 shadow-panel">
        <button className="mb-3 flex h-12 w-full items-center justify-center gap-2 rounded-md border border-white/10 bg-graphite-800 text-zinc-100" onClick={onBack}>
          <ChevronLeft size={20} />
          Back
        </button>
        <div className="grid gap-2">
          {chargers.map((charger) => (
            <button
              key={charger.charger_id}
              className={`h-12 rounded-md px-3 text-left font-semibold ${
                charger.charger_id === selectedChargerId ? "bg-zinc-100 text-graphite-950" : "bg-graphite-900 text-zinc-200"
              }`}
              onClick={() => onSelectCharger(charger.charger_id)}
            >
              {charger.charger_id}
            </button>
          ))}
        </div>
      </aside>

      <main className="parameters-main min-w-0">
        {loading ? (
          <div className="rounded-lg border border-white/10 bg-graphite-850 p-6 text-zinc-300">Loading parameters</div>
        ) : parameters ? (
          <ParameterForm
            parameters={parameters}
            saving={saving}
            error={error}
            success={success}
            onApply={apply}
            onEdit={() => {
              setError(null);
              setSuccess(null);
            }}
          />
        ) : (
          <div className="rounded-lg border border-white/10 bg-graphite-850 p-6 text-zinc-300">No parameters available</div>
        )}
      </main>
    </div>
  );
}

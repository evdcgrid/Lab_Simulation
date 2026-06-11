import { AlertTriangle } from "lucide-react";

interface ConfirmModalProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmModal({
  open,
  title,
  message,
  confirmLabel = "Apply",
  onConfirm,
  onCancel
}: ConfirmModalProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-6">
      <div className="w-full max-w-md rounded-lg border border-white/10 bg-graphite-850 p-5 shadow-panel">
        <div className="flex items-start gap-3">
          <div className="grid h-12 w-12 place-items-center rounded-md bg-signal-amber/10 text-signal-amber">
            <AlertTriangle size={24} />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-zinc-50">{title}</h2>
            <p className="mt-2 text-base text-zinc-300">{message}</p>
          </div>
        </div>
        <div className="mt-6 grid grid-cols-2 gap-3">
          <button className="h-12 rounded-md border border-white/10 bg-graphite-800 text-zinc-100" onClick={onCancel}>
            Cancel
          </button>
          <button className="h-12 rounded-md bg-signal-amber font-semibold text-graphite-950" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

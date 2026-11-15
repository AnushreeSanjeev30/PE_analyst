import { useState } from "react";
import { downloadExport, extractErrorMessage } from "../lib/api";
import type { ExportFormat } from "../lib/api";

// "Download PDF" and "Download Word" for a report or a comparison. The file is built on the
// server from the saved run, so what downloads is exactly what was analysed.
export function DownloadButtons({
  path,
  params,
  label = "Download",
}: {
  /** API path of the export endpoint, e.g. "/deals/analyses/<id>/export". */
  path: string;
  params?: Record<string, string>;
  label?: string;
}) {
  const [busy, setBusy] = useState<ExportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function download(format: ExportFormat) {
    setError(null);
    setBusy(format);
    try {
      await downloadExport(path, format, params);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  const button =
    "rounded-md border border-[var(--border-hairline)] bg-[var(--surface-1)] px-3 py-1.5 text-sm font-medium text-[var(--text-primary)] hover:bg-[var(--page-plane)] disabled:opacity-50";
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-[var(--text-muted)]">{label}</span>
      <button type="button" className={button} disabled={busy !== null} onClick={() => download("pdf")}>
        {busy === "pdf" ? "Preparing..." : "PDF"}
      </button>
      <button type="button" className={button} disabled={busy !== null} onClick={() => download("docx")}>
        {busy === "docx" ? "Preparing..." : "Word"}
      </button>
      {error && <span className="text-xs text-[var(--status-critical)]">{error}</span>}
    </div>
  );
}

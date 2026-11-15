import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { extractErrorMessage, fetchDocumentFile } from "../lib/api";

// Opens the original PDF at a cited page, in a viewer over the current screen, so a reader can
// check a quote against its source without losing their place in the report.
//
// The file is fetched with the auth header and shown from an object URL; one URL is kept per
// document for the life of the page so reopening a citation is instant.
const objectUrls = new Map<string, string>();

async function documentUrl(documentId: string): Promise<string> {
  const cached = objectUrls.get(documentId);
  if (cached) return cached;
  const url = URL.createObjectURL(await fetchDocumentFile(documentId));
  objectUrls.set(documentId, url);
  return url;
}

function Viewer({
  url,
  page,
  title,
  onClose,
}: {
  url: string;
  page: number;
  title: string;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // "#page=N" is the standard PDF open parameter; the browser's built-in viewer honours it.
  const src = `${url}#page=${page}`;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={`${title}, page ${page}`}
      onClick={onClose}
    >
      <div
        className="flex h-full w-full max-w-5xl flex-col overflow-hidden rounded-lg bg-[var(--surface-1)] shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-4 border-b border-[var(--border-hairline)] px-4 py-3">
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-[var(--text-primary)]">{title}</div>
            <div className="text-xs text-[var(--text-muted)] tabular-nums">Page {page}</div>
          </div>
          <div className="flex shrink-0 items-center gap-4">
            <a href={src} target="_blank" rel="noreferrer" className="text-sm font-medium text-[var(--series-1)]">
              Open in new tab
            </a>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-[var(--border-hairline)] px-3 py-1 text-sm text-[var(--text-secondary)] hover:bg-[var(--page-plane)]"
            >
              Close
            </button>
          </div>
        </div>
        <iframe key={src} src={src} title={`${title}, page ${page}`} className="min-h-0 flex-1 border-0" />
      </div>
    </div>
  );
}

export function PdfPageLink({
  documentId,
  page,
  title,
  children,
  className = "",
}: {
  /** Without a document id (evidence typed in by hand) the content renders as plain text. */
  documentId: string | null | undefined;
  page: number;
  title: string;
  children: ReactNode;
  className?: string;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!documentId) return <span className={className}>{children}</span>;

  async function open() {
    setError(null);
    setLoading(true);
    try {
      setUrl(await documentUrl(documentId as string));
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={open}
        disabled={loading}
        title="Open the PDF at this page"
        className={`text-left text-[var(--series-1)] underline decoration-dotted underline-offset-2 hover:decoration-solid disabled:opacity-60 ${className}`}
      >
        {loading ? "Opening..." : children}
      </button>
      {error && <span className="ml-2 text-xs text-[var(--status-critical)]">{error}</span>}
      {url && <Viewer url={url} page={page} title={title} onClose={() => setUrl(null)} />}
    </>
  );
}

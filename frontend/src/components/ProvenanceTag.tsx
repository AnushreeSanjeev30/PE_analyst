import { PdfPageLink } from "./PdfPageLink";

// Every extracted claim in the document-intelligence pipeline carries a page
// number + excerpt + confidence. Surfacing that provenance (rather than hiding
// it) is called out explicitly in the product brief.
export function ProvenanceTag({
  page,
  confidence,
  excerpt,
  documentId,
  documentTitle = "Source document",
}: {
  page: number;
  confidence: number;
  excerpt?: string;
  /** When given, the page number opens the PDF at that page. */
  documentId?: string | null;
  documentTitle?: string;
}) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded border border-[var(--border-hairline)] bg-[var(--surface-1)] px-2 py-0.5 text-xs text-[var(--text-secondary)] tabular-nums"
      title={excerpt}
    >
      <PdfPageLink documentId={documentId} page={page} title={documentTitle}>
        p.{page}
      </PdfPageLink>{" "}
      &middot; {(confidence * 100).toFixed(0)}% confidence
    </span>
  );
}

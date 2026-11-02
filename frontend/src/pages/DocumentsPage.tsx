import { useCallback, useEffect, useRef, useState } from "react";
import type { DragEvent } from "react";
import { Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import { extractErrorMessage, listDocuments, uploadDocument } from "../lib/api";
import type { DocumentSummary } from "../lib/types";

export function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(() => {
    setError(null);
    listDocuments()
      .then(setDocuments)
      .catch((err) => setError(extractErrorMessage(err)));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleFiles(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf") {
      setUploadError("Only PDF files are accepted.");
      return;
    }
    setUploadError(null);
    setUploading(true);
    try {
      await uploadDocument(file);
      refresh();
    } catch (err) {
      setUploadError(extractErrorMessage(err));
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragOver(false);
    handleFiles(event.dataTransfer.files);
  }

  return (
    <Layout>
      <div className="max-w-5xl">
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Document Library</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Upload annual reports, CIMs, or other deal PDFs for extraction. Every extracted claim is
          traced back to a page and confidence score.
        </p>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`mt-6 cursor-pointer rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
            dragOver ? "border-[var(--series-1)] bg-[var(--seq-100)]" : "border-[var(--baseline)] bg-[var(--surface-1)]"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
          <p className="text-sm font-medium text-[var(--text-primary)]">
            {uploading ? "Uploading and extracting..." : "Drag & drop a PDF here, or click to browse"}
          </p>
          <p className="mt-1 text-xs text-[var(--text-muted)]">PDF only</p>
        </div>
        {uploadError && <p className="mt-2 text-sm text-[var(--status-critical)]">{uploadError}</p>}

        <div className="mt-8">
          {error && <p className="text-sm text-[var(--status-critical)]">{error}</p>}
          {documents === null && !error && (
            <p className="text-sm text-[var(--text-muted)]">Loading documents...</p>
          )}
          {documents && documents.length === 0 && (
            <p className="text-sm text-[var(--text-muted)]">No documents uploaded yet.</p>
          )}
          {documents && documents.length > 0 && (
            <div className="overflow-hidden rounded-lg border border-[var(--border-hairline)] bg-[var(--surface-1)]">
              <table className="min-w-full divide-y divide-[var(--gridline)]">
                <thead className="bg-[var(--page-plane)]">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">File</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Pages</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Risk factors</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Warnings</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--gridline)]">
                  {documents.map((doc) => (
                    <tr key={doc.document_id} className="hover:bg-[var(--page-plane)]">
                      <td className="px-4 py-3 text-sm">
                        <Link
                          to={`/documents/${doc.document_id}`}
                          className="font-medium text-[var(--series-1)] hover:underline"
                        >
                          {doc.file_name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-sm text-[var(--text-secondary)] tabular-nums">{doc.page_count}</td>
                      <td className="px-4 py-3 text-sm text-[var(--text-secondary)] tabular-nums">{doc.risk_factor_count}</td>
                      <td className="px-4 py-3 text-sm tabular-nums">
                        {doc.warning_count > 0 ? (
                          <span className="text-[var(--status-serious)]">{doc.warning_count}</span>
                        ) : (
                          <span className="text-[var(--text-muted)]">0</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

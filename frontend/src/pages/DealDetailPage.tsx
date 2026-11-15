import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Layout } from "../components/Layout";
import { SeverityBadge } from "../components/SeverityBadge";
import {
  addDealRoomMember,
  assignDocumentDealRoom,
  deleteDealRoom,
  extractErrorMessage,
  getDealRoom,
  listAnalyses,
  listDocuments,
  removeDealRoomMember,
  uploadDocument,
} from "../lib/api";
import type { DealAnalysisSummary, DealRoomDetail, DocumentSummary } from "../lib/types";

const STATUS_LABEL: Record<string, string> = {
  pending: "Queued",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
};

function Card({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-[var(--border-hairline)] bg-[var(--surface-1)] p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-[var(--text-primary)]">{title}</h2>
        {action}
      </div>
      <div className="mt-3">{children}</div>
    </section>
  );
}

export function DealDetailPage() {
  const { dealId } = useParams<{ dealId: string }>();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [deal, setDeal] = useState<DealRoomDetail | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [privateDocuments, setPrivateDocuments] = useState<DocumentSummary[]>([]);
  const [analyses, setAnalyses] = useState<DealAnalysisSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [uploading, setUploading] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);

  const refresh = useCallback(async () => {
    if (!dealId) return;
    try {
      const [room, roomDocuments, allDocuments, roomAnalyses] = await Promise.all([
        getDealRoom(dealId),
        listDocuments(dealId),
        listDocuments(),
        listAnalyses(dealId),
      ]);
      setDeal(room);
      setDocuments(roomDocuments);
      setPrivateDocuments(allDocuments.filter((doc) => doc.deal_room_id === null));
      setAnalyses(roomAnalyses);
      setError(null);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }, [dealId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load on mount / deal change
    refresh();
  }, [refresh]);

  async function run(action: () => Promise<unknown>, done?: string) {
    setError(null);
    setNotice(null);
    try {
      await action();
      if (done) setNotice(done);
      await refresh();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  async function handleAddMember(event: FormEvent) {
    event.preventDefault();
    if (!dealId || !email.trim()) return;
    const address = email.trim();
    await run(() => addDealRoomMember(dealId, address), `${address} can now see this deal.`);
    setEmail("");
  }

  async function handleUpload(files: FileList | null) {
    if (!dealId || !files?.length) return;
    setUploading(true);
    await run(async () => {
      // One at a time: each upload is extracted and indexed before the next starts.
      for (const file of Array.from(files)) {
        await uploadDocument(file, dealId);
      }
    });
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleDeleteDeal() {
    if (!deal) return;
    const message =
      `Delete the deal "${deal.name}"? Its documents and analyses are kept, but go back to being ` +
      "private to whoever created them. This cannot be undone.";
    if (!window.confirm(message)) return;
    try {
      await deleteDealRoom(deal.id);
      navigate("/deals");
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  function toggleSelected(id: string) {
    setSelected((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id].slice(-2),
    );
  }

  if (!deal) {
    return (
      <Layout>
        <p className={`text-sm ${error ? "text-[var(--status-critical)]" : "text-[var(--text-muted)]"}`}>
          {error ?? "Loading deal..."}
        </p>
      </Layout>
    );
  }

  const comparable = analyses.filter((analysis) => analysis.status === "completed");

  return (
    <Layout>
      <div className="max-w-5xl space-y-6 pb-16">
        <div>
          <Link to="/deals" className="text-sm text-[var(--series-1)] hover:underline">
            &larr; All deals
          </Link>
          <div className="mt-2 flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold text-[var(--text-primary)]">{deal.name}</h1>
              {deal.description && <p className="mt-1 text-sm text-[var(--text-secondary)]">{deal.description}</p>}
            </div>
            <Link
              to={`/analysis/new?deal=${deal.id}`}
              className="shrink-0 rounded-md bg-[var(--series-1)] px-4 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              New analysis
            </Link>
          </div>
        </div>

        {error && <p className="text-sm text-[var(--status-critical)]">{error}</p>}
        {notice && <p className="text-sm text-[var(--text-secondary)]">{notice}</p>}

        <Card title={`Documents (${documents.length})`}>
          <p className="text-xs text-[var(--text-muted)]">
            Add everything you have on the company: the CIM, audited accounts, a management presentation. An
            analysis can draw on several at once.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,.pdf"
              multiple
              className="hidden"
              onChange={(e) => handleUpload(e.target.files)}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="rounded-md border border-[var(--border-hairline)] px-3 py-1.5 text-sm font-medium text-[var(--text-primary)] hover:bg-[var(--page-plane)] disabled:opacity-50"
            >
              {uploading ? "Uploading and extracting..." : "Upload PDFs"}
            </button>
            {privateDocuments.length > 0 && (
              <select
                value=""
                onChange={(e) => {
                  const id = e.target.value;
                  if (id && dealId) run(() => assignDocumentDealRoom(id, dealId));
                }}
                className="rounded-md border border-[var(--border-hairline)] px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)]"
              >
                <option value="">Add one of your private documents...</option>
                {privateDocuments.map((doc) => (
                  <option key={doc.document_id} value={doc.document_id}>
                    {doc.display_name}
                  </option>
                ))}
              </select>
            )}
          </div>
          {documents.length === 0 ? (
            <p className="mt-4 text-sm text-[var(--text-muted)]">No documents in this deal yet.</p>
          ) : (
            <ul className="mt-4 divide-y divide-[var(--gridline)] rounded-md border border-[var(--border-hairline)]">
              {documents.map((doc) => (
                <li key={doc.document_id} className="flex items-center justify-between gap-4 px-4 py-3">
                  <div className="min-w-0">
                    <Link
                      to={`/documents/${doc.document_id}`}
                      className="text-sm font-medium text-[var(--series-1)] hover:underline"
                    >
                      {doc.display_name}
                    </Link>
                    <div className="text-xs text-[var(--text-muted)] tabular-nums">
                      {doc.page_count} pages &middot; {doc.risk_factor_count} risk factors
                      {doc.warning_count > 0 && <> &middot; {doc.warning_count} extraction warnings</>}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => run(() => assignDocumentDealRoom(doc.document_id, null))}
                    className="shrink-0 text-xs text-[var(--text-muted)] hover:text-[var(--status-critical)]"
                    title="Take this document out of the deal. Only its uploader can do this."
                  >
                    Remove from deal
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card
          title={`Analyses (${analyses.length})`}
          action={
            <button
              type="button"
              disabled={selected.length !== 2}
              onClick={() => navigate(`/analyses/compare?base=${selected[0]}&other=${selected[1]}`)}
              className="rounded-md border border-[var(--border-hairline)] px-3 py-1.5 text-sm font-medium text-[var(--text-primary)] hover:bg-[var(--page-plane)] disabled:opacity-40"
            >
              Compare selected
            </button>
          }
        >
          {analyses.length === 0 ? (
            <p className="text-sm text-[var(--text-muted)]">No analyses in this deal yet.</p>
          ) : (
            <>
              {comparable.length >= 2 && (
                <p className="text-xs text-[var(--text-muted)]">
                  Tick two completed runs to see what changed between them. The first one you tick is the baseline.
                </p>
              )}
              <ul className="mt-3 divide-y divide-[var(--gridline)] rounded-md border border-[var(--border-hairline)]">
                {analyses.map((analysis) => (
                  <li key={analysis.id} className="flex items-center gap-4 px-4 py-3">
                    <input
                      type="checkbox"
                      aria-label={`Select the ${analysis.company_name} run for comparison`}
                      disabled={analysis.status !== "completed"}
                      checked={selected.includes(analysis.id)}
                      onChange={() => toggleSelected(analysis.id)}
                    />
                    <div className="min-w-0 flex-1">
                      <Link
                        to={`/analyses/${analysis.id}`}
                        className="text-sm font-medium text-[var(--series-1)] hover:underline"
                      >
                        {analysis.company_name}
                      </Link>
                      <div className="text-xs text-[var(--text-muted)] tabular-nums">
                        {new Date(analysis.created_at).toLocaleString()} &middot;{" "}
                        {STATUS_LABEL[analysis.status] ?? analysis.status}
                      </div>
                    </div>
                    {analysis.recommendation && <SeverityBadge level={analysis.recommendation} />}
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>

        <Card title={`Team (${deal.members.length})`}>
          <ul className="divide-y divide-[var(--gridline)] rounded-md border border-[var(--border-hairline)]">
            {deal.members.map((member) => (
              <li key={member.user_id} className="flex items-center justify-between gap-4 px-4 py-2.5">
                <span className="text-sm text-[var(--text-primary)]">{member.email}</span>
                <span className="flex items-center gap-4">
                  <span className="text-xs capitalize text-[var(--text-muted)]">{member.role}</span>
                  {deal.can_manage && member.role === "member" && (
                    <button
                      type="button"
                      onClick={() => run(() => removeDealRoomMember(deal.id, member.user_id))}
                      className="text-xs text-[var(--text-muted)] hover:text-[var(--status-critical)]"
                    >
                      Remove
                    </button>
                  )}
                </span>
              </li>
            ))}
          </ul>
          {deal.can_manage ? (
            <form onSubmit={handleAddMember} className="mt-4 flex flex-wrap gap-2">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="colleague@firm.com"
                className="w-full max-w-xs rounded-md border border-[var(--border-hairline)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)]"
              />
              <button
                type="submit"
                className="rounded-md bg-[var(--series-1)] px-4 py-2 text-sm font-medium text-white hover:opacity-90"
              >
                Add to deal
              </button>
              <p className="w-full text-xs text-[var(--text-muted)]">
                They need an account first. Once added they can read every document and analysis in this deal.
              </p>
            </form>
          ) : (
            <p className="mt-3 text-xs text-[var(--text-muted)]">Only the deal owner can change the team.</p>
          )}
        </Card>

        {deal.can_manage && (
          <button type="button" onClick={handleDeleteDeal} className="text-sm text-[var(--status-critical)] hover:underline">
            Delete this deal
          </button>
        )}
      </div>
    </Layout>
  );
}

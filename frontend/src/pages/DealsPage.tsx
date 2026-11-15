import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { createDealRoom, extractErrorMessage, listDealRooms } from "../lib/api";
import type { DealRoomSummary } from "../lib/types";

export function DealsPage() {
  const navigate = useNavigate();
  const [deals, setDeals] = useState<DealRoomSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listDealRooms()
      .then((rooms) => {
        if (!cancelled) setDeals(rooms);
      })
      .catch((err) => {
        if (!cancelled) setError(extractErrorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const room = await createDealRoom(name.trim(), description.trim());
      navigate(`/deals/${room.id}`);
    } catch (err) {
      setError(extractErrorMessage(err));
      setCreating(false);
    }
  }

  return (
    <Layout>
      <div className="max-w-5xl">
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Deals</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          A deal holds its documents, its analyses and its team. Everyone on the team sees everything filed in the
          deal; anything outside a deal stays private to you.
        </p>

        <form
          onSubmit={handleCreate}
          className="mt-6 rounded-lg border border-[var(--border-hairline)] bg-[var(--surface-1)] p-5"
        >
          <h2 className="text-base font-semibold text-[var(--text-primary)]">Start a deal</h2>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-[1fr_2fr_auto] sm:items-end">
            <label className="block">
              <span className="block text-xs font-medium text-[var(--text-secondary)]">Deal name</span>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Project Meridian"
                className="mt-1 w-full rounded-md border border-[var(--border-hairline)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)]"
              />
            </label>
            <label className="block">
              <span className="block text-xs font-medium text-[var(--text-secondary)]">Description (optional)</span>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Vertical software buyout, sell-side process run by ..."
                className="mt-1 w-full rounded-md border border-[var(--border-hairline)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)]"
              />
            </label>
            <button
              type="submit"
              disabled={creating}
              className="rounded-md bg-[var(--series-1)] px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
            >
              {creating ? "Creating..." : "Create deal"}
            </button>
          </div>
        </form>

        <div className="mt-8">
          {error && <p className="text-sm text-[var(--status-critical)]">{error}</p>}
          {deals === null && !error && <p className="text-sm text-[var(--text-muted)]">Loading deals...</p>}
          {deals && deals.length === 0 && (
            <p className="text-sm text-[var(--text-muted)]">No deals yet. Create one above to start sharing work.</p>
          )}
          {deals && deals.length > 0 && (
            <div className="overflow-hidden rounded-lg border border-[var(--border-hairline)] bg-[var(--surface-1)]">
              <table className="min-w-full divide-y divide-[var(--gridline)]">
                <thead className="bg-[var(--page-plane)]">
                  <tr>
                    {["Deal", "Documents", "Analyses", "Team", "Your role"].map((heading) => (
                      <th
                        key={heading}
                        className="px-4 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase"
                      >
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--gridline)]">
                  {deals.map((deal) => (
                    <tr key={deal.id} className="hover:bg-[var(--page-plane)]">
                      <td className="px-4 py-3 text-sm">
                        <Link to={`/deals/${deal.id}`} className="font-medium text-[var(--series-1)] hover:underline">
                          {deal.name}
                        </Link>
                        {deal.description && (
                          <div className="text-xs text-[var(--text-muted)]">{deal.description}</div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-[var(--text-secondary)] tabular-nums">{deal.document_count}</td>
                      <td className="px-4 py-3 text-sm text-[var(--text-secondary)] tabular-nums">{deal.analysis_count}</td>
                      <td className="px-4 py-3 text-sm text-[var(--text-secondary)] tabular-nums">{deal.member_count}</td>
                      <td className="px-4 py-3 text-sm text-[var(--text-secondary)]">
                        {deal.can_manage ? "Owner" : "Member"}
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

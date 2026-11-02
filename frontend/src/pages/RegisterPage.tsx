import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { extractErrorMessage } from "../lib/api";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setSubmitting(true);
    try {
      await register(email, password);
      navigate("/documents", { replace: true });
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--page-plane)" }}>
      <div className="w-full max-w-sm rounded-lg border border-[var(--border-hairline)] bg-[var(--surface-1)] p-8 shadow-sm">
        <h1 className="text-xl font-semibold text-[var(--text-primary)]">Create an account</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">Join the PE-Analyst workbench.</p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)]">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-md border border-[var(--border-hairline)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)]"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)]">Password</label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-md border border-[var(--border-hairline)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)]"
            />
            <p className="mt-1 text-xs text-[var(--text-muted)]">At least 8 characters.</p>
          </div>
          {error && <p className="text-sm text-[var(--status-critical)]">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-[var(--series-1)] px-3 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? "Creating account..." : "Register"}
          </button>
        </form>

        <p className="mt-4 text-sm text-[var(--text-secondary)]">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-[var(--series-1)]">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

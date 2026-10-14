import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { apiErrorMessage } from "../api/client";

const DEMO_ACCOUNTS = [
  { username: "admin", role: "Admin", department: "HQ" },
  { username: "officer", role: "Officer", department: "Traffic" },
  { username: "reviewer", role: "Reviewer", department: "Traffic" },
  { username: "approver", role: "Approver", department: "HQ" },
  { username: "auditor", role: "Auditor", department: "HQ" },
];

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("Passw0rd!23");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? "/";

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(apiErrorMessage(err, "Invalid credentials"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-900 px-4">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-xl">
        <h1 className="text-2xl font-bold text-brand-900">IPMPRS</h1>
        <p className="mt-1 text-sm text-slate-500">
          Intelligent Proposal Management &amp; Precedent Retrieval System
        </p>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="block text-sm font-medium text-slate-700" htmlFor="username">
              Username
            </label>
            <input
              id="username"
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 focus:border-brand-600 focus:outline-none"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 focus:border-brand-600 focus:outline-none"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {error && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-brand-600 px-4 py-2 font-medium text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className="mt-6 border-t border-slate-200 pt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Demo accounts (password Passw0rd!23)
          </p>
          <ul className="mt-2 space-y-1 text-sm text-slate-600">
            {DEMO_ACCOUNTS.map((account) => (
              <li key={account.username}>
                <button
                  type="button"
                  className="font-mono text-brand-700 hover:underline"
                  onClick={() => setUsername(account.username)}
                >
                  {account.username}
                </button>{" "}
                — {account.role}, {account.department}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

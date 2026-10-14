import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  createProposal,
  listProposals,
  type ProposalStatus,
} from "../api/proposals";
import { apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { StatusBadge } from "../components/StatusBadge";

const STATUSES: ProposalStatus[] = [
  "created",
  "submitted",
  "reviewed",
  "modified",
  "returned",
  "approved",
  "rejected",
  "implemented",
  "closed",
];

function splitList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseBudget(value: string): { item: string; amount: number }[] {
  return value
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean)
    .map((entry) => {
      const [item, amount] = entry.split(":").map((part) => part.trim());
      return { item: item ?? "", amount: Number(amount) || 0 };
    })
    .filter((line) => line.item);
}

export function ProposalsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<ProposalStatus | "">("");
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    subject: "",
    purpose: "",
    resources: "",
    policies: "",
    budget: "",
    classification: "INTERNAL",
  });

  const { data: proposals, isLoading } = useQuery({
    queryKey: ["proposals", filter],
    queryFn: () => listProposals(filter || undefined),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      createProposal({
        subject: form.subject,
        purpose: form.purpose,
        resources: splitList(form.resources),
        policies: splitList(form.policies),
        budget: parseBudget(form.budget),
        classification: form.classification,
      }),
    onSuccess: () => {
      setForm({ subject: "", purpose: "", resources: "", policies: "", budget: "", classification: "INTERNAL" });
      setShowForm(false);
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["proposals"] });
    },
    onError: (err) => setError(apiErrorMessage(err, "Could not create proposal")),
  });

  const canCreate = user?.role === "officer" || user?.role === "reviewer" || user?.role === "admin";

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    createMutation.mutate();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-800">Proposals</h1>
        {canCreate && (
          <button
            type="button"
            onClick={() => setShowForm((value) => !value)}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            {showForm ? "Cancel" : "New proposal"}
          </button>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <input
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            placeholder="Subject"
            value={form.subject}
            onChange={(e) => setForm({ ...form, subject: e.target.value })}
            required
            minLength={3}
          />
          <textarea
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            placeholder="Purpose"
            rows={3}
            value={form.purpose}
            onChange={(e) => setForm({ ...form, purpose: e.target.value })}
            required
            minLength={3}
          />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="Resources (comma separated)"
              value={form.resources}
              onChange={(e) => setForm({ ...form, resources: e.target.value })}
            />
            <input
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="Policies (comma separated)"
              value={form.policies}
              onChange={(e) => setForm({ ...form, policies: e.target.value })}
            />
            <input
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="Budget e.g. cameras:50000, docks:8000"
              value={form.budget}
              onChange={(e) => setForm({ ...form, budget: e.target.value })}
            />
            <select
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={form.classification}
              onChange={(e) => setForm({ ...form, classification: e.target.value })}
            >
              <option value="INTERNAL">INTERNAL</option>
              <option value="RESTRICTED">RESTRICTED</option>
              <option value="CONFIDENTIAL">CONFIDENTIAL</option>
            </select>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {createMutation.isPending ? "Creating..." : "Create"}
          </button>
        </form>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setFilter("")}
          className={`rounded-full px-3 py-1 text-xs font-medium ${
            filter === "" ? "bg-brand-600 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"
          }`}
        >
          all
        </button>
        {STATUSES.map((status) => (
          <button
            key={status}
            type="button"
            onClick={() => setFilter(status)}
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              filter === status ? "bg-brand-600 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Subject</th>
              <th className="px-4 py-3">Department</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Version</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isLoading && (
              <tr>
                <td className="px-4 py-4 text-slate-400" colSpan={4}>
                  Loading...
                </td>
              </tr>
            )}
            {proposals?.length === 0 && (
              <tr>
                <td className="px-4 py-4 text-slate-400" colSpan={4}>
                  No proposals visible for your account.
                </td>
              </tr>
            )}
            {proposals?.map((proposal) => (
              <tr key={proposal.id} className="hover:bg-slate-50">
                <td className="px-4 py-3">
                  <Link to={`/proposals/${proposal.id}`} className="font-medium text-brand-700 hover:underline">
                    {proposal.subject}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-600">{proposal.department}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={proposal.status} />
                </td>
                <td className="px-4 py-3 text-slate-500">v{proposal.version}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

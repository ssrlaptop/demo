import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  closeProposal,
  decideProposal,
  getProposal,
  getProposalTimeline,
  getProposalVersions,
  implementProposal,
  modifyProposal,
  returnProposal,
  reviewProposal,
  submitProposal,
} from "../api/proposals";
import { apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { StatusBadge } from "../components/StatusBadge";

const BTN =
  "rounded-md px-3 py-1.5 text-sm font-medium disabled:opacity-50";
const BTN_PRIMARY = `${BTN} bg-brand-600 text-white hover:bg-brand-700`;
const BTN_DANGER = `${BTN} bg-red-600 text-white hover:bg-red-700`;
const BTN_NEUTRAL = `${BTN} border border-slate-300 text-slate-700 hover:bg-slate-50`;

function includes(role: string | undefined, roles: string[]): boolean {
  return !!role && roles.includes(role);
}

export function ProposalDetailPage() {
  const { id = "" } = useParams();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [modifying, setModifying] = useState(false);
  const [draft, setDraft] = useState({ subject: "", purpose: "" });

  const proposalQuery = useQuery({ queryKey: ["proposal", id], queryFn: () => getProposal(id) });
  const versionsQuery = useQuery({ queryKey: ["proposal-versions", id], queryFn: () => getProposalVersions(id) });
  const timelineQuery = useQuery({ queryKey: ["proposal-timeline", id], queryFn: () => getProposalTimeline(id) });

  function refresh() {
    queryClient.invalidateQueries({ queryKey: ["proposal", id] });
    queryClient.invalidateQueries({ queryKey: ["proposal-versions", id] });
    queryClient.invalidateQueries({ queryKey: ["proposal-timeline", id] });
    queryClient.invalidateQueries({ queryKey: ["proposals"] });
    setNote("");
    setError(null);
  }

  const proposal = proposalQuery.data;
  const status = proposal?.status;
  const role = user?.role;

  const onError = (err: unknown) => setError(apiErrorMessage(err, "Action failed"));

  const submitM = useMutation({ mutationFn: () => submitProposal(id), onSuccess: refresh, onError });
  const reviewM = useMutation({ mutationFn: () => reviewProposal(id, note), onSuccess: refresh, onError });
  const returnM = useMutation({ mutationFn: () => returnProposal(id, note), onSuccess: refresh, onError });
  const approveM = useMutation({ mutationFn: () => decideProposal(id, "approved", note), onSuccess: refresh, onError });
  const rejectM = useMutation({ mutationFn: () => decideProposal(id, "rejected", note), onSuccess: refresh, onError });
  const implementM = useMutation({ mutationFn: () => implementProposal(id), onSuccess: refresh, onError });
  const closeM = useMutation({ mutationFn: () => closeProposal(id), onSuccess: refresh, onError });

  const modifyM = useMutation({
    mutationFn: () => modifyProposal(id, { ...draft, reason: note }),
    onSuccess: () => {
      setModifying(false);
      refresh();
    },
    onError,
  });

  if (proposalQuery.isLoading) return <p className="text-slate-500">Loading proposal...</p>;
  if (proposalQuery.isError || !proposal) return <p className="text-red-600">Proposal not found or not authorized.</p>;

  const canSubmit = (status === "created" || status === "modified") && includes(role, ["officer", "reviewer", "admin"]);
  const canReview = status === "submitted" && includes(role, ["reviewer", "approver", "admin"]);
  const canReturn =
    (status === "submitted" && includes(role, ["reviewer", "approver", "admin"])) ||
    (status === "reviewed" && includes(role, ["approver", "admin"]));
  const canDecide = status === "reviewed" && includes(role, ["approver", "admin"]);
  const canModify = status === "returned" && includes(role, ["officer", "reviewer", "admin"]);
  const canImplement = status === "approved" && includes(role, ["officer", "reviewer", "admin"]);
  const canClose = status === "implemented" && includes(role, ["approver", "admin"]);

  return (
    <div className="space-y-6">
      <Link to="/proposals" className="text-sm text-brand-700 hover:underline">
        &larr; Back to proposals
      </Link>

      <header className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-xl font-semibold text-slate-800">{proposal.subject}</h1>
          <div className="flex items-center gap-2">
            <StatusBadge status={proposal.status} />
            <span className="text-sm text-slate-500">v{proposal.version}</span>
          </div>
        </div>
        <dl className="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-slate-400">Department</dt>
            <dd className="text-slate-700">{proposal.department}</dd>
          </div>
          <div>
            <dt className="text-slate-400">Classification</dt>
            <dd className="text-slate-700">{proposal.classification}</dd>
          </div>
          <div>
            <dt className="text-slate-400">Owner</dt>
            <dd className="text-slate-700">{proposal.created_by}</dd>
          </div>
        </dl>
        <p className="mt-4 whitespace-pre-wrap text-slate-700">{proposal.purpose}</p>
      </header>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Actions</h2>
        {error && <p className="mt-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        <textarea
          className="mt-3 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          rows={2}
          placeholder="Comment / reason (used by review, return, and decision)"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        <div className="mt-3 flex flex-wrap gap-2">
          {canSubmit && (
            <button className={BTN_PRIMARY} onClick={() => submitM.mutate()} disabled={submitM.isPending}>
              Submit
            </button>
          )}
          {canReview && (
            <button className={BTN_PRIMARY} onClick={() => reviewM.mutate()} disabled={reviewM.isPending}>
              Mark reviewed
            </button>
          )}
          {canDecide && (
            <>
              <button className={BTN_PRIMARY} onClick={() => approveM.mutate()} disabled={approveM.isPending}>
                Approve
              </button>
              <button className={BTN_DANGER} onClick={() => rejectM.mutate()} disabled={rejectM.isPending}>
                Reject
              </button>
            </>
          )}
          {canReturn && (
            <button className={BTN_NEUTRAL} onClick={() => returnM.mutate()} disabled={returnM.isPending}>
              Return for changes
            </button>
          )}
          {canModify && !modifying && (
            <button
              className={BTN_NEUTRAL}
              onClick={() => {
                setModifying(true);
                setDraft({ subject: proposal.subject, purpose: proposal.purpose });
              }}
            >
              Modify
            </button>
          )}
          {canImplement && (
            <button className={BTN_PRIMARY} onClick={() => implementM.mutate()} disabled={implementM.isPending}>
              Mark implemented
            </button>
          )}
          {canClose && (
            <button className={BTN_NEUTRAL} onClick={() => closeM.mutate()} disabled={closeM.isPending}>
              Close
            </button>
          )}
          {!canSubmit &&
            !canReview &&
            !canDecide &&
            !canReturn &&
            !canModify &&
            !canImplement &&
            !canClose && <p className="text-sm text-slate-400">No actions available for your role at this stage.</p>}
        </div>

        {modifying && (
          <div className="mt-4 space-y-3 rounded-lg bg-slate-50 p-4">
            <input
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={draft.subject}
              onChange={(e) => setDraft({ ...draft, subject: e.target.value })}
            />
            <textarea
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              rows={3}
              value={draft.purpose}
              onChange={(e) => setDraft({ ...draft, purpose: e.target.value })}
            />
            <div className="flex gap-2">
              <button className={BTN_PRIMARY} onClick={() => modifyM.mutate()} disabled={modifyM.isPending}>
                Save changes
              </button>
              <button className={BTN_NEUTRAL} onClick={() => setModifying(false)}>
                Cancel
              </button>
            </div>
          </div>
        )}
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Details</h2>
          <div className="mt-3 space-y-3 text-sm">
            <div>
              <p className="text-slate-400">Resources</p>
              <p className="text-slate-700">{proposal.resources.join(", ") || "—"}</p>
            </div>
            <div>
              <p className="text-slate-400">Policies</p>
              <p className="text-slate-700">{proposal.policies.join(", ") || "—"}</p>
            </div>
            <div>
              <p className="text-slate-400">Budget</p>
              {proposal.budget.length ? (
                <ul className="text-slate-700">
                  {proposal.budget.map((line) => (
                    <li key={line.item}>
                      {line.item}: ${line.amount.toLocaleString()}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-slate-700">—</p>
              )}
            </div>
            {proposal.decisions.length > 0 && (
              <div>
                <p className="text-slate-400">Decisions (version-pinned)</p>
                <ul className="space-y-1 text-slate-700">
                  {proposal.decisions.map((decision) => (
                    <li key={decision.snapshot_hash} className="rounded bg-slate-50 px-2 py-1">
                      <span className="font-medium uppercase">{decision.outcome}</span> at v{decision.version} by{" "}
                      {decision.decided_by}
                      <span className="block font-mono text-xs text-slate-400">
                        pin {decision.snapshot_hash.slice(0, 16)}…
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Version history</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {versionsQuery.data?.map((version) => (
              <li key={version.version} className="rounded-md border border-slate-100 px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-700">
                    v{version.version} · {version.action}
                  </span>
                  <span className="text-xs text-slate-400">{version.actor_username}</span>
                </div>
                {version.changes.length > 0 && (
                  <p className="text-xs text-amber-700">changed: {version.changes.join(", ")}</p>
                )}
                <p className="font-mono text-xs text-slate-400">{version.content_hash.slice(0, 24)}…</p>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Timeline</h2>
        <ol className="mt-3 space-y-2 text-sm">
          {timelineQuery.data?.map((entry, index) => (
            <li key={index} className="flex gap-3">
              <span className="w-40 shrink-0 text-xs text-slate-400">
                {new Date(entry.at).toLocaleString()}
              </span>
              <span
                className={`inline-block rounded px-1.5 text-xs font-medium ${
                  entry.kind === "audit" ? "bg-slate-100 text-slate-600" : "bg-blue-50 text-blue-700"
                }`}
              >
                {entry.source}
              </span>
              <span className="text-slate-700">
                {entry.actor_username}
                {entry.version ? ` · v${entry.version}` : ""} — {entry.message}
              </span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

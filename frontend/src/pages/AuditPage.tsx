import { useQuery } from "@tanstack/react-query";
import { listAuditEvents, verifyAudit } from "../api/audit";
import { apiErrorMessage } from "../api/client";

export function AuditPage() {
  const eventsQuery = useQuery({ queryKey: ["audit-events"], queryFn: () => listAuditEvents(200) });
  const verifyQuery = useQuery({ queryKey: ["audit-verify"], queryFn: verifyAudit });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-800">Audit trail</h1>
        {verifyQuery.data && (
          <span
            className={`rounded-full px-3 py-1 text-xs font-semibold ${
              verifyQuery.data.verified
                ? "bg-emerald-100 text-emerald-700"
                : "bg-red-100 text-red-700"
            }`}
          >
            {verifyQuery.data.verified
              ? `Chain verified · ${verifyQuery.data.checked} events`
              : `CHAIN BROKEN at seq ${verifyQuery.data.first_bad_seq}`}
          </span>
        )}
      </div>

      <p className="text-sm text-slate-500">
        Append-only, hash-chained log. Each event pins the proposal version and snapshot hash it acted on.
        Audit events never contain proposal/document content.
      </p>

      {eventsQuery.isError && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {apiErrorMessage(eventsQuery.error, "Could not load audit events")}
        </p>
      )}

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-3">Seq</th>
              <th className="px-3 py-3">Action</th>
              <th className="px-3 py-3">Version</th>
              <th className="px-3 py-3">Actor</th>
              <th className="px-3 py-3">Outcome</th>
              <th className="px-3 py-3">Event hash</th>
              <th className="px-3 py-3">Prev hash</th>
              <th className="px-3 py-3">When</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {eventsQuery.data?.map((event) => (
              <tr key={event.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 font-mono text-xs text-slate-500">{event.seq}</td>
                <td className="px-3 py-2 text-slate-700">{event.action}</td>
                <td className="px-3 py-2 text-slate-500">{event.proposal_version ? `v${event.proposal_version}` : "—"}</td>
                <td className="px-3 py-2 text-slate-600">{event.actor_username}</td>
                <td className="px-3 py-2 text-slate-600">{event.outcome ?? "—"}</td>
                <td className="px-3 py-2 font-mono text-xs text-slate-400">{event.event_hash.slice(0, 12)}…</td>
                <td className="px-3 py-2 font-mono text-xs text-slate-400">
                  {event.prev_hash ? `${event.prev_hash.slice(0, 12)}…` : "genesis"}
                </td>
                <td className="px-3 py-2 text-xs text-slate-400">{new Date(event.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {eventsQuery.data?.length === 0 && (
              <tr>
                <td className="px-3 py-4 text-slate-400" colSpan={8}>
                  No audit events yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

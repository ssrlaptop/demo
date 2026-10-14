import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { healthRequest } from "../api/auth";
import { listProposals, type ProposalStatus } from "../api/proposals";
import { useAuth } from "../auth/AuthContext";

const LIFECYCLE_STAGES: ProposalStatus[] = [
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

function StatCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-brand-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const { data: health, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: healthRequest,
    refetchInterval: 15000,
  });
  const { data: proposals } = useQuery({ queryKey: ["proposals", ""], queryFn: () => listProposals() });

  if (!user) return null;

  const dbOk = health?.mongodb === "connected";
  const pipeline = LIFECYCLE_STAGES.map((stage) => ({
    stage,
    count: proposals?.filter((p) => p.status === stage).length ?? 0,
  }));
  const total = proposals?.length ?? 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Signed in as" value={user.full_name} hint={`@${user.username}`} />
        <StatCard label="Role" value={user.role} hint="Enforced server-side (RBAC)" />
        <StatCard label="Visible proposals" value={String(total)} hint="Department + oversight scope" />
        <StatCard
          label="MongoDB"
          value={isLoading ? "checking..." : dbOk ? "connected" : "unavailable"}
          hint="Atlas cluster"
        />
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-semibold text-slate-800">Proposal pipeline</h2>
          <span className="text-xs text-slate-400">Live counts from your authorized proposals</span>
        </div>
        <div className="mt-4 h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={pipeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="stage" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#1d4ed8" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-800">Phase 2 status</h2>
        <ul className="mt-3 space-y-2 text-sm text-slate-600">
          <li>Proposal lifecycle state machine with approver-only finalization — complete</li>
          <li>Version-pinned decisions + immutable version history — complete</li>
          <li>Append-only, hash-chained audit trail + verifier — complete</li>
          <li>Field-change history, review comments, timeline endpoint — complete</li>
          <li>Upcoming: document ingestion, extraction &amp; versioning (Phase 3)</li>
        </ul>
      </section>
    </div>
  );
}

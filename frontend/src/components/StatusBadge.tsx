import type { ProposalStatus } from "../api/proposals";

const STYLES: Record<ProposalStatus, string> = {
  created: "bg-slate-100 text-slate-700",
  submitted: "bg-blue-100 text-blue-700",
  reviewed: "bg-indigo-100 text-indigo-700",
  modified: "bg-amber-100 text-amber-700",
  approved: "bg-emerald-100 text-emerald-700",
  rejected: "bg-red-100 text-red-700",
  returned: "bg-orange-100 text-orange-700",
  implemented: "bg-teal-100 text-teal-700",
  closed: "bg-slate-200 text-slate-600",
};

export function StatusBadge({ status }: { status: ProposalStatus }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase ${STYLES[status]}`}>
      {status}
    </span>
  );
}

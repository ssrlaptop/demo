import { api } from "./client";

export type ProposalStatus =
  | "created"
  | "submitted"
  | "reviewed"
  | "modified"
  | "approved"
  | "rejected"
  | "returned"
  | "implemented"
  | "closed";

export interface BudgetItem {
  item: string;
  amount: number;
}

export interface Decision {
  outcome: string;
  version: number;
  reason: string;
  decided_by: string;
  decided_at: string;
  snapshot_hash: string;
}

export interface Proposal {
  id: string;
  subject: string;
  purpose: string;
  department: string;
  status: ProposalStatus;
  version: number;
  resources: string[];
  budget: BudgetItem[];
  policies: string[];
  identifiers: Record<string, string>;
  responsible_officers: string[];
  start_date: string | null;
  end_date: string | null;
  decisions: Decision[];
  classification: string;
  owner_id: string;
  owner_department: string;
  allowed_user_ids: string[];
  allowed_departments: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ProposalVersion {
  version: number;
  content_hash: string;
  changes: string[];
  action: string;
  actor_username: string;
  reason: string;
  created_at: string;
}

export interface TimelineEntry {
  at: string;
  kind: "audit" | "comment";
  source: string;
  actor_username: string;
  version: number | null;
  message: string;
}

export interface ProposalCreateInput {
  subject: string;
  purpose: string;
  department?: string;
  resources?: string[];
  budget?: BudgetItem[];
  policies?: string[];
  classification?: string;
}

export async function listProposals(status?: ProposalStatus): Promise<Proposal[]> {
  const params = status ? { status_filter: status } : undefined;
  const { data } = await api.get<Proposal[]>("/proposals", { params });
  return data;
}

export async function getProposal(id: string): Promise<Proposal> {
  const { data } = await api.get<Proposal>(`/proposals/${id}`);
  return data;
}

export async function getProposalVersions(id: string): Promise<ProposalVersion[]> {
  const { data } = await api.get<ProposalVersion[]>(`/proposals/${id}/versions`);
  return data;
}

export async function getProposalTimeline(id: string): Promise<TimelineEntry[]> {
  const { data } = await api.get<TimelineEntry[]>(`/proposals/${id}/timeline`);
  return data;
}

export async function createProposal(input: ProposalCreateInput): Promise<Proposal> {
  const { data } = await api.post<Proposal>("/proposals", input);
  return data;
}

async function action(id: string, path: string, body?: unknown): Promise<Proposal> {
  const { data } = await api.post<Proposal>(`/proposals/${id}/${path}`, body ?? {});
  return data;
}

export const submitProposal = (id: string) => action(id, "submit");
export const reviewProposal = (id: string, comment: string) => action(id, "review", { comment });
export const returnProposal = (id: string, reason: string) => action(id, "return", { reason });
export const decideProposal = (id: string, outcome: "approved" | "rejected", reason: string) =>
  action(id, "decide", { outcome, reason });
export const implementProposal = (id: string) => action(id, "implement");
export const closeProposal = (id: string) => action(id, "close");

export interface ProposalModifyInput {
  subject?: string;
  purpose?: string;
  resources?: string[];
  policies?: string[];
  budget?: BudgetItem[];
  reason?: string;
}

export async function modifyProposal(id: string, patch: ProposalModifyInput): Promise<Proposal> {
  const { data } = await api.post<Proposal>(`/proposals/${id}/modify`, patch);
  return data;
}

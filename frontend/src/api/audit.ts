import { api } from "./client";

export interface AuditEvent {
  id: string;
  seq: number;
  actor_id: string;
  actor_username: string;
  action: string;
  entity_type: string;
  entity_id: string;
  proposal_version: number | null;
  content_hash: string | null;
  outcome: string | null;
  summary: string;
  prev_hash: string | null;
  event_hash: string;
  created_at: string;
}

export interface AuditVerdict {
  verified: boolean;
  checked: number;
  first_bad_seq: number | null;
}

export async function listAuditEvents(limit = 100): Promise<AuditEvent[]> {
  const { data } = await api.get<AuditEvent[]>("/audit/events", { params: { limit } });
  return data;
}

export async function verifyAudit(): Promise<AuditVerdict> {
  const { data } = await api.get<AuditVerdict>("/audit/verify");
  return data;
}

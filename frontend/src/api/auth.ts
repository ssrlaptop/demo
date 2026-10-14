import { api } from "./client";

export type Role = "officer" | "reviewer" | "approver" | "auditor" | "admin";

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: Role;
  department: string;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface HealthStatus {
  status: string;
  mongodb: "connected" | "unavailable";
}

export async function loginRequest(username: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/login", { username, password });
  return data;
}

export async function meRequest(): Promise<User> {
  const { data } = await api.get<User>("/auth/me");
  return data;
}

export async function healthRequest(): Promise<HealthStatus> {
  const { data } = await api.get<HealthStatus>("/health");
  return data;
}

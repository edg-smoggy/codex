import type { AuthBundle } from "../types/api";
import { API_BASE, parseResponse } from "./http";

export async function register(params: {
  inviteCode: string;
  username: string;
  password: string;
}): Promise<AuthBundle> {
  const resp = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      invite_code: params.inviteCode,
      username: params.username,
      password: params.password,
    }),
  });
  return parseResponse<AuthBundle>(resp);
}

export async function login(params: { username: string; password: string }): Promise<AuthBundle> {
  const resp = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return parseResponse<AuthBundle>(resp);
}

export async function refresh(refreshToken: string): Promise<AuthBundle> {
  const resp = await fetch(`${API_BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  return parseResponse<AuthBundle>(resp);
}

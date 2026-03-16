import type { DataSourceMode } from "../types/view";

export const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

function resolveDataSourceMode(raw: unknown): DataSourceMode {
  if (raw === "real" || raw === "mock" || raw === "hybrid") {
    return raw;
  }
  return "hybrid";
}

export const DATA_SOURCE_MODE = resolveDataSourceMode(import.meta.env.VITE_DATA_SOURCE_MODE);

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(`${status}: ${message}`);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function parseResponse<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = "Request failed";
    try {
      const data = await resp.json();
      detail = data.detail || detail;
    } catch {
      // ignore JSON parse errors
    }
    throw new ApiError(resp.status, detail);
  }
  return (await resp.json()) as T;
}

export function isUnauthorizedError(err: unknown): boolean {
  if (!(err instanceof Error)) return false;
  return err.message.includes("401") || (err as { status?: number }).status === 401;
}

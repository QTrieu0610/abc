export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  statusText: string;
  path: string;

  constructor(path: string, status: number, statusText: string, message?: string) {
    super(message || `API request failed: ${status} ${statusText}`);
    this.name = "ApiError";
    this.status = status;
    this.statusText = statusText;
    this.path = path;
  }
}

export async function apiRequest<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers || {}),
      },
      ...options,
    });
  } catch (error) {
    throw new ApiError(
      path,
      0,
      "Network Error",
      "Backend API is not reachable. Please start FastAPI server."
    );
  }

  if (!response.ok) {
    let message = `API request failed: ${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body?.detail) {
        message = Array.isArray(body.detail)
          ? body.detail.map((item: unknown) => String(item)).join(", ")
          : String(body.detail);
      }
    } catch {
      // Keep the status-based message when the body is not JSON.
    }
    throw new ApiError(path, response.status, response.statusText, message);
  }

  return response.json();
}

export function buildQuery(params: Record<string, string | number | boolean | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) query.set(key, String(value));
  });
  const value = query.toString();
  return value ? `?${value}` : "";
}

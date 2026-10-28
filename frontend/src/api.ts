import { useCallback, useEffect, useState } from "react";

const KEY = "mrk_token";
export const getToken = (): string => {
  try { return localStorage.getItem(KEY) || ""; } catch { return ""; }
};
export const setToken = (t: string) => {
  try { t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY); } catch { /* bỏ qua */ }
};

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const res = await fetch("/api" + path, {
    method: opts.method || "GET",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken()}` },
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
  });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && getToken()) { setToken(""); location.reload(); }
    const d = data?.detail;
    const msg = typeof d === "string" ? d : Array.isArray(d) ? d.map((x: any) => x.msg).join("; ") : `Lỗi ${res.status}`;
    throw new ApiError(res.status, msg);
  }
  return data as T;
}

export function useLoad<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const reload = useCallback(async () => {
    if (!path) return;
    setLoading(true);
    try { setData(await api<T>(path)); setError(""); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, [path]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { reload(); }, [reload, ...deps]);
  return { data, error, loading, reload };
}

export const utc = (s?: string | null) => (s ? new Date(s).toLocaleString("vi-VN") : "—");

export async function upload(path: string, files: File[], fields: Record<string, string> = {}, fieldName = "files"): Promise<any> {
  const fd = new FormData();
  Object.entries(fields).forEach(([k, v]) => fd.append(k, v));
  files.forEach((f) => fd.append(fieldName, f));
  const res = await fetch("/api" + path, { method: "POST", headers: { Authorization: `Bearer ${getToken()}` }, body: fd });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data?.detail;
    throw new ApiError(res.status, typeof d === "string" ? d : Array.isArray(d) ? d.map((x: any) => x.msg).join("; ") : `Lỗi ${res.status}`);
  }
  return data;
}

export async function download(path: string, filename: string): Promise<void> {
  const res = await fetch("/api" + path, { headers: { Authorization: `Bearer ${getToken()}` } });
  if (!res.ok) throw new ApiError(res.status, `Lỗi ${res.status}`);
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

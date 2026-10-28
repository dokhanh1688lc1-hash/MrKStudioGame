import { ReactNode, useState } from "react";

export function Async({ loading, error, children }: { loading: boolean; error: string; children: ReactNode }) {
  if (error) return <div className="msg err">Lỗi: {error}</div>;
  if (loading) return <div className="msg muted">Đang tải…</div>;
  return <>{children}</>;
}

export function Empty({ text }: { text: string }) {
  return <div className="msg muted">{text}</div>;
}

export const Badge = ({ v }: { v: string }) => <span className={`badge ${v}`}>{v}</span>;

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return <div><label>{label}</label>{children}</div>;
}

export function Pager({ total, offset, limit, onChange }: { total: number; offset: number; limit: number; onChange: (o: number) => void }) {
  if (total <= limit) return null;
  return (
    <div className="pager">
      <button className="btn ghost" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>‹ Trước</button>
      <span className="muted">{offset + 1}–{Math.min(total, offset + limit)} / {total}</span>
      <button className="btn ghost" disabled={offset + limit >= total} onClick={() => onChange(offset + limit)}>Sau ›</button>
    </div>
  );
}

/** Hook chạy hành động có xác nhận tùy chọn + hiển thị thông báo thành công/lỗi. */
export function useAction() {
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  async function run(fn: () => Promise<unknown>, okText: string, confirmText?: string) {
    if (confirmText && !window.confirm(confirmText)) return false;
    setBusy(true);
    try { await fn(); setMsg({ ok: true, text: okText }); return true; }
    catch (e: any) { setMsg({ ok: false, text: e.message }); return false; }
    finally { setBusy(false); }
  }
  const banner = msg && <div className={`msg ${msg.ok ? "okk" : "err"}`}>{msg.text}</div>;
  return { run, busy, banner };
}

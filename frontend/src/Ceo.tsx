import { useState } from "react";
import { api, useLoad, utc } from "./api";
import { Async, Badge, Empty, useAction } from "./ui";

const LABEL: Record<string, string> = { accepted: "Đã chấp nhận", rework: "Yêu cầu sửa lại", forward: "Đã chuyển phòng khác", dismissed: "Bỏ qua" };

function Item({ it, owner, depts, onDone, go }: { it: any; owner: boolean; depts: any[]; onDone: () => void; go: (p: string) => void }) {
  const [note, setNote] = useState(""); const [target, setTarget] = useState("");
  const [full, setFull] = useState<string | null>(null);
  const { run, busy, banner } = useAction();
  const decide = (decision: string, ok: string, confirm?: string) =>
    run(() => api(`/ceo/tasks/${it.task_id}/decide`, { method: "POST", body: { decision, note, target_department: target } }), ok, confirm).then((r) => r && onDone());
  return (
    <div className="card">
      <div className="row tight" style={{ alignItems: "center" }}>
        <b>#{it.task_id} · {it.title}</b><Badge v={it.status} />
        <span className="muted">{it.department} · dự án {it.project}{it.finished_at ? ` · ${utc(it.finished_at)}` : ""}{it.source ? ` · do ${it.source}` : ""}</span>
      </div>
      {it.source === "internal" && <div className="msg">Kết quả do chế độ nội bộ dựng sẵn, không phải đầu ra của AI.</div>}
      <pre className="out" style={{ maxHeight: full ? 420 : 140 }}>{full ?? (it.excerpt || "(không có nội dung)")}{!full && it.truncated ? "\n…" : ""}</pre>
      {it.truncated && !full && <p><a href="#" onClick={async (e) => { e.preventDefault(); const t = await api<any>(`/tasks/${it.task_id}`); setFull(t.result || t.error || ""); }}>Xem đầy đủ</a></p>}
      {banner}
      {it.decision ? (
        <p><Badge v={LABEL[it.decision]} /> {it.note && <span>“{it.note}”</span>} <span className="muted">— {it.decided_by}, {it.decided_at ? utc(it.decided_at) : ""}</span>
          {it.followup_task_id && <> · việc tiếp theo <a href="#" onClick={(e) => { e.preventDefault(); go("tasks"); }}>#{it.followup_task_id}</a> (đã giao, vào Task Center bấm Chạy)</>}</p>
      ) : owner ? (
        <>
          <textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Ghi chú / phản hồi của CEO (bắt buộc khi yêu cầu sửa lại; làm nội dung việc khi chuyển phòng khác)" />
          <p className="row tight" style={{ alignItems: "center" }}>
            <button className="btn" disabled={busy} onClick={() => decide("accepted", "Đã chấp nhận. Ghi chú của bạn (nếu có) được đề xuất thành bài học trong Sổ bài học để bạn duyệt.")}>✔ Chấp nhận</button>
            <button className="btn ghost" disabled={busy || !note.trim()} title={!note.trim() ? "Hãy ghi rõ cần sửa gì" : ""}
              onClick={() => decide("rework", "Đã giao phòng sửa lại. Phản hồi của bạn được đề xuất thành bài học trong Sổ bài học để bạn duyệt.", "Giao lại nhiệm vụ này cho phòng ban kèm phản hồi của bạn?")}>🔧 Yêu cầu sửa lại</button>
            <select value={target} onChange={(e) => setTarget(e.target.value)} style={{ width: "auto" }}>
              <option value="">Chuyển sang phòng…</option>{depts.filter((d) => d.key !== it.department_key && d.key !== "ceo").map((d) => <option key={d.key} value={d.key}>{d.name}</option>)}</select>
            <button className="btn ghost" disabled={busy || !target} onClick={() => decide("forward", "Đã chuyển sang phòng ban khác.")}>➡ Chuyển</button>
            <button className="btn ghost" disabled={busy} onClick={() => decide("dismissed", "Đã bỏ qua.")}>Bỏ qua</button>
          </p>
        </>
      ) : <p className="muted">Chỉ chủ studio (CEO) ra quyết định.</p>}
    </div>
  );
}

export function CeoInbox({ role, go }: { role: string; go: (p: string) => void }) {
  const [view, setView] = useState<"pending" | "decided">("pending");
  const [tick, setTick] = useState(0);
  const inbox = useLoad<{ pending: number; items: any[] }>(`/ceo/inbox?view=${view}&limit=30`, [tick, view]);
  const depts = useLoad<any[]>("/departments");
  const { run, busy, banner } = useAction();
  const [made, setMade] = useState<number | null>(null);
  const owner = role === "owner"; const manager = owner || role === "manager";
  return (
    <>
      <h2>Hộp thư CEO</h2>
      <div className="card ofc-bar">
        <span>Kết quả từ các phòng ban gửi về để CEO quyết định: <b>{inbox.data?.pending ?? "…"}</b> mục đang chờ.</span>
        {manager && <button className="btn" disabled={busy || !inbox.data?.pending} onClick={() => run(async () => { const r = await api<any>("/ceo/digest", { method: "POST" }); setMade(r.task_id); },
          "Đã tạo nhiệm vụ tổng hợp cho CEO AI. Vào Task Center bấm Chạy để nhận bản đề xuất quyết định.", "Tạo nhiệm vụ để CEO AI tổng hợp các kết quả chờ quyết định và đề xuất hướng xử lý?")}>
          Nhờ CEO AI tổng hợp & đề xuất</button>}
      </div>
      {banner}
      {made && <div className="msg okk">Nhiệm vụ #{made} đã tạo cho CEO. <a href="#" onClick={(e) => { e.preventDefault(); go("tasks"); }}>Mở Task Center</a> → bấm Chạy; kết quả là đề xuất cho từng mục (bạn vẫn là người quyết định).</div>}
      <p className="row tight">
        <button className={`btn ${view === "pending" ? "" : "ghost"}`} onClick={() => setView("pending")}>Chờ quyết định</button>
        <button className={`btn ${view === "decided" ? "" : "ghost"}`} onClick={() => setView("decided")}>Đã quyết định</button>
      </p>
      <Async loading={inbox.loading} error={inbox.error}>
        {inbox.data?.items.length ? inbox.data.items.map((it) => (
          <Item key={it.task_id} it={it} owner={owner} depts={depts.data ?? []} go={go} onDone={() => setTick((x) => x + 1)} />
        )) : <Empty text={view === "pending" ? "Không có kết quả nào chờ quyết định. Khi một phòng ban hoàn thành (hoặc thất bại) nhiệm vụ, nó sẽ hiện ở đây." : "Chưa có quyết định nào."} />}
      </Async>
    </>
  );
}

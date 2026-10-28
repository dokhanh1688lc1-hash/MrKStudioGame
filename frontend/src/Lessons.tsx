import { useState } from "react";
import { api, useLoad } from "./api";
import { Async, Empty, Field, useAction } from "./ui";

const STATUS: Record<string, string> = { suggested: "Chờ duyệt", active: "Đang dùng", archived: "Lưu trữ" };

export function Lessons({ role }: { role: string }) {
  const depts = useLoad<any[]>("/departments");
  const projects = useLoad<{ items: any[] }>("/projects?limit=100");
  const [dept, setDept] = useState(""); const [status, setStatus] = useState("suggested");
  const [tick, setTick] = useState(0);
  const list = useLoad<{ items: any[]; counts: Record<string, number> }>(`/lessons?status=${status}&department=${dept}`, [tick, status, dept]);
  const [f, setF] = useState({ department_key: "", project_id: "", text: "" });
  const [edit, setEdit] = useState<{ id: number; text: string } | null>(null);
  const { run, busy, banner } = useAction();
  const manager = role === "owner" || role === "manager";
  const refresh = () => setTick((x) => x + 1);
  const dname = (k: string) => depts.data?.find((d) => d.key === k)?.name ?? k;
  const patch = (id: number, body: any, ok: string) => run(() => api(`/lessons/${id}`, { method: "PATCH", body }), ok).then(refresh);

  return (
    <>
      <h2>Sổ bài học theo phòng ban</h2>
      {banner}
      <p className="muted">Bài học <b>đang dùng</b> được chèn gọn (tối đa 8 bài, ~1500 ký tự) vào đầu prompt của mọi nhiệm vụ sau của phòng đó, nên phòng ban làm đúng ý bạn hơn mà không tốn nhiều token. Khi bạn Chấp nhận hoặc Yêu cầu sửa lại kèm ghi chú trong Hộp thư CEO, ghi chú được đề xuất thành bài học <b>chờ duyệt</b> (chưa ảnh hưởng prompt cho đến khi bạn duyệt).</p>
      {manager && (
        <form className="card" onSubmit={async (e) => {
          e.preventDefault();
          if (await run(() => api("/lessons", { method: "POST", body: { department_key: f.department_key, text: f.text, project_id: f.project_id ? Number(f.project_id) : null } }), "Đã thêm bài học (đang dùng).")) { setF({ ...f, text: "" }); setStatus("active"); refresh(); }
        }}>
          <b>Thêm bài học</b>
          <div className="row">
            <Field label="Phòng ban *"><select value={f.department_key} onChange={(e) => setF({ ...f, department_key: e.target.value })} required>
              <option value="">— chọn —</option>{depts.data?.map((d) => <option key={d.key} value={d.key}>{d.name}</option>)}</select></Field>
            <Field label="Phạm vi"><select value={f.project_id} onChange={(e) => setF({ ...f, project_id: e.target.value })}>
              <option value="">Mọi dự án</option>{projects.data?.items.map((p) => <option key={p.id} value={p.id}>Chỉ dự án: {p.name}</option>)}</select></Field>
          </div>
          <Field label="Nội dung (ngắn gọn, 1–2 câu, ≤ 500 ký tự; khóa/token sẽ bị che)"><textarea value={f.text} maxLength={1000} onChange={(e) => setF({ ...f, text: e.target.value })} required minLength={5} placeholder="VD: Báo cáo lỗi phải có bước tái hiện, kết quả mong đợi và kết quả thực tế." /></Field>
          <p><button className="btn" disabled={busy}>Thêm</button></p>
        </form>
      )}
      <div className="card">
        <div className="row tight">
          {Object.keys(STATUS).map((k) => <button key={k} className={`btn ${status === k ? "" : "ghost"}`} onClick={() => setStatus(k)}>{STATUS[k]} ({list.data?.counts[k] ?? 0})</button>)}
          <label style={{ margin: 0 }}>Phòng ban <select value={dept} onChange={(e) => setDept(e.target.value)}>
            <option value="">Tất cả</option>{depts.data?.map((d) => <option key={d.key} value={d.key}>{d.name}</option>)}</select></label>
        </div>
        <Async loading={list.loading} error={list.error}>
          {list.data?.items.length ? (
            <div className="tablewrap"><table>
              <thead><tr><th>Phòng ban</th><th>Bài học</th><th>Phạm vi</th><th>Nguồn</th><th>Đã dùng</th><th></th></tr></thead>
              <tbody>{list.data.items.map((l) => { const cur = edit?.id === l.id ? edit : null; return (
                <tr key={l.id}><td>{dname(l.department_key)}</td>
                  <td>{cur ? (
                    <form onSubmit={(e) => { e.preventDefault(); patch(l.id, { text: cur.text }, "Đã lưu.").then(() => setEdit(null)); }}>
                      <textarea value={cur.text} maxLength={1000} onChange={(e) => setEdit({ id: l.id, text: e.target.value })} />
                      <span className="row tight"><button className="btn" disabled={busy}>Lưu</button><button type="button" className="btn ghost" onClick={() => setEdit(null)}>Đóng</button></span>
                    </form>) : l.text}</td>
                  <td>{l.project_id ? `Dự án: ${l.project_name}` : "Mọi dự án"}</td>
                  <td>{l.source === "ceo" ? "Từ CEO" : "Thêm tay"}{l.task_id ? ` (việc #${l.task_id})` : ""}</td>
                  <td>{l.uses} lần</td>
                  <td className="row tight">{manager && <>
                    {l.status === "suggested" && <button className="btn" disabled={busy} onClick={() => patch(l.id, { status: "active" }, "Đã duyệt — bài học bắt đầu được dùng.")}>Duyệt</button>}
                    {l.status === "suggested" && l.project_id && <button className="btn ghost" disabled={busy} title="Áp dụng cho mọi dự án" onClick={() => patch(l.id, { status: "active", project_id: null }, "Đã duyệt cho mọi dự án.")}>Duyệt cho mọi dự án</button>}
                    {l.status === "archived" && <button className="btn" disabled={busy} onClick={() => patch(l.id, { status: "active" }, "Đã dùng lại.")}>Dùng lại</button>}
                    {l.status === "active" && <button className="btn ghost" disabled={busy} onClick={() => patch(l.id, { status: "archived" }, "Đã lưu trữ.")}>Lưu trữ</button>}
                    {!cur && <button className="btn ghost" onClick={() => setEdit({ id: l.id, text: l.text })}>Sửa</button>}
                    <button className="btn danger" disabled={busy} onClick={() => run(() => api(`/lessons/${l.id}`, { method: "DELETE" }), "Đã xóa.", "Xóa bài học này?").then(refresh)}>Xóa</button></>}</td></tr>); })}</tbody></table></div>
          ) : <Empty text={status === "suggested" ? "Không có bài học nào chờ duyệt." : "Chưa có bài học nào."} />}
        </Async>
      </div>
    </>
  );
}

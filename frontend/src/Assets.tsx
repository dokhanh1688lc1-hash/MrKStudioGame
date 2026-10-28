import { useState } from "react";
import { api, download, upload, useLoad } from "./api";
import { Async, Badge, Empty, Field, useAction } from "./ui";

const KINDS: Record<string, string> = { image: "Hình ảnh", audio: "Âm thanh", font: "Phông chữ", model: "Mô hình 3D", data: "Dữ liệu", other: "Khác" };
const SOURCES: Record<string, string> = { own: "Tự tạo", purchased: "Mua", open_license: "Giấy phép mở (CC…)", ai_generated: "Do AI tạo", unknown: "Chưa rõ" };
const STATUS: Record<string, string> = { draft: "Nháp", approved: "Đã duyệt", rejected: "Từ chối" };
const blank = { name: "", kind: "", source: "own", license: "", license_url: "", author: "", notes: "" };

export function Assets({ role, go }: { role: string; go: (p: string) => void }) {
  const projects = useLoad<{ items: any[] }>("/projects?limit=100");
  const [pid, setPid] = useState("");
  const [kind, setKind] = useState(""); const [status, setStatus] = useState("");
  const [tick, setTick] = useState(0);
  const list = useLoad<{ items: any[]; summary: any }>(pid ? `/projects/${pid}/assets?kind=${kind}&status=${status}` : null, [tick, pid, kind, status]);
  const [f, setF] = useState<any>(blank); const [file, setFile] = useState<File | null>(null);
  const [editId, setEditId] = useState<number | null>(null);
  const { run, busy, banner } = useAction();
  const manager = role === "owner" || role === "manager"; const owner = role === "owner";
  const refresh = () => setTick((x) => x + 1);
  const reset = () => { setF(blank); setFile(null); setEditId(null); };

  return (
    <>
      <h2>Thư viện tài sản</h2>
      <div className="card">
        <Field label="Dự án">
          <select value={pid} onChange={(e) => { setPid(e.target.value); reset(); }}>
            <option value="">— chọn dự án —</option>{projects.data?.items.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select>
        </Field>
        <p className="muted">Mỗi tài sản (hình, nhạc, phông, mô hình…) cần ghi rõ <b>nguồn gốc và giấy phép</b> trước khi được duyệt, để tránh vi phạm bản quyền khi phát hành. Tài sản chỉ được duyệt khi không còn vấn đề nào.</p>
      </div>
      {banner}
      {pid && (
        <>
          {manager && (
            <form className="card" onSubmit={async (e) => {
              e.preventDefault();
              const ok = await run(async () => {
                if (editId) {
                  const { kind: k, ...rest } = f;
                  await api(`/assets/${editId}`, { method: "PATCH", body: { ...rest, ...(k ? { kind: k } : {}) } });
                } else {
                  await upload(`/projects/${pid}/assets`, file ? [file] : [], f, "file");
                }
              }, editId ? "Đã cập nhật." : "Đã thêm tài sản.");
              if (ok) { reset(); refresh(); }
            }}>
              <b>{editId ? `Sửa tài sản #${editId}` : "Thêm tài sản"}</b>
              <div className="row">
                <Field label="Tên (để trống = lấy theo tên tệp)"><input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
                <Field label="Loại (để trống = tự nhận theo đuôi tệp)"><select value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>
                  <option value="">Tự động</option>{Object.entries(KINDS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>
                <Field label="Nguồn gốc *"><select value={f.source} onChange={(e) => setF({ ...f, source: e.target.value })}>
                  {Object.entries(SOURCES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>
              </div>
              <div className="row">
                <Field label="Giấy phép (ví dụ CC0, CC-BY 4.0, giấy phép thương mại)"><input value={f.license} onChange={(e) => setF({ ...f, license: e.target.value })} /></Field>
                <Field label="Link giấy phép / trang gốc"><input value={f.license_url} onChange={(e) => setF({ ...f, license_url: e.target.value })} /></Field>
                <Field label="Tác giả / nhà cung cấp"><input value={f.author} onChange={(e) => setF({ ...f, author: e.target.value })} /></Field>
              </div>
              <Field label="Ghi chú (tài sản do AI tạo: ghi công cụ và prompt)"><textarea value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field>
              {!editId && <p><input type="file" style={{ width: "auto" }} onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
                <span className="muted"> Ảnh, âm thanh, phông, mô hình 3D, dữ liệu (tối đa 50 MB). Có thể chỉ ghi thông tin, chưa tải tệp.</span></p>}
              <p className="row tight">
                <button className="btn" disabled={busy || (!editId && !f.name && !file)}>{editId ? "Lưu" : "Thêm"}</button>
                {editId && <button type="button" className="btn ghost" onClick={reset}>Hủy sửa</button>}
              </p>
            </form>
          )}
          <Async loading={list.loading} error={list.error}>
            {list.data && (
              <div className="card">
                <div className="row tight" style={{ alignItems: "center" }}>
                  <span><b>{list.data.summary.total}</b> tài sản · <b>{list.data.summary.approved}</b> đã duyệt · <b style={{ color: list.data.summary.with_problems ? "var(--warn)" : undefined }}>{list.data.summary.with_problems}</b> cần xử lý · {list.data.summary.ai_generated} do AI tạo</span>
                  <select value={kind} onChange={(e) => setKind(e.target.value)} style={{ width: "auto" }}><option value="">Mọi loại</option>{Object.entries(KINDS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
                  <select value={status} onChange={(e) => setStatus(e.target.value)} style={{ width: "auto" }}><option value="">Mọi trạng thái</option>{Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
                  {manager && list.data.summary.total > 0 && <button className="btn ghost" disabled={busy} onClick={() => run(async () => { const r = await api<any>(`/projects/${pid}/assets/review-task`, { method: "POST" }); void r; },
                    "Đã giao phòng Bản quyền & Pháp lý rà soát. Vào Task Center bấm Chạy.", "Tạo nhiệm vụ rà soát bản quyền toàn bộ tài sản của dự án?").then((ok) => ok && go("tasks"))}>Nhờ phòng Bản quyền rà soát</button>}
                </div>
                {list.data.items.length ? (
                  <div className="tablewrap"><table><thead><tr><th>Tên</th><th>Loại</th><th>Nguồn</th><th>Giấy phép / tác giả</th><th>Trạng thái</th><th></th></tr></thead>
                    <tbody>{list.data.items.map((a) => (
                      <tr key={a.id}>
                        <td><b>{a.name}</b><div className="muted">{a.has_file ? `${a.file_name} · ${Math.max(1, Math.round(a.file_size / 1024))} KB` : "(chưa có tệp)"}</div></td>
                        <td>{KINDS[a.kind]}</td><td>{SOURCES[a.source]}</td>
                        <td>{a.license || a.license_url || "—"}<div className="muted">{a.author}</div>
                          {a.problems.map((p: string) => <div key={p}><span className="badge bad">{p}</span></div>)}</td>
                        <td><Badge v={STATUS[a.status]} /></td>
                        <td style={{ whiteSpace: "nowrap" }}>
                          {a.has_file && <button className="btn ghost" onClick={() => run(() => download(`/assets/${a.id}/file`, a.file_name), "Đã tải xuống.")}>Tải</button>}{" "}
                          {manager && <button className="btn ghost" onClick={() => { setEditId(a.id); setF({ name: a.name, kind: "", source: a.source, license: a.license, license_url: a.license_url, author: a.author, notes: a.notes }); window.scrollTo({ top: 0, behavior: "smooth" }); }}>Sửa</button>}{" "}
                          {owner && a.status !== "approved" && <button className="btn" disabled={busy || a.problems.length > 0} title={a.problems.join("; ")} onClick={() => run(() => api(`/assets/${a.id}/decision`, { method: "POST", body: { status: "approved" } }), "Đã duyệt.").then(refresh)}>Duyệt</button>}{" "}
                          {owner && a.status !== "rejected" && <button className="btn ghost" disabled={busy} onClick={() => run(() => api(`/assets/${a.id}/decision`, { method: "POST", body: { status: "rejected" } }), "Đã từ chối.").then(refresh)}>Từ chối</button>}{" "}
                          {owner && <button className="btn danger" disabled={busy} onClick={() => run(() => api(`/assets/${a.id}`, { method: "DELETE" }), "Đã xóa.", `Xóa tài sản “${a.name}” và tệp của nó?`).then(refresh)}>Xóa</button>}
                        </td>
                      </tr>))}</tbody></table></div>
                ) : <Empty text="Chưa có tài sản nào khớp." />}
              </div>
            )}
          </Async>
        </>
      )}
    </>
  );
}

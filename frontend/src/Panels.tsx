import { useState } from "react";
import { api, useLoad, utc } from "./api";
import { Async, Badge, Empty, Field, useAction } from "./ui";

export type Perm = { manager: boolean; owner: boolean };
export const perm = (role: string): Perm => ({ manager: role === "owner" || role === "manager", owner: role === "owner" });

export const DOC_KINDS: Record<string, string> = {
  gdd: "GDD", market_report: "Báo cáo thị trường", design: "Thiết kế", art_bible: "Art Bible", audio_bible: "Audio Bible", tech: "Kỹ thuật",
  qa_report: "Báo cáo QA", monetization: "Kiếm tiền", marketing: "Marketing", store_listing: "Thông tin cửa hàng", legal: "Pháp lý / bản quyền",
  release_notes: "Ghi chú phát hành", other: "Khác",
};

// ---------------------------------------------------------------- Tài liệu
export function DocsPanel({ pid, kinds, p }: { pid: number; kinds: string[]; p: Perm }) {
  const [tick, setTick] = useState(0);
  const [kind, setKind] = useState(kinds[0]); const [title, setTitle] = useState(""); const [content, setContent] = useState("");
  const [open, setOpen] = useState<number | null>(null);
  const q = kinds.length === 1 ? `?kind=${kinds[0]}` : "";
  const list = useLoad<{ items: any[] }>(`/projects/${pid}/documents${q}`, [tick]);
  const detail = useLoad<any>(open ? `/documents/${open}` : null, [open, tick]);
  const { run, busy, banner } = useAction();
  const items = list.data?.items.filter((d) => kinds.includes(d.kind)) ?? [];
  const refresh = () => setTick((x) => x + 1);
  return (
    <div className="card">
      <b>Tài liệu dự án (có phiên bản)</b>{banner}
      <Async loading={list.loading} error={list.error}>
        {items.length ? <div className="tablewrap"><table><thead><tr><th>Tên</th><th>Loại</th><th>Phiên bản</th><th>Trạng thái</th><th></th></tr></thead><tbody>
          {items.map((d) => (
            <tr key={d.id}><td>{d.title}</td><td>{DOC_KINDS[d.kind]}</td><td>v{d.version} ({d.versions} bản)</td><td><Badge v={d.status === "approved" ? "approved" : "draft"} /></td>
              <td className="row tight">
                <button className="btn ghost" onClick={() => setOpen(open === d.id ? null : d.id)}>{open === d.id ? "Ẩn" : "Xem"}</button>
                {p.manager && <button className="btn ghost" onClick={() => { setKind(d.kind); setTitle(d.title); setContent(""); window.scrollTo({ top: 0 }); }} title="Điền sẵn tên để lưu phiên bản mới ở form bên dưới">Phiên bản mới</button>}
                {p.owner && d.status !== "approved" && <button className="btn" disabled={busy} onClick={() => run(() => api(`/documents/${d.id}/status`, { method: "POST", body: { status: "approved" } }), "Đã duyệt tài liệu.").then(refresh)}>Duyệt</button>}
                {p.owner && <button className="btn danger" disabled={busy} onClick={() => run(() => api(`/documents/${d.id}`, { method: "DELETE" }), "Đã xóa.", `Xóa phiên bản v${d.version} của “${d.title}”?`).then(refresh)}>Xóa</button>}
              </td></tr>))}</tbody></table></div> : <Empty text="Chưa có tài liệu. Chạy nhiệm vụ rồi bấm “Lưu thành tài liệu”, hoặc thêm tay bên dưới." />}
      </Async>
      {open && detail.data && <div className="card"><b>{detail.data.title} v{detail.data.version}</b> <span className="muted">— {detail.data.created_by}, {utc(detail.data.created_at)}</span>
        <p className="muted">Các phiên bản: {detail.data.history.map((h: any) => `v${h.version}${h.status === "approved" ? "✔" : ""}`).join(", ")}</p><pre className="out">{detail.data.content || "(trống)"}</pre></div>}
      {p.manager && (
        <form onSubmit={async (e) => { e.preventDefault(); if (await run(() => api(`/projects/${pid}/documents`, { method: "POST", body: { kind, title, content } }), "Đã lưu phiên bản mới.")) { setTitle(""); setContent(""); refresh(); } }}>
          <div className="row">
            <Field label="Loại"><select value={kind} onChange={(e) => setKind(e.target.value)}>{kinds.map((k) => <option key={k} value={k}>{DOC_KINDS[k]}</option>)}</select></Field>
            <Field label="Tên tài liệu *"><input value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={200} /></Field>
          </div>
          <Field label="Nội dung (Markdown/văn bản)"><textarea value={content} onChange={(e) => setContent(e.target.value)} style={{ minHeight: 120 }} /></Field>
          <p><button className="btn" disabled={busy}>Lưu thành phiên bản mới</button></p>
        </form>)}
    </div>
  );
}

// ---------------------------------------------------------------- Kiểm thử
const TST: Record<string, string> = { not_run: "Chưa chạy", passed: "Passed", failed: "Failed", blocked: "Blocked" };
export function TestsPanel({ pid, p }: { pid: number; p: Perm }) {
  const [tick, setTick] = useState(0);
  const list = useLoad<{ items: any[]; summary: any }>(`/projects/${pid}/test-cases`, [tick]);
  const [f, setF] = useState({ title: "", steps: "", expected: "" }); const [lines, setLines] = useState("");
  const [runFor, setRunFor] = useState<{ id: number; status: string } | null>(null); const [sev, setSev] = useState("medium"); const [notes, setNotes] = useState("");
  const [hist, setHist] = useState<number | null>(null);
  const runs = useLoad<{ items: any[] }>(hist ? `/test-cases/${hist}/runs` : null, [hist, tick]);
  const { run, busy, banner } = useAction();
  const refresh = () => setTick((x) => x + 1);
  const s = list.data?.summary;
  const record = async (id: number, status: string) => {
    const body: any = { status, notes, severity: status === "failed" ? sev : "" };
    if (await run(() => api(`/test-cases/${id}/runs`, { method: "POST", body }), "Đã ghi kết quả chạy test.")) { setRunFor(null); setNotes(""); refresh(); }
  };
  return (
    <div className="card">
      <b>Test case & báo cáo lỗi</b>{banner}
      <p className="muted">Trạng thái chỉ đổi khi bạn ghi một lần chạy test thật — hệ thống không tự đánh dấu Passed.</p>
      {s && <p className="row tight"><span className="badge">Tổng {s.total}</span><span className="badge approved">Passed {s.passed}</span><span className="badge failed">Failed {s.failed}</span><span className="badge Blocked">Blocked {s.blocked}</span><span className="badge">Chưa chạy {s.not_run}</span>
        {s.failed > 0 && <span className="muted">Lỗi theo mức: critical {s.bugs_by_severity.critical}, high {s.bugs_by_severity.high}, medium {s.bugs_by_severity.medium}, low {s.bugs_by_severity.low}</span>}</p>}
      <Async loading={list.loading} error={list.error}>
        {list.data?.items.length ? <div className="tablewrap"><table><thead><tr><th>Test case</th><th>Kết quả gần nhất</th><th></th></tr></thead><tbody>
          {list.data.items.map((c) => { const rf = runFor && runFor.id === c.id ? runFor : null; return (
            <tr key={c.id}><td><b>{c.title}</b>{c.steps && <div className="muted">Bước: {c.steps}</div>}{c.expected && <div className="muted">Mong đợi: {c.expected}</div>}
              {c.status === "failed" && c.last_notes && <div style={{ color: "var(--bad)" }}>🐞 [{c.severity}] {c.last_notes}</div>}
              {rf && p.manager && (
                <div className="card">
                  {rf.status === "failed" && <Field label="Mức độ nghiêm trọng"><select value={sev} onChange={(e) => setSev(e.target.value)}>{["low", "medium", "high", "critical"].map((x) => <option key={x}>{x}</option>)}</select></Field>}
                  {rf.status !== "passed" && <Field label={rf.status === "failed" ? "Mô tả lỗi (bước tái hiện, kết quả thực tế) *" : "Lý do bị chặn *"}><textarea value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>}
                  <p className="row tight"><button className="btn" disabled={busy} onClick={() => record(c.id, rf.status)}>Ghi {TST[rf.status]}</button><button className="btn ghost" onClick={() => setRunFor(null)}>Hủy</button></p>
                </div>)}
              {hist === c.id && runs.data && <ul className="timeline">{runs.data.items.map((r) => <li key={r.id}><Badge v={r.status === "passed" ? "approved" : r.status === "failed" ? "failed" : "Blocked"} /> {utc(r.created_at)} · {r.run_by}{r.severity ? ` · ${r.severity}` : ""}{r.notes ? ` — ${r.notes}` : ""}</li>)}</ul>}
            </td>
              <td><Badge v={c.status === "passed" ? "approved" : c.status === "failed" ? "failed" : c.status === "blocked" ? "Blocked" : "draft"} /> {TST[c.status]}{c.last_run_at ? <div className="muted">{utc(c.last_run_at)}</div> : null}</td>
              <td className="row tight">{p.manager && <><button className="btn ghost" onClick={() => { if (window.confirm("Xác nhận bạn ĐÃ chạy test này và nó đạt?")) record(c.id, "passed"); }}>Passed</button>
                <button className="btn ghost" onClick={() => setRunFor({ id: c.id, status: "failed" })}>Failed</button>
                <button className="btn ghost" onClick={() => setRunFor({ id: c.id, status: "blocked" })}>Blocked</button></>}
                <button className="btn ghost" onClick={() => setHist(hist === c.id ? null : c.id)}>Lịch sử</button>
                {p.owner && <button className="btn danger" disabled={busy} onClick={() => run(() => api(`/test-cases/${c.id}`, { method: "DELETE" }), "Đã xóa.", `Xóa test case “${c.title}” và lịch sử chạy?`).then(refresh)}>Xóa</button>}</td></tr>); })}</tbody></table></div> : <Empty text="Chưa có test case." />}
      </Async>
      {p.manager && (<>
        <form onSubmit={async (e) => { e.preventDefault(); if (await run(() => api(`/projects/${pid}/test-cases`, { method: "POST", body: f }), "Đã thêm test case.")) { setF({ title: "", steps: "", expected: "" }); refresh(); } }}>
          <div className="row"><Field label="Tiêu đề *"><input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} required /></Field>
            <Field label="Các bước"><input value={f.steps} onChange={(e) => setF({ ...f, steps: e.target.value })} /></Field>
            <Field label="Kết quả mong đợi"><input value={f.expected} onChange={(e) => setF({ ...f, expected: e.target.value })} /></Field></div>
          <p><button className="btn" disabled={busy}>Thêm test case</button></p>
        </form>
        <details><summary>Nhập nhiều test case (mỗi dòng: tiêu đề | các bước | kết quả mong đợi) — dán kết quả của phòng QA AI vào đây</summary>
          <textarea value={lines} onChange={(e) => setLines(e.target.value)} style={{ minHeight: 100 }} />
          <p><button className="btn" disabled={busy || !lines.trim()} onClick={async () => { if (await run(() => api(`/projects/${pid}/test-cases/import`, { method: "POST", body: { lines } }), "Đã nhập test case.")) { setLines(""); refresh(); } }}>Nhập</button></p></details>
      </>)}
    </div>
  );
}

// ---------------------------------------------------------------- Checklist phát hành
export function ChecklistPanel({ pid, p, only }: { pid: number; p: Perm; only?: string[] }) {
  const [tick, setTick] = useState(0);
  const ck = useLoad<any>(`/projects/${pid}/release-checklist`, [tick]);
  const { run, busy, banner } = useAction();
  return (
    <div className="card"><b>Checklist phát hành</b>{banner}
      <Async loading={ck.loading} error={ck.error}>{ck.data && (<>
        <p className={ck.data.ready ? "msg okk" : "muted"}>{ck.data.ready ? "✅ Đạt đủ điều kiện — việc phát hành vẫn do chủ studio tự thực hiện ngoài hệ thống." : `Đạt ${ck.data.done}/${ck.data.total} mục. Hệ thống không bao giờ tự phát hành.`}</p>
        <ul className="checklist">{ck.data.items.filter((i: any) => !only || only.includes(i.key)).map((i: any) => (
          <li key={i.key} className={i.done ? "done" : ""}>
            <label style={{ margin: 0 }}><input type="checkbox" style={{ width: "auto" }} checked={i.done} disabled={i.auto || busy || !p.manager || (i.key === "owner_approval" && !p.owner)}
              onChange={(e) => run(() => api(`/projects/${pid}/release-checklist/${i.key}`, { method: "PUT", body: { done: e.target.checked } }), "Đã cập nhật.").then(() => setTick((x) => x + 1))} /> {i.label}</label>
            {i.auto && <span className="muted"> · tự động{!i.done && i.detail ? ` — ${i.detail}` : ""}</span>}
            {!i.auto && i.done && <span className="muted"> · {i.by}, {utc(i.at)}</span>}
          </li>))}</ul></>)}</Async>
    </div>
  );
}

// ---------------------------------------------------------------- Build
export function BuildsPanel({ pid, p }: { pid: number; p: Perm }) {
  const [tick, setTick] = useState(0);
  const list = useLoad<{ items: any[] }>(`/projects/${pid}/builds`, [tick]);
  const [f, setF] = useState({ version: "", platform: "windows", status: "planned", file_path: "", changelog: "" });
  const { run, busy, banner } = useAction();
  const refresh = () => setTick((x) => x + 1);
  const setStatus = (id: number, status: string, confirm?: string) => run(() => api(`/builds/${id}/status`, { method: "POST", body: { status } }), "Đã cập nhật build.", confirm).then(refresh);
  return (
    <div className="card"><b>Build & phiên bản</b>{banner}
      <p className="muted">Tệp build phải nằm trong workspace của dự án (đường dẫn tương đối, ví dụ <code>build/game.zip</code>). Hệ thống chỉ ghi nhận — không tự build hay tự phát hành.</p>
      <Async loading={list.loading} error={list.error}>
        {list.data?.items.length ? <div className="tablewrap"><table><thead><tr><th>Phiên bản</th><th>Nền tảng</th><th>Trạng thái</th><th>Tệp</th><th>Changelog</th><th></th></tr></thead><tbody>
          {list.data.items.map((b) => (<tr key={b.id}><td>{b.version}</td><td>{b.platform}</td><td><Badge v={b.status === "released" || b.status === "ready" ? "approved" : b.status === "failed" ? "failed" : "draft"} /> {b.status}</td><td><code>{b.file_path || "—"}</code></td><td>{b.changelog}</td>
            <td className="row tight">{p.manager && b.status === "planned" && b.file_path && <button className="btn ghost" disabled={busy} onClick={() => setStatus(b.id, "ready")}>Đánh dấu sẵn sàng</button>}
              {p.manager && b.status !== "failed" && b.status !== "released" && <button className="btn ghost" disabled={busy} onClick={() => setStatus(b.id, "failed")}>Lỗi build</button>}
              {p.owner && b.status === "ready" && <button className="btn" disabled={busy} onClick={() => setStatus(b.id, "released", "Đánh dấu build này là ĐÃ PHÁT HÀNH? (Chỉ ghi nhận; hệ thống không tự đăng lên cửa hàng.)")}>Ghi nhận đã phát hành</button>}</td></tr>))}</tbody></table></div> : <Empty text="Chưa có build." />}
      </Async>
      {p.manager && (
        <form onSubmit={async (e) => { e.preventDefault(); if (await run(() => api(`/projects/${pid}/builds`, { method: "POST", body: f }), "Đã thêm build.")) { setF({ ...f, version: "", file_path: "", changelog: "" }); refresh(); } }}>
          <div className="row">
            <Field label="Phiên bản *"><input value={f.version} onChange={(e) => setF({ ...f, version: e.target.value })} required placeholder="0.1.0" /></Field>
            <Field label="Nền tảng"><select value={f.platform} onChange={(e) => setF({ ...f, platform: e.target.value })}>{["windows", "linux", "macos", "android", "ios", "web", "other"].map((x) => <option key={x}>{x}</option>)}</select></Field>
            <Field label="Trạng thái"><select value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}><option value="planned">planned</option><option value="ready">ready (cần có tệp)</option><option value="failed">failed</option></select></Field>
            <Field label="Tệp build (trong workspace)"><input value={f.file_path} onChange={(e) => setF({ ...f, file_path: e.target.value })} placeholder="build/game.zip" /></Field>
          </div>
          <Field label="Changelog"><textarea value={f.changelog} onChange={(e) => setF({ ...f, changelog: e.target.value })} /></Field>
          <p><button className="btn" disabled={busy}>Thêm build</button></p>
        </form>)}
    </div>
  );
}

// ---------------------------------------------------------------- Tài chính
const FIN_CAT: Record<string, string> = { ai_subscription: "Gói AI thuê bao", tool: "Công cụ/phần mềm", asset_purchase: "Mua tài sản", ads: "Quảng cáo", iap: "Mua hàng trong game", store_fee: "Phí cửa hàng", contractor: "Thuê ngoài", other: "Khác" };
export function FinancePanel({ pid, p }: { pid: number | null; p: Perm }) {
  const [tick, setTick] = useState(0);
  const q = pid ? `?project_id=${pid}` : "";
  const sum = useLoad<any>(p.manager ? `/finance/summary${q}` : null, [tick]);
  const list = useLoad<{ items: any[] }>(p.manager ? `/finance/records${q}` : null, [tick]);
  const today = new Date().toISOString().slice(0, 10);
  const [f, setF] = useState({ kind: "cost", category: "ai_subscription", amount: "", currency: "USD", occurred_on: today, note: "", estimated: false });
  const { run, busy, banner } = useAction();
  const refresh = () => setTick((x) => x + 1);
  if (!p.manager) return <div className="card"><Empty text="Chỉ quản lý và chủ studio xem được tài chính." /></div>;
  return (
    <div className="card"><b>Chi phí & doanh thu {pid ? "của dự án" : "toàn studio"}</b>{banner}
      <p className="muted">Mọi số liệu do bạn nhập; hệ thống không bịa hay ước đoán. Doanh thu chỉ được tính sau khi <b>chủ studio xác nhận</b>; chi phí ước tính tách riêng khỏi chi phí thực tế; các loại tiền không bị quy đổi lẫn nhau.</p>
      <Async loading={sum.loading} error={sum.error}>{sum.data && (<>
        {sum.data.currencies.length ? <div className="kpis">{sum.data.currencies.map((c: any) => (
          <div key={c.currency} className="kpi" style={{ gridColumn: "span 2" }}><b>{c.profit.toFixed(2)} {c.currency}</b><span>Lợi nhuận (doanh thu xác nhận − chi phí thực tế)</span>
            <span>Chi thực tế {c.cost_actual.toFixed(2)} · Chi ước tính {c.cost_estimated.toFixed(2)} · Thu đã xác nhận {c.revenue_confirmed.toFixed(2)} · Thu chờ xác nhận {c.revenue_pending.toFixed(2)}</span></div>))}</div> : <Empty text="Chưa có bản ghi tài chính." />}
        {sum.data.ai_runs_this_month.length > 0 && <p className="muted">Lượt chạy AI tháng này: {sum.data.ai_runs_this_month.map((r: any) => `${r.department_key || "—"}/${r.provider}: ${r.runs}`).join(" · ")}. {sum.data.note}</p>}</>)}</Async>
      <Async loading={list.loading} error={list.error}>
        {list.data?.items.length ? <div className="tablewrap"><table><thead><tr><th>Ngày</th><th>Loại</th><th>Danh mục</th><th>Số tiền</th><th>Trạng thái</th><th>Ghi chú</th><th></th></tr></thead><tbody>
          {list.data.items.map((r) => (<tr key={r.id}><td>{r.occurred_on}</td><td>{r.kind === "cost" ? "Chi" : "Thu"}</td><td>{FIN_CAT[r.category]}</td><td>{r.amount} {r.currency}</td>
            <td>{r.kind === "cost" ? (r.estimated ? "Ước tính" : "Thực tế") : r.confirmed ? `Đã xác nhận (${r.confirmed_by})` : "Chờ xác nhận"}</td><td>{r.note}</td>
            <td className="row tight">{p.owner && r.kind === "revenue" && !r.confirmed && <button className="btn" disabled={busy} onClick={() => run(() => api(`/finance/records/${r.id}/confirm`, { method: "POST" }), "Đã xác nhận doanh thu.", "Xác nhận khoản doanh thu này đã thực sự nhận được?").then(refresh)}>Xác nhận</button>}
              {p.owner && <button className="btn danger" disabled={busy} onClick={() => run(() => api(`/finance/records/${r.id}`, { method: "DELETE" }), "Đã xóa.", "Xóa bản ghi này?").then(refresh)}>Xóa</button>}</td></tr>))}</tbody></table></div> : null}
      </Async>
      <form onSubmit={async (e) => { e.preventDefault(); if (await run(() => api("/finance/records", { method: "POST", body: { ...f, project_id: pid } }), "Đã ghi nhận (doanh thu cần chủ studio xác nhận).")) { setF({ ...f, amount: "", note: "" }); refresh(); } }}>
        <div className="row">
          <Field label="Loại"><select value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value, estimated: false })}><option value="cost">Chi phí</option><option value="revenue">Doanh thu</option></select></Field>
          <Field label="Danh mục"><select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>{Object.entries(FIN_CAT).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>
          <Field label="Số tiền *"><input value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} required placeholder="20.00" /></Field>
          <Field label="Tiền tệ"><input value={f.currency} onChange={(e) => setF({ ...f, currency: e.target.value.toUpperCase() })} maxLength={3} /></Field>
          <Field label="Ngày"><input type="date" value={f.occurred_on} onChange={(e) => setF({ ...f, occurred_on: e.target.value })} required /></Field>
        </div>
        <div className="row"><Field label="Ghi chú"><input value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></Field>
          {f.kind === "cost" && <label style={{ margin: 0 }}><input type="checkbox" style={{ width: "auto" }} checked={f.estimated} onChange={(e) => setF({ ...f, estimated: e.target.checked })} /> Đây là chi phí ước tính (chưa phát sinh thật)</label>}</div>
        <p><button className="btn" disabled={busy}>Ghi nhận</button></p>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------- Analytics
export function AnalyticsPanel({ pid, p }: { pid: number; p: Perm }) {
  const [tick, setTick] = useState(0);
  const list = useLoad<{ items: any[] }>(`/projects/${pid}/analytics`, [tick]);
  const blank = { title: "", source: "", period_start: "", period_end: "", metrics: "", limitations: "", summary: "" };
  const [f, setF] = useState(blank);
  const { run, busy, banner } = useAction();
  const parse = () => { const m: Record<string, number> = {}; f.metrics.split("\n").forEach((l) => { const [k, v] = l.split("="); if (k && v !== undefined && k.trim() && v.trim() !== "" && !isNaN(Number(v))) m[k.trim()] = Number(v); }); return m; };
  return (
    <div className="card"><b>Báo cáo analytics</b>{banner}
      <p className="muted">Chỉ nhập dữ liệu THẬT từ nguồn đã kết nối (xuất từ cửa hàng, công cụ analytics…). Mỗi báo cáo bắt buộc ghi nguồn, khoảng thời gian và hạn chế của dữ liệu.</p>
      <Async loading={list.loading} error={list.error}>
        {list.data?.items.length ? list.data.items.map((r) => (
          <div key={r.id} className="card"><b>{r.title}</b> <span className="muted">· {r.period_start} → {r.period_end} · nguồn: {r.source}</span>
            {Object.keys(r.metrics).length > 0 && <p className="row tight">{Object.entries(r.metrics).map(([k, v]) => <span key={k} className="badge">{k}: {String(v)}</span>)}</p>}
            {r.summary && <p>{r.summary}</p>}<p className="muted">⚠ Hạn chế: {r.limitations}</p>
            {p.owner && <button className="btn danger" disabled={busy} onClick={() => run(() => api(`/analytics/${r.id}`, { method: "DELETE" }), "Đã xóa.", "Xóa báo cáo này?").then(() => setTick((x) => x + 1))}>Xóa</button>}</div>)) : <Empty text="Chưa có báo cáo." />}
      </Async>
      {p.manager && (
        <form onSubmit={async (e) => { e.preventDefault(); if (await run(() => api(`/projects/${pid}/analytics`, { method: "POST", body: { ...f, metrics: parse() } }), "Đã lưu báo cáo.")) { setF(blank); setTick((x) => x + 1); } }}>
          <div className="row"><Field label="Tiêu đề *"><input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} required /></Field>
            <Field label="Nguồn dữ liệu *"><input value={f.source} onChange={(e) => setF({ ...f, source: e.target.value })} required minLength={3} placeholder="VD: Google Play Console, xuất tay" /></Field>
            <Field label="Từ ngày *"><input type="date" value={f.period_start} onChange={(e) => setF({ ...f, period_start: e.target.value })} required /></Field>
            <Field label="Đến ngày *"><input type="date" value={f.period_end} onChange={(e) => setF({ ...f, period_end: e.target.value })} required /></Field></div>
          <Field label="Chỉ số (mỗi dòng: tên = số)"><textarea value={f.metrics} onChange={(e) => setF({ ...f, metrics: e.target.value })} placeholder={"D1 retention % = 31.5\ncrash rate % = 0.4"} /></Field>
          <Field label="Hạn chế của dữ liệu *"><textarea value={f.limitations} onChange={(e) => setF({ ...f, limitations: e.target.value })} required minLength={3} placeholder="VD: chỉ 120 người dùng, chưa đủ ý nghĩa thống kê" /></Field>
          <Field label="Nhận định / đề xuất"><textarea value={f.summary} onChange={(e) => setF({ ...f, summary: e.target.value })} /></Field>
          <p><button className="btn" disabled={busy}>Lưu báo cáo</button></p>
        </form>)}
    </div>
  );
}

// ---------------------------------------------------------------- Tài sản (tóm tắt theo loại)
export function AssetsMini({ pid, kind, go }: { pid: number; kind?: string; go: (p: string) => void }) {
  const list = useLoad<{ items: any[]; summary: any }>(`/projects/${pid}/assets?kind=${kind || ""}`);
  return (
    <div className="card"><b>Tài sản {kind === "image" ? "đồ họa" : kind === "audio" ? "âm thanh" : "của dự án"}</b>{" "}
      <button className="btn ghost" onClick={() => go("assets")}>Mở Thư viện tài sản →</button>
      <Async loading={list.loading} error={list.error}>
        {list.data?.items.length ? <div className="tablewrap"><table><thead><tr><th>Tên</th><th>Nguồn</th><th>Trạng thái</th><th>Vấn đề</th></tr></thead><tbody>
          {list.data.items.slice(0, 12).map((a) => <tr key={a.id}><td>{a.name}</td><td>{a.source}</td><td><Badge v={a.status} /></td><td>{a.problems.length ? <span style={{ color: "var(--bad)" }}>{a.problems.join("; ")}</span> : "—"}</td></tr>)}</tbody></table></div>
          : <Empty text="Chưa có tài sản. Phòng này chỉ tạo brief/prompt; tệp thật phải do bạn hoặc công cụ ngoài tạo rồi tải lên Thư viện tài sản." />}
      </Async>
    </div>
  );
}

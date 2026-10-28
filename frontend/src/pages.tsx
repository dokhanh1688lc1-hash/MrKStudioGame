import { useState } from "react";
import { api, upload, usd, useLoad, utc } from "./api";
import { Async, Badge, Empty, Field, Pager, useAction } from "./ui";

type Role = { role: string };
const canEdit = (r: string) => r === "manager" || r === "owner";

// ---------------- Dashboard ----------------
export function Dashboard({ go }: { go: (p: string) => void }) {
  const d = useLoad<any>("/dashboard");
  return (
    <>
      <h2>CEO Dashboard</h2>
      <Async loading={d.loading} error={d.error}>
        {d.data && (
          <>
            <div className="grid">
              <div className="stat"><b>{d.data.projects_total}</b><span>Dự án</span></div>
              <div className="stat"><b>{d.data.tasks_total}</b><span>Nhiệm vụ</span></div>
              <div className="stat" style={{ cursor: "pointer" }} onClick={() => go("approvals")}>
                <b>{d.data.pending_approvals}</b><span>Chờ phê duyệt</span></div>
              <div className="stat"><b>${d.data.spend_today_usd.toFixed(4)}</b><span>Chi phí hôm nay (đã biết giá)</span></div>
              <div className="stat"><b>${d.data.spend_month_usd.toFixed(4)}</b><span>Chi phí tháng này (đã biết giá)</span></div>
            </div>
            {d.data.usage_records_without_price > 0 && (
              <div className="msg">⚠ {d.data.usage_records_without_price} lần gọi chưa tính được chi phí vì chưa cấu hình giá provider.</div>
            )}
            <div className="card">
              <b>Nhiệm vụ theo trạng thái</b>
              {Object.keys(d.data.tasks_by_status).length === 0 ? <Empty text="Chưa có nhiệm vụ." /> : (
                <p>{Object.entries(d.data.tasks_by_status).map(([k, v]) => <span key={k}><Badge v={k} /> {String(v)}&nbsp;&nbsp;</span>)}</p>
              )}
            </div>
            <div className="card">
              <b>Nhà cung cấp AI</b>
              <div className="tablewrap"><table><tbody>
                {d.data.providers.map((p: any) => (
                  <tr key={p.name}><td>{p.name}</td>
                    <td>{p.configured ? "Đã có khóa" : "Chưa cấu hình khóa"}</td>
                    <td>{p.enabled ? "Bật" : "Tắt"}</td><td><Badge v={p.last_check_status} /></td></tr>
                ))}
              </tbody></table></div>
              <p className="muted">Chỉ báo “ok” sau khi bạn bấm “Kiểm tra kết nối” thành công. Không có khóa → hệ thống chạy chế độ nội bộ (không gọi AI).</p>
            </div>
          </>
        )}
      </Async>
    </>
  );
}

// ---------------- Projects ----------------
const PSTAT = ["Research", "Concept", "Pre-production", "Prototype", "Production", "QA", "Release Preparation", "Live Operations", "Paused", "Archived"];

export function Projects({ role }: Role) {
  const [q, setQ] = useState(""); const [status, setStatus] = useState(""); const [offset, setOffset] = useState(0);
  const list = useLoad<{ items: any[]; total: number }>(`/projects?limit=10&offset=${offset}&q=${encodeURIComponent(q)}&status=${status}`);
  const [f, setF] = useState({ name: "", genre: "", platform: "", target_market: "", description: "" });
  const { run, busy, banner } = useAction();
  const [edit, setEdit] = useState<any | null>(null);
  const [codeFor, setCodeFor] = useState<any | null>(null);
  return (
    <>
      <h2>Dự án</h2>
      {banner}
      {canEdit(role) && (
        <form className="card" onSubmit={async (e) => {
          e.preventDefault();
          if (await run(() => api("/projects", { method: "POST", body: f }), "Đã tạo dự án.")) { setF({ name: "", genre: "", platform: "", target_market: "", description: "" }); list.reload(); }
        }}>
          <b>Tạo dự án mới</b>
          <div className="row">
            <Field label="Tên game *"><input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required /></Field>
            <Field label="Thể loại"><input value={f.genre} onChange={(e) => setF({ ...f, genre: e.target.value })} /></Field>
            <Field label="Nền tảng"><input value={f.platform} onChange={(e) => setF({ ...f, platform: e.target.value })} /></Field>
            <Field label="Thị trường mục tiêu"><input value={f.target_market} onChange={(e) => setF({ ...f, target_market: e.target.value })} /></Field>
          </div>
          <Field label="Mô tả"><textarea value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field>
          <p><button className="btn" disabled={busy}>Tạo dự án</button></p>
        </form>
      )}
      <div className="card">
        <div className="row">
          <Field label="Tìm kiếm"><input value={q} onChange={(e) => { setQ(e.target.value); setOffset(0); }} placeholder="Tên, mô tả, thể loại…" /></Field>
          <Field label="Trạng thái">
            <select value={status} onChange={(e) => { setStatus(e.target.value); setOffset(0); }}>
              <option value="">Tất cả</option>{PSTAT.map((s) => <option key={s}>{s}</option>)}
            </select>
          </Field>
        </div>
        <Async loading={list.loading} error={list.error}>
          {list.data?.items.length ? (
            <div className="tablewrap"><table>
              <thead><tr><th>ID</th><th>Tên</th><th>Thể loại</th><th>Nền tảng</th><th>Trạng thái</th><th></th></tr></thead>
              <tbody>{list.data.items.map((p) => (
                <tr key={p.id}><td>{p.id}</td><td>{p.name}<div className="muted">{p.description}</div></td><td>{p.genre}</td><td>{p.platform}</td>
                  <td>{canEdit(role) ? (
                    <select value={p.status} onChange={(e) => run(() => api(`/projects/${p.id}`, { method: "PATCH", body: { status: e.target.value } }), "Đã cập nhật trạng thái.", e.target.value === "Archived" ? "Lưu trữ dự án này? Không thể tạo thêm nhiệm vụ cho dự án đã lưu trữ." : undefined).then(list.reload)}>
                      {PSTAT.map((s) => <option key={s}>{s}</option>)}</select>) : <Badge v={p.status} />}</td>
                  <td className="row tight">
                    {canEdit(role) && <button className="btn ghost" onClick={() => { setEdit({ ...p }); setCodeFor(null); }}>Sửa</button>}
                    <button className="btn ghost" onClick={() => { setCodeFor(p); setEdit(null); }}>Mã nguồn</button></td></tr>
              ))}</tbody></table></div>
          ) : <Empty text="Chưa có dự án nào khớp. Hãy tạo dự án đầu tiên ở trên." />}
          {list.data && <Pager total={list.data.total} offset={offset} limit={10} onChange={setOffset} />}
        </Async>
      </div>
      {edit && (
        <form className="card" onSubmit={async (e) => {
          e.preventDefault();
          const { name, genre, platform, target_market, description } = edit;
          if (await run(() => api(`/projects/${edit.id}`, { method: "PATCH", body: { name, genre, platform, target_market, description } }), "Đã lưu thay đổi dự án.")) { setEdit(null); list.reload(); }
        }}>
          <div className="row tight"><b>Sửa dự án #{edit.id}</b><button type="button" className="btn ghost" onClick={() => setEdit(null)}>Đóng</button></div>
          <div className="row">
            <Field label="Tên game *"><input value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} required /></Field>
            <Field label="Thể loại"><input value={edit.genre} onChange={(e) => setEdit({ ...edit, genre: e.target.value })} /></Field>
            <Field label="Nền tảng"><input value={edit.platform} onChange={(e) => setEdit({ ...edit, platform: e.target.value })} /></Field>
            <Field label="Thị trường mục tiêu"><input value={edit.target_market} onChange={(e) => setEdit({ ...edit, target_market: e.target.value })} /></Field>
          </div>
          <Field label="Mô tả"><textarea value={edit.description} onChange={(e) => setEdit({ ...edit, description: e.target.value })} /></Field>
          <p><button className="btn" disabled={busy}>Lưu</button></p>
        </form>
      )}
      {codeFor && <ProjectCode project={codeFor} role={role} onClose={() => setCodeFor(null)} />}
    </>
  );
}

function ProjectCode({ project, role, onClose }: { project: any; role: string; onClose: () => void }) {
  const [tick, setTick] = useState(0);
  const tree = useLoad<any>(`/projects/${project.id}/files`, [tick]);
  const [picked, setPicked] = useState<File[]>([]);
  const [view, setView] = useState<string | null>(null);
  const content = useLoad<any>(view ? `/projects/${project.id}/files/content?path=${encodeURIComponent(view)}` : null);
  const [up, setUp] = useState<any | null>(null);
  const [goal, setGoal] = useState(""); const [sens, setSens] = useState(false);
  const { run, busy, banner } = useAction();
  return (
    <div className="card">
      <div className="row tight"><b>Mã nguồn dự án: {project.name}</b><button className="btn ghost" onClick={onClose}>Đóng</button></div>
      {banner}
      {canEdit(role) && project.status !== "Archived" && (
        <>
          <div className="msg">Tải lên dự án đang làm (ví dụ tệp .zip tải về từ Claude, hoặc từng tệp .gd/.py/…). Mỗi lần tải tạo một thư mục <code>imports/</code> mới, không ghi đè bản cũ. Tệp bí mật (.env, khóa riêng), .git, node_modules và symlink bị bỏ qua. Tối đa 100 MB mỗi lần.</div>
          <div className="row tight">
            <input type="file" multiple style={{ width: "auto" }} onChange={(e) => setPicked(Array.from(e.target.files || []))} />
            <button className="btn" disabled={busy || !picked.length} onClick={async () => {
              if (await run(async () => setUp(await upload(`/projects/${project.id}/files`, picked)), "Đã tải lên.")) { setPicked([]); setTick((x) => x + 1); }
            }}>Tải lên</button>
          </div>
          {up && <div className="msg okk">Đã nhập {up.files_saved} tệp vào <code>imports/{up.import}</code>.{up.skipped.length > 0 && <> Bỏ qua {up.skipped.length}: {up.skipped.slice(0, 5).join(", ")}{up.skipped.length > 5 ? "…" : ""}</>}</div>}
        </>
      )}
      <Async loading={tree.loading} error={tree.error}>
        {tree.data?.files.length ? (
          <>
            <p className="muted">{tree.data.files.length} tệp{tree.data.truncated ? " (đã cắt bớt)" : ""} · các lần nhập: {tree.data.imports.join(", ") || "—"}</p>
            <div className="tablewrap" style={{ maxHeight: 260, overflow: "auto" }}><table><tbody>
              {tree.data.files.map((f: any) => <tr key={f.path}><td><a href="#" onClick={(e) => { e.preventDefault(); setView(f.path); }}>{f.path}</a></td><td className="muted">{f.size} B</td></tr>)}
            </tbody></table></div>
            {view && (
              <Async loading={content.loading} error={content.error}>
                {content.data && <><p className="muted">{content.data.path}{content.data.truncated ? " (đã cắt bớt)" : ""} · chuỗi giống khóa/mật khẩu được che</p><pre className="out">{content.data.content}</pre></>}
              </Async>
            )}
            {canEdit(role) && (
              <form onSubmit={async (e) => {
                e.preventDefault();
                await run(() => api(`/projects/${project.id}/upgrade-task`, { method: "POST", body: { goal, sensitive: sens } }), "Đã tạo nhiệm vụ phân tích & nâng cấp. Vào Task Center để bấm Chạy.", "Nhiệm vụ sẽ gửi tóm tắt mã nguồn (đã che khóa) tới nhà cung cấp AI nếu có cấu hình. Tiếp tục?");
              }}>
                <b>Phân tích & nâng cấp bằng AI (Game Development AI)</b>
                <Field label="Mục tiêu (lỗi cần sửa, tính năng cần thêm…)"><textarea value={goal} onChange={(e) => setGoal(e.target.value)} required minLength={3} /></Field>
                <p className="row tight">
                  <label style={{ margin: 0 }}><input type="checkbox" style={{ width: "auto" }} checked={sens} onChange={(e) => setSens(e.target.checked)} /> Mã nguồn nhạy cảm (chỉ gửi provider được cấp quyền)</label>
                  <button className="btn" disabled={busy}>Tạo nhiệm vụ</button>
                </p>
                <p className="muted">AI trả về báo cáo, kế hoạch và đoạn mã đề xuất; hệ thống không tự sửa tệp của bạn. Sau khi chạy xong, dùng “Lưu vào workspace” trong chi tiết nhiệm vụ để lưu kết quả thành tệp .md.</p>
              </form>
            )}
          </>
        ) : <Empty text="Workspace chưa có tệp. Hãy tải mã nguồn lên." />}
      </Async>
    </div>
  );
}

// ---------------- Tasks ----------------
const TSTAT = ["Pending", "Planned", "Assigned", "Running", "Blocked", "Awaiting Approval", "Completed", "Failed", "Cancelled"];

export function Tasks({ role }: Role) {
  const [status, setStatus] = useState(""); const [q, setQ] = useState(""); const [offset, setOffset] = useState(0);
  const [tick, setTick] = useState(0);
  const list = useLoad<{ items: any[]; total: number }>(`/tasks?limit=10&offset=${offset}&status=${status}&q=${encodeURIComponent(q)}`, [tick]);
  const projects = useLoad<{ items: any[] }>("/projects?limit=100");
  const depts = useLoad<any[]>("/departments");
  const [sel, setSel] = useState<number | null>(null);
  const detail = useLoad<any>(sel ? `/tasks/${sel}` : null, [tick]);
  const blank = { project_id: "", department_key: "", title: "", objective: "", context: "", acceptance_criteria: "", provider: "", sensitive: false, requires_approval: false };
  const [f, setF] = useState<any>(blank);
  const [savedPath, setSavedPath] = useState("");
  const { run, busy, banner } = useAction();
  const refresh = () => setTick((t) => t + 1);

  return (
    <>
      <h2>Task Center</h2>
      {banner}
      {canEdit(role) && (
        <form className="card" onSubmit={async (e) => {
          e.preventDefault();
          const body = { ...f, project_id: Number(f.project_id), provider: f.provider || null };
          if (await run(() => api("/tasks", { method: "POST", body }), "Đã tạo nhiệm vụ.")) { setF(blank); refresh(); }
        }}>
          <b>Giao nhiệm vụ mới</b>
          <div className="row">
            <Field label="Dự án *"><select value={f.project_id} onChange={(e) => setF({ ...f, project_id: e.target.value })} required>
              <option value="">— chọn —</option>{projects.data?.items.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></Field>
            <Field label="Phòng ban *"><select value={f.department_key} onChange={(e) => setF({ ...f, department_key: e.target.value })} required>
              <option value="">— chọn —</option>{depts.data?.map((d) => <option key={d.key} value={d.key}>{d.name} (ưu tiên {d.preferred_provider})</option>)}</select></Field>
            <Field label="Provider (để trống = theo routing)"><select value={f.provider} onChange={(e) => setF({ ...f, provider: e.target.value })}>
              <option value="">Tự động theo routing</option><option>openai</option><option>anthropic</option><option>claude_cli</option><option>codex_cli</option><option>internal</option></select></Field>
          </div>
          <Field label="Tiêu đề *"><input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} required /></Field>
          <Field label="Mục tiêu *"><textarea value={f.objective} onChange={(e) => setF({ ...f, objective: e.target.value })} required /></Field>
          <div className="row">
            <Field label="Bối cảnh / đầu vào"><textarea value={f.context} onChange={(e) => setF({ ...f, context: e.target.value })} /></Field>
            <Field label="Tiêu chí nghiệm thu"><textarea value={f.acceptance_criteria} onChange={(e) => setF({ ...f, acceptance_criteria: e.target.value })} /></Field>
          </div>
          <p className="row tight">
            <label style={{ margin: 0 }}><input type="checkbox" style={{ width: "auto" }} checked={f.sensitive} onChange={(e) => setF({ ...f, sensitive: e.target.checked })} /> Dữ liệu nhạy cảm (chỉ gửi provider được cấp quyền)</label>
            <label style={{ margin: 0 }}><input type="checkbox" style={{ width: "auto" }} checked={f.requires_approval} onChange={(e) => setF({ ...f, requires_approval: e.target.checked })} /> Cần phê duyệt trước khi chạy</label>
            <button className="btn" disabled={busy}>Tạo nhiệm vụ</button>
          </p>
        </form>
      )}
      <div className="card">
        <div className="row">
          <Field label="Tìm kiếm"><input value={q} onChange={(e) => { setQ(e.target.value); setOffset(0); }} /></Field>
          <Field label="Trạng thái"><select value={status} onChange={(e) => { setStatus(e.target.value); setOffset(0); }}>
            <option value="">Tất cả</option>{TSTAT.map((s) => <option key={s}>{s}</option>)}</select></Field>
          <button className="btn ghost" style={{ flex: "0 0 auto" }} onClick={refresh}>Làm mới</button>
        </div>
        <Async loading={list.loading} error={list.error}>
          {list.data?.items.length ? (
            <div className="tablewrap"><table>
              <thead><tr><th>ID</th><th>Tiêu đề</th><th>Phòng ban</th><th>Trạng thái</th><th>Chi phí ước tính / thực tế</th><th></th></tr></thead>
              <tbody>{list.data.items.map((t) => (
                <tr key={t.id}><td>{t.id}</td><td>{t.title}</td><td>{t.department_key}</td><td><Badge v={t.status} /></td>
                  <td>{usd(t.estimated_cost)} / {usd(t.actual_cost)}</td>
                  <td className="row tight">
                    <button className="btn ghost" onClick={() => setSel(t.id)}>Chi tiết</button>
                    {canEdit(role) && ["Pending", "Planned", "Assigned", "Blocked", "Failed"].includes(t.status) &&
                      <button className="btn" disabled={busy} onClick={async () => { await run(() => api(`/tasks/${t.id}/run`, { method: "POST" }), "Đã bắt đầu chạy nhiệm vụ."); refresh(); setTimeout(refresh, 1500); }}>Chạy</button>}
                    {canEdit(role) && !["Completed", "Cancelled"].includes(t.status) &&
                      <button className="btn danger" disabled={busy} onClick={async () => { await run(() => api(`/tasks/${t.id}/cancel`, { method: "POST" }), "Đã hủy nhiệm vụ.", "Hủy nhiệm vụ này?"); refresh(); }}>Hủy</button>}
                  </td></tr>
              ))}</tbody></table></div>
          ) : <Empty text="Chưa có nhiệm vụ nào." />}
          {list.data && <Pager total={list.data.total} offset={offset} limit={10} onChange={setOffset} />}
        </Async>
      </div>
      {sel && (
        <div className="card">
          <div className="row tight"><b>Nhiệm vụ #{sel}</b><button className="btn ghost" onClick={() => setSel(null)}>Đóng</button></div>
          <Async loading={detail.loading} error={detail.error}>
            {detail.data && (
              <>
                <p><Badge v={detail.data.status} /> {detail.data.title}</p>
                {detail.data.error && <div className="msg err">{detail.data.error}</div>}
                {detail.data.result && (
                  <>
                    <p className="muted">Kết quả do: <b>{detail.data.result_source}</b>
                      {canEdit(role) && <> · <button className="btn ghost" disabled={busy} onClick={() => run(async () => { const r = await api(`/tasks/${detail.data.id}/save-to-workspace`, { method: "POST" }); setSavedPath(r.path); }, "Đã lưu vào workspace dự án.")}>Lưu vào workspace</button></>}
                      {savedPath && <> · <code>{savedPath}</code></>}</p>
                    <pre className="out">{detail.data.result}</pre>
                  </>
                )}
                <b>Lần chạy ({detail.data.attempts.length})</b>
                <div className="tablewrap"><table><thead><tr><th>#</th><th>Provider/model</th><th>Trạng thái</th><th>Token vào/ra</th><th>Chi phí</th><th>Lỗi</th></tr></thead>
                  <tbody>{detail.data.attempts.map((a: any) => (
                    <tr key={a.id}><td>{a.id}</td><td>{a.provider}/{a.model}</td><td><Badge v={a.status} /></td>
                      <td>{a.input_tokens ?? "—"} / {a.output_tokens ?? "—"}</td><td>{usd(a.cost_usd)}</td><td>{a.error}</td></tr>))}</tbody></table></div>
              </>
            )}
          </Async>
        </div>
      )}
    </>
  );
}

// ---------------- Agents ----------------
export function Agents({ role }: Role) {
  const deps = useLoad<any[]>("/departments");
  const ag = useLoad<any[]>("/agents");
  const { run, banner } = useAction();
  return (
    <>
      <h2>Phòng ban & Agent</h2>{banner}
      <Async loading={deps.loading || ag.loading} error={deps.error || ag.error}>
        <div className="card tablewrap"><table>
          <thead><tr><th>Phòng ban</th><th>Mô tả</th><th>Provider ưu tiên</th><th>Agent</th></tr></thead>
          <tbody>{deps.data?.map((d) => {
            const a = ag.data?.find((x) => x.department_id === d.id);
            return (
              <tr key={d.key}><td>{d.name}</td><td className="muted">{d.description}</td>
                <td>{role === "owner" ? (
                  <select value={d.preferred_provider} onChange={(e) => run(() => api(`/departments/${d.key}`, { method: "PATCH", body: { preferred_provider: e.target.value } }), "Đã đổi provider ưu tiên.").then(deps.reload)}>
                    <option>openai</option><option>anthropic</option></select>) : d.preferred_provider}</td>
                <td>{a && (role === "owner" ? (
                  <label style={{ margin: 0 }}><input type="checkbox" style={{ width: "auto" }} checked={a.enabled} onChange={(e) => run(() => api(`/agents/${a.id}`, { method: "PATCH", body: { enabled: e.target.checked } }), "Đã cập nhật agent.").then(ag.reload)} /> {a.enabled ? "Bật" : "Tắt"}</label>
                ) : (a.enabled ? "Bật" : "Tắt"))}</td></tr>);
          })}</tbody></table></div>
      </Async>
    </>
  );
}

// ---------------- Providers ----------------
export function Providers({ role }: Role) {
  const ps = useLoad<any[]>("/providers");
  const { run, busy, banner } = useAction();
  const [edit, setEdit] = useState<Record<string, any>>({});
  const [dept, setDept] = useState("game_dev");
  const deps = useLoad<any[]>("/departments");
  const prev = useLoad<any>(`/routing/preview?department=${dept}`, [ps.data]);
  return (
    <>
      <h2>AI Provider & Routing</h2>{banner}
      <div className="msg">API key chỉ nằm trong biến môi trường của backend (file <code>.env</code>), không bao giờ hiển thị đầy đủ hay lưu vào database. Model ID và giá do bạn tự cấu hình bên dưới; hệ thống không tự bịa giá.</div>
      <Async loading={ps.loading} error={ps.error}>
        {ps.data?.map((p) => {
          const e = edit[p.name] || {};
          const val = (k: string) => (k in e ? e[k] : p[k] ?? "");
          const set = (k: string, v: any) => setEdit({ ...edit, [p.name]: { ...e, [k]: v } });
          return (
            <div className="card" key={p.name}>
              <div className="row tight"><b style={{ fontSize: 17 }}>{p.name}</b>
                <span>{p.kind === "cli" ? (p.configured ? `Chương trình: ${p.masked_key}` : "Chưa tìm thấy chương trình trên máy") : p.configured ? `Khóa: ${p.masked_key || "(nội bộ)"}` : "Chưa có API key"}</span>
                <Badge v={p.last_check_status} /><span className="muted">{p.last_check_message} {p.last_check_at && `(${utc(p.last_check_at)})`}</span></div>
              {p.name !== "internal" && role === "owner" && (
                <div className="row">
                  <Field label={p.kind === "cli" ? "Model (để trống = mặc định của chương trình)" : "Model ID mặc định"}><input value={val("default_model")} onChange={(ev) => set("default_model", ev.target.value)} /></Field>
                  {p.kind === "api" && <><Field label="Giá input (USD / 1 triệu token)"><input type="number" step="any" min="0" value={val("price_in_per_mtok")} onChange={(ev) => set("price_in_per_mtok", ev.target.value === "" ? null : Number(ev.target.value))} /></Field>
                  <Field label="Giá output (USD / 1 triệu token)"><input type="number" step="any" min="0" value={val("price_out_per_mtok")} onChange={(ev) => set("price_out_per_mtok", ev.target.value === "" ? null : Number(ev.target.value))} /></Field></>}
                </div>
              )}
              {p.kind === "cli" && <p className="muted">Dùng tài khoản {p.name === "claude_cli" ? "Claude" : "ChatGPT"} đã đăng nhập sẵn trên máy qua chương trình dòng lệnh (không cần API key). Tính vào hạn mức gói thuê bao của bạn, không tính tiền theo token, nên hệ thống không theo dõi chi phí USD cho provider này. Chạy chậm hơn API; chỉ trả về văn bản, không sửa tệp. Mặc định TẮT: bấm “Kiểm tra kết nối” rồi bật.</p>}
              <p className="row tight">
                {role === "owner" && <>
                  <label style={{ margin: 0 }}><input type="checkbox" style={{ width: "auto" }} checked={p.enabled} onChange={(ev) => run(() => api(`/providers/${p.name}`, { method: "PATCH", body: { enabled: ev.target.checked } }), "Đã cập nhật.").then(ps.reload)} /> Bật</label>
                  {p.name !== "internal" && <label style={{ margin: 0 }}><input type="checkbox" style={{ width: "auto" }} checked={p.allow_sensitive} onChange={(ev) => run(() => api(`/providers/${p.name}`, { method: "PATCH", body: { allow_sensitive: ev.target.checked } }), "Đã cập nhật.", ev.target.checked ? `Cho phép gửi dữ liệu nhạy cảm tới ${p.name}?` : undefined).then(ps.reload)} /> Được nhận dữ liệu nhạy cảm</label>}
                  {p.name !== "internal" && <button className="btn" disabled={busy || !Object.keys(e).length} onClick={() => run(() => api(`/providers/${p.name}`, { method: "PATCH", body: e }), "Đã lưu cấu hình.").then(() => { setEdit({ ...edit, [p.name]: {} }); ps.reload(); })}>Lưu cấu hình</button>}
                </>}
                {canEdit(role) && <button className="btn ghost" disabled={busy} onClick={() => run(() => api(`/providers/${p.name}/check`, { method: "POST" }), "Đã kiểm tra.").then(ps.reload)}>Kiểm tra kết nối</button>}
              </p>
            </div>
          );
        })}
      </Async>
      <div className="card">
        <b>Xem trước định tuyến</b>
        <Field label="Phòng ban"><select value={dept} onChange={(e) => setDept(e.target.value)}>{deps.data?.map((d) => <option key={d.key} value={d.key}>{d.name}</option>)}</select></Field>
        <Async loading={prev.loading} error={prev.error}>
          {prev.data && <p>{prev.data.chain.map((c: any) => `${c.provider}/${c.model}`).join("  →  ")}<br /><span className="muted">{prev.data.reason}</span></p>}
        </Async>
      </div>
    </>
  );
}

// ---------------- Approvals ----------------
export function Approvals({ role }: Role) {
  const [st, setSt] = useState("pending");
  const l = useLoad<any[]>(`/approvals?status=${st}`);
  const { run, busy, banner } = useAction();
  return (
    <>
      <h2>Approval Center</h2>{banner}
      <div className="card">
        <Field label="Lọc"><select value={st} onChange={(e) => setSt(e.target.value)}>
          <option value="pending">Đang chờ</option><option value="approved">Đã duyệt</option><option value="rejected">Từ chối</option><option value="">Tất cả</option></select></Field>
        <Async loading={l.loading} error={l.error}>
          {l.data?.length ? (
            <div className="tablewrap"><table><thead><tr><th>ID</th><th>Loại</th><th>Nội dung</th><th>Trạng thái</th><th>Yêu cầu lúc</th><th></th></tr></thead>
              <tbody>{l.data.map((a) => (
                <tr key={a.id}><td>{a.id}</td><td>{a.kind}</td><td>{a.title}<div className="muted">{a.detail}</div></td><td><Badge v={a.status} /></td><td>{utc(a.requested_at)}</td>
                  <td className="row tight">{a.status === "pending" && role === "owner" && <>
                    <button className="btn" disabled={busy} onClick={() => run(() => api(`/approvals/${a.id}/decision`, { method: "POST", body: { approve: true } }), "Đã duyệt.", `Duyệt: ${a.title}?`).then(l.reload)}>Duyệt</button>
                    <button className="btn danger" disabled={busy} onClick={() => run(() => api(`/approvals/${a.id}/decision`, { method: "POST", body: { approve: false } }), "Đã từ chối.", `Từ chối: ${a.title}?`).then(l.reload)}>Từ chối</button></>}</td></tr>))}</tbody></table></div>
          ) : <Empty text="Không có yêu cầu phê duyệt nào." />}
        </Async>
      </div>
    </>
  );
}

// ---------------- Budgets ----------------
export function Budgets({ role }: Role) {
  const b = useLoad<any[]>("/budgets");
  const u = useLoad<any[]>("/usage?limit=30");
  const [f, setF] = useState({ scope: "studio", scope_key: "", period: "monthly", limit_usd: "" });
  const { run, busy, banner } = useAction();
  return (
    <>
      <h2>Ngân sách & Chi phí</h2>{banner}
      <div className="msg">Chi phí chỉ được tính khi bạn đã cấu hình giá provider. Lần gọi chưa có giá hiển thị “chưa biết” — không bịa số. Khi có ngân sách mà provider ngoài chưa có giá, hệ thống chặn gọi API.</div>
      {role === "owner" && (
        <form className="card" onSubmit={async (e) => {
          e.preventDefault();
          if (await run(() => api("/budgets", { method: "POST", body: { ...f, limit_usd: Number(f.limit_usd) } }), "Đã tạo ngân sách.")) b.reload();
        }}>
          <b>Thêm ngân sách</b>
          <div className="row">
            <Field label="Phạm vi"><select value={f.scope} onChange={(e) => setF({ ...f, scope: e.target.value })}>
              {["studio", "project", "department", "provider", "model", "task"].map((s) => <option key={s}>{s}</option>)}</select></Field>
            <Field label="Khóa (ID dự án/task, key phòng ban, tên provider/model)"><input value={f.scope_key} disabled={f.scope === "studio"} onChange={(e) => setF({ ...f, scope_key: e.target.value })} /></Field>
            <Field label="Kỳ"><select value={f.period} onChange={(e) => setF({ ...f, period: e.target.value })}><option value="daily">Ngày</option><option value="monthly">Tháng</option><option value="total">Tổng</option></select></Field>
            <Field label="Hạn mức (USD)"><input type="number" step="any" min="0" value={f.limit_usd} onChange={(e) => setF({ ...f, limit_usd: e.target.value })} required /></Field>
          </div>
          <p><button className="btn" disabled={busy}>Thêm</button></p>
        </form>
      )}
      <div className="card">
        <b>Ngân sách hiện có</b>
        <Async loading={b.loading} error={b.error}>
          {b.data?.length ? (
            <div className="tablewrap"><table><thead><tr><th>Phạm vi</th><th>Kỳ</th><th>Hạn mức</th><th>Đã dùng</th><th>%</th><th></th></tr></thead>
              <tbody>{b.data.map((x) => (
                <tr key={x.id}><td>{x.scope} {x.scope_key}</td><td>{x.period}</td><td>${x.limit_usd}</td><td>${x.spent_usd.toFixed(4)}</td>
                  <td style={{ color: x.ratio >= 1 ? "var(--bad)" : x.ratio >= x.warn_ratio ? "var(--warn)" : undefined }}>{(x.ratio * 100).toFixed(1)}%</td>
                  <td>{role === "owner" && <button className="btn danger" onClick={() => run(() => api(`/budgets/${x.id}`, { method: "DELETE" }), "Đã xóa ngân sách.", "Xóa ngân sách này?").then(b.reload)}>Xóa</button>}</td></tr>))}</tbody></table></div>
          ) : <Empty text="Chưa đặt ngân sách nào. Nên đặt ngân sách studio trước khi dùng provider thật." />}
        </Async>
      </div>
      <div className="card">
        <b>Lượt dùng gần đây</b>
        <Async loading={u.loading} error={u.error}>
          {u.data?.length ? (
            <div className="tablewrap"><table><thead><tr><th>Thời gian</th><th>Task</th><th>Provider/model</th><th>Token vào/ra</th><th>Chi phí</th></tr></thead>
              <tbody>{u.data.map((x) => (
                <tr key={x.id}><td>{utc(x.created_at)}</td><td>{x.task_id}</td><td>{x.provider}/{x.model}</td><td>{x.input_tokens ?? "—"} / {x.output_tokens ?? "—"}</td><td>{usd(x.cost_usd)}</td></tr>))}</tbody></table></div>
          ) : <Empty text="Chưa có lượt dùng nào." />}
        </Async>
      </div>
    </>
  );
}

// ---------------- Logs ----------------
export function Logs({ role }: Role) {
  const [offset, setOffset] = useState(0);
  const [action, setAction] = useState("");
  const l = useLoad<{ items: any[]; total: number }>(role === "viewer" ? null : `/audit?limit=25&offset=${offset}&action=${encodeURIComponent(action)}`);
  if (role === "viewer") return <><h2>Activity Logs</h2><div className="msg err">Cần quyền manager trở lên.</div></>;
  return (
    <>
      <h2>Activity Logs</h2>
      <div className="card">
        <Field label="Lọc theo hành động (chính xác, vd: task_created)"><input value={action} onChange={(e) => { setAction(e.target.value); setOffset(0); }} /></Field>
        <Async loading={l.loading} error={l.error}>
          {l.data?.items.length ? (
            <div className="tablewrap"><table><thead><tr><th>Thời gian</th><th>Người dùng</th><th>Hành động</th><th>Đối tượng</th><th>Chi tiết</th></tr></thead>
              <tbody>{l.data.items.map((x) => (<tr key={x.id}><td>{utc(x.created_at)}</td><td>{x.actor}</td><td>{x.action}</td><td>{x.entity} {x.entity_id}</td><td className="muted">{x.detail}</td></tr>))}</tbody></table></div>
          ) : <Empty text="Chưa có log." />}
          {l.data && <Pager total={l.data.total} offset={offset} limit={25} onChange={setOffset} />}
        </Async>
      </div>
    </>
  );
}

// ---------------- Settings ----------------
export function Settings({ role }: Role) {
  const st = useLoad<any>("/system/state");
  const users = useLoad<any[]>(role === "owner" ? "/users" : null);
  const { run, busy, banner } = useAction();
  const [nu, setNu] = useState({ username: "", password: "", role: "viewer" });
  const [thr, setThr] = useState("");
  const backups = useLoad<any[]>(role === "owner" ? "/system/backups" : null);
  return (
    <>
      <h2>Cài đặt & Bảo mật</h2>{banner}
      <Async loading={st.loading} error={st.error}>
        {st.data && (
          <div className="card">
            <b>Emergency Stop</b>
            <p className="muted">Bật để chặn mọi nhiệm vụ mới và hủy các nhiệm vụ đang chạy do hệ thống quản lý.</p>
            {role === "owner" ? (
              <button className={`btn ${st.data.emergency_stop ? "" : "danger"}`} disabled={busy}
                onClick={() => run(() => api("/system/emergency-stop", { method: "POST", body: { active: !st.data.emergency_stop } }), st.data.emergency_stop ? "Đã tắt Emergency Stop." : "Đã bật Emergency Stop.", st.data.emergency_stop ? "Tắt Emergency Stop?" : "BẬT Emergency Stop? Các nhiệm vụ đang chạy sẽ bị hủy.").then(() => { st.reload(); setTimeout(() => location.reload(), 300); })}>
                {st.data.emergency_stop ? "Tắt Emergency Stop" : "⛔ Bật Emergency Stop"}</button>
            ) : <Badge v={st.data.emergency_stop ? "ĐANG BẬT" : "Tắt"} />}
            <hr style={{ borderColor: "var(--line)" }} />
            <b>Chính sách</b>
            <p><label style={{ margin: 0 }}><input type="checkbox" style={{ width: "auto" }} disabled={role !== "owner"} checked={st.data.fallback_enabled}
              onChange={(e) => run(() => api("/system/settings", { method: "PATCH", body: { fallback_enabled: e.target.checked } }), "Đã cập nhật.").then(st.reload)} /> Cho phép tự chuyển sang provider khác khi provider chính lỗi</label></p>
            <p><label style={{ margin: 0 }}><input type="checkbox" style={{ width: "auto" }} disabled={role !== "owner"} checked={st.data.prefer_cli}
              onChange={(e) => run(() => api("/system/settings", { method: "PATCH", body: { prefer_cli: e.target.checked } }), "Đã cập nhật.").then(st.reload)} /> Ưu tiên dùng Claude Code / Codex đã đăng nhập trên máy (gói thuê bao) trước API khi cùng nhà cung cấp</label></p>
            <div className="row tight">
              <Field label={`Ngưỡng chi phí ước tính cần phê duyệt (USD) — hiện: ${st.data.approval_cost_threshold_usd}`}><input type="number" step="any" min="0" value={thr} disabled={role !== "owner"} onChange={(e) => setThr(e.target.value)} /></Field>
              {role === "owner" && <button className="btn" disabled={busy || thr === ""} onClick={() => run(() => api("/system/settings", { method: "PATCH", body: { approval_cost_threshold_usd: Number(thr) } }), "Đã lưu ngưỡng.").then(() => { setThr(""); st.reload(); })}>Lưu</button>}
            </div>
          </div>
        )}
      </Async>
      {role === "owner" && (
        <div className="card">
          <b>Sao lưu database</b>
          <p className="muted">Tự động sao lưu khi khởi động (tối đa 1 lần/24 giờ) và trước mỗi lần nâng cấp schema; giữ 14 bản mới nhất trong thư mục <code>data\backups</code>. Khôi phục: tắt ứng dụng, chép đè file <code>data\mrk_studio.db</code> bằng một bản sao lưu.</p>
          <button className="btn" disabled={busy} onClick={() => run(() => api("/system/backups", { method: "POST" }), "Đã tạo bản sao lưu.").then(backups.reload)}>Sao lưu ngay</button>
          <Async loading={backups.loading} error={backups.error}>
            {backups.data?.length ? (
              <div className="tablewrap"><table><thead><tr><th>Tệp</th><th>Thời gian</th><th>Dung lượng</th></tr></thead>
                <tbody>{backups.data.map((b) => <tr key={b.name}><td>{b.name}</td><td>{b.created}</td><td>{Math.round(b.size / 1024)} KB</td></tr>)}</tbody></table></div>
            ) : <Empty text="Chưa có bản sao lưu." />}
          </Async>
        </div>
      )}
      {role === "owner" && (
        <div className="card">
          <b>Người dùng</b>
          <Async loading={users.loading} error={users.error}>
            <div className="tablewrap"><table><thead><tr><th>ID</th><th>Tên</th><th>Quyền</th></tr></thead>
              <tbody>{users.data?.map((u) => <tr key={u.id}><td>{u.id}</td><td>{u.username}</td><td>{u.role}</td></tr>)}</tbody></table></div>
          </Async>
          <form onSubmit={async (e) => { e.preventDefault(); if (await run(() => api("/users", { method: "POST", body: nu }), "Đã tạo người dùng.")) { setNu({ username: "", password: "", role: "viewer" }); users.reload(); } }}>
            <div className="row">
              <Field label="Tên đăng nhập"><input value={nu.username} onChange={(e) => setNu({ ...nu, username: e.target.value })} required minLength={3} /></Field>
              <Field label="Mật khẩu (≥ 8 ký tự)"><input type="password" value={nu.password} onChange={(e) => setNu({ ...nu, password: e.target.value })} required minLength={8} /></Field>
              <Field label="Quyền"><select value={nu.role} onChange={(e) => setNu({ ...nu, role: e.target.value })}><option value="viewer">viewer (chỉ xem)</option><option value="manager">manager</option><option value="owner">owner</option></select></Field>
            </div>
            <p><button className="btn" disabled={busy}>Tạo người dùng</button></p>
          </form>
        </div>
      )}
    </>
  );
}

// ---------------- Pipeline ----------------
export function Pipeline({ role }: Role) {
  const projects = useLoad<{ items: any[] }>("/projects?limit=100");
  const [pid, setPid] = useState("");
  const [brief, setBrief] = useState("");
  const [tick, setTick] = useState(0);
  const steps = useLoad<any[]>(pid ? `/projects/${pid}/pipeline` : null, [tick]);
  const { run, busy, banner } = useAction();
  const [report, setReport] = useState<any[] | null>(null);
  const refresh = () => setTick((t) => t + 1);
  const byId = Object.fromEntries((steps.data || []).map((t) => [t.id, t]));
  return (
    <>
      <h2>Pipeline sản xuất game</h2>{banner}
      <div className="msg">Chuỗi 12 bước liên phòng ban (Research → Concept → GDD → … → Phát hành). Kết quả bước trước được đưa vào bước sau. Các bước đánh dấu 🔒 cần chủ studio phê duyệt trong Approval Center trước khi chạy. Không bước nào tự phát hành hay chi tiền.</div>
      <div className="card">
        <Field label="Dự án">
          <select value={pid} onChange={(e) => { setPid(e.target.value); setReport(null); }}>
            <option value="">— chọn dự án —</option>{projects.data?.items.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </Field>
      </div>
      {pid && (
        <Async loading={steps.loading} error={steps.error}>
          {steps.data && steps.data.length === 0 ? (
            canEdit(role) ? (
              <form className="card" onSubmit={async (e) => { e.preventDefault(); if (await run(() => api(`/projects/${pid}/pipeline`, { method: "POST", body: { brief } }), "Đã khởi tạo pipeline.")) refresh(); }}>
                <b>Dự án chưa có pipeline</b>
                <Field label="Yêu cầu / định hướng của chủ studio (tùy chọn, được gửi cho mọi bước)"><textarea value={brief} onChange={(e) => setBrief(e.target.value)} /></Field>
                <p><button className="btn" disabled={busy}>Khởi tạo pipeline 12 bước</button></p>
              </form>
            ) : <Empty text="Dự án chưa có pipeline." />
          ) : (
            <div className="card">
              <div className="row tight">
                {canEdit(role) && <button className="btn" disabled={busy} onClick={async () => {
                  await run(async () => setReport(await api(`/projects/${pid}/pipeline/run-ready`, { method: "POST" })), "Đã gửi lệnh chạy các bước sẵn sàng.", "Chạy các bước đã đủ điều kiện? Việc này có thể gọi AI thật và phát sinh chi phí (trong giới hạn ngân sách).");
                  refresh(); setTimeout(refresh, 2500);
                }}>▶ Chạy các bước sẵn sàng</button>}
                <button className="btn ghost" onClick={refresh}>Làm mới</button>
              </div>
              {report && report.length > 0 && (
                <div className="msg">{report.map((r) => <div key={r.task_id}>{r.title}: {r.outcome === "started" ? "đã bắt đầu" : r.reason}</div>)}</div>
              )}
              <div className="tablewrap"><table>
                <thead><tr><th>Bước</th><th>Phòng ban</th><th>Phụ thuộc</th><th>Trạng thái</th><th>Chi phí</th><th></th></tr></thead>
                <tbody>{steps.data?.map((t) => (
                  <tr key={t.id}><td>{t.requires_approval ? "🔒 " : ""}{t.title.replace("[Pipeline] ", "")}{t.error && <div className="muted" style={{ color: "var(--bad)" }}>{t.error}</div>}</td>
                    <td>{t.department_key}</td>
                    <td className="muted">{t.depends_on.map((d: number) => byId[d]?.title.replace("[Pipeline] ", "").split(".")[0]).join(", ") || "—"}</td>
                    <td><Badge v={t.status} /></td><td>{usd(t.actual_cost)}</td>
                    <td>{t.result && <details><summary>Kết quả ({t.result_source})</summary><pre className="out">{t.result}</pre></details>}</td></tr>
                ))}</tbody></table></div>
            </div>
          )}
        </Async>
      )}
    </>
  );
}

import { useState } from "react";
import { api, useLoad, utc } from "./api";
import { Async, Badge, Empty, Field, useAction } from "./ui";

function Diff({ text }: { text: string }) {
  return (
    <pre className="out diff">
      {text.split("\n").map((l, i) => (
        <span key={i} className={l.startsWith("+") && !l.startsWith("+++") ? "dadd" : l.startsWith("-") && !l.startsWith("---") ? "ddel" : l.startsWith("@@") ? "dhunk" : ""}>{l + "\n"}</span>
      ))}
    </pre>
  );
}

/** Sửa file trong thư mục dự án trên máy: AI/bạn đề xuất → xem diff → chủ studio Áp dụng (có sao lưu + Hoàn tác). */
export function ChangesPanel({ project, role, onChanged }: { project: any; role: string; onChanged: () => void }) {
  const [tick, setTick] = useState(0);
  const isFolder = project.source_type === "folder";
  const list = useLoad<{ allow_write: boolean; items: any[] }>(isFolder ? `/projects/${project.id}/changes` : null, [tick, project.allow_write]);
  const [path, setPath] = useState(""); const [content, setContent] = useState(""); const [loaded, setLoaded] = useState("");
  const { run, busy, banner } = useAction();
  const owner = role === "owner"; const manager = role === "owner" || role === "manager";
  const refresh = () => { setTick((x) => x + 1); onChanged(); };
  if (!isFolder) {
    return <div className="card"><b>Sửa file trên máy</b><p className="muted">Chỉ dùng được với dự án đã liên kết <b>thư mục trên máy</b> (Mã nguồn → “Từ thư mục trên máy tính”). Dự án từ GitHub/.zip chỉ xem và nhận đề xuất, không ghi ngược lại.</p></div>;
  }
  const pending = list.data?.items.filter((c) => c.status === "pending") ?? [];
  const done = list.data?.items.filter((c) => c.status !== "pending") ?? [];
  const allow = !!list.data?.allow_write;

  return (
    <div className="card" style={{ background: "var(--panel2)" }}>
      <b>Sửa file trên máy</b>
      {banner}
      <p className="muted">AI và bạn chỉ <b>đề xuất</b>; không có gì được ghi cho tới khi chủ studio bấm “Áp dụng”. Mỗi lần ghi đều sao lưu bản gốc (thư mục <code>data\file-backups</code>) và có nút “Hoàn tác”. Chỉ sửa tệp văn bản/mã nguồn trong <code>{project.source_ref}</code>; không động tới .env, khóa, tệp chạy (.bat/.exe/.ps1…), và không xóa tệp.</p>
      {owner ? (
        <p><label style={{ margin: 0 }}><input type="checkbox" style={{ width: "auto" }} checked={allow} disabled={busy}
          onChange={(e) => run(() => api(`/projects/${project.id}/write-access`, { method: "PUT", body: { enabled: e.target.checked } }), e.target.checked ? "Đã cho phép ghi vào thư mục dự án." : "Đã tắt quyền ghi.", e.target.checked ? `Cho phép hệ thống GHI vào thư mục ${project.source_ref} (sau mỗi lần bạn bấm Áp dụng)?` : undefined).then(refresh)} />
          {" "}Cho phép ghi vào thư mục gốc của dự án này</label></p>
      ) : <p>Quyền ghi: <Badge v={allow ? "Đã bật" : "Tắt"} /> (chỉ chủ studio bật/tắt và áp dụng)</p>}

      <Async loading={list.loading} error={list.error}>
        <b>Đề xuất chờ duyệt ({pending.length})</b>
        {pending.length === 0 && <Empty text="Chưa có đề xuất. Chạy nhiệm vụ “Phân tích & nâng cấp” rồi bấm “Trích đề xuất sửa file” trong chi tiết nhiệm vụ, hoặc tự soạn bên dưới." />}
        {pending.map((c) => (
          <div key={c.id} className="card">
            <div className="row tight" style={{ alignItems: "center" }}>
              <b>{c.path}</b><Badge v={c.is_new ? "tệp mới" : "sửa"} /><span className="muted">{c.source === "ai" ? `từ AI (nhiệm vụ #${c.task_id})` : `soạn tay: ${c.created_by}`}</span>
              {c.stale && <span className="badge bad">Tệp đã đổi trên máy — không áp dụng được</span>}
            </div>
            {c.error && <div className="msg err">{c.error}</div>}
            {c.diff && <Diff text={c.diff} />}
            <p className="row tight">
              {owner && <button className="btn" disabled={busy || c.stale || !allow} title={!allow ? "Hãy bật quyền ghi ở trên" : ""}
                onClick={() => run(() => api(`/changes/${c.id}/apply`, { method: "POST" }), "Đã ghi vào máy (có sao lưu).", `Ghi thay đổi vào ${c.path} trên máy của bạn?`).then(refresh)}>Áp dụng</button>}
              {manager && <button className="btn ghost" disabled={busy} onClick={() => run(() => api(`/changes/${c.id}/reject`, { method: "POST" }), "Đã từ chối.").then(refresh)}>Từ chối</button>}
            </p>
          </div>
        ))}
        {done.length > 0 && (
          <>
            <b>Đã xử lý</b>
            <div className="tablewrap"><table><thead><tr><th>Tệp</th><th>Trạng thái</th><th>Người xử lý</th><th>Lúc</th><th></th></tr></thead>
              <tbody>{done.map((c) => (
                <tr key={c.id}><td>{c.path}</td><td><Badge v={c.status === "applied" ? "Đã áp dụng" : c.status === "reverted" ? "Đã hoàn tác" : "Đã từ chối"} /></td><td>{c.decided_by}</td><td>{c.decided_at ? utc(c.decided_at) : ""}</td>
                  <td>{owner && c.status === "applied" && <button className="btn ghost" disabled={busy}
                    onClick={() => run(() => api(`/changes/${c.id}/revert`, { method: "POST" }), "Đã hoàn tác về bản gốc.", `Hoàn tác ${c.path} về bản trước khi áp dụng?`).then(refresh)}>Hoàn tác</button>}</td></tr>))}</tbody></table></div>
          </>
        )}
      </Async>

      {manager && (
        <form onSubmit={async (e) => {
          e.preventDefault();
          if (await run(() => api(`/projects/${project.id}/changes`, { method: "POST", body: { path, content } }), "Đã tạo đề xuất. Xem diff ở trên.")) { setContent(""); setLoaded(""); refresh(); }
        }}>
          <b>Tự soạn thay đổi</b>
          <div className="row" style={{ alignItems: "flex-end" }}>
            <Field label="Đường dẫn tệp (tương đối so với thư mục dự án, ví dụ scripts/player.gd)"><input value={path} onChange={(e) => setPath(e.target.value)} required /></Field>
            <button type="button" className="btn ghost" style={{ flex: "0 0 auto" }} disabled={!path || busy}
              onClick={() => run(async () => { const r = await api<any>(`/projects/${project.id}/source-file?path=${encodeURIComponent(path)}`); setContent(r.content); setLoaded(r.exists ? "Đã tải nội dung hiện tại." : "Tệp chưa tồn tại — sẽ tạo mới."); }, "Đã tải.")}>Tải nội dung hiện tại</button>
          </div>
          {loaded && <p className="muted">{loaded}</p>}
          <Field label="Nội dung mới (toàn bộ tệp)"><textarea style={{ minHeight: 160, fontFamily: "monospace" }} value={content} onChange={(e) => setContent(e.target.value)} required /></Field>
          <p><button className="btn" disabled={busy}>Tạo đề xuất</button></p>
        </form>
      )}
    </div>
  );
}

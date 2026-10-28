import { useState } from "react";
import { api, useLoad } from "./api";
import { Field, useAction } from "./ui";

type Result = { files_saved: number; import: string; skipped: string[]; commit?: string; source?: string };

function ResultMsg({ r }: { r: Result | null }) {
  if (!r) return null;
  return (
    <div className="msg okk">
      Đã nhập {r.files_saved} tệp vào <code>imports/{r.import}</code>{r.commit ? <> (commit <code>{r.commit.slice(0, 8)}</code>)</> : null}.
      {r.skipped.length > 0 && <> Bỏ qua {r.skipped.length} (tệp bí mật, symlink…): {r.skipped.slice(0, 4).join(", ")}{r.skipped.length > 4 ? "…" : ""}</>}
    </div>
  );
}

/** Nhập mã nguồn dự án có sẵn từ GitHub hoặc thư mục trên máy (luôn SAO CHÉP vào workspace, không sửa bản gốc). */
export function SourcePanel({ project, role, onDone }: { project: any; role: string; onDone: () => void }) {
  const [tab, setTab] = useState<"github" | "folder">("github");
  const [url, setUrl] = useState(project.source_type === "github" ? project.source_ref : "");
  const [branch, setBranch] = useState(project.source_branch || "");
  const [path, setPath] = useState(project.source_type === "folder" ? project.source_ref : "");
  const [browsePath, setBrowsePath] = useState<string | null>(null);
  const [res, setRes] = useState<Result | null>(null);
  const roots = useLoad<{ paths: string[] }>("/system/import-roots");
  const dirs = useLoad<{ path: string; parent: string; dirs: string[] }>(browsePath !== null ? `/system/browse?path=${encodeURIComponent(browsePath)}` : null);
  const { run, busy, banner } = useAction();
  const linked = project.source_type === "github" || project.source_type === "folder";
  const noRoots = roots.data && roots.data.paths.length === 0 && role !== "owner";
  const norm = (x: string) => x.replace(/\//g, "\\").replace(/\\+$/, "").toLowerCase();
  const outside = role === "owner" && !!path.trim() && !(roots.data?.paths ?? []).some((r) => norm(path) === norm(r) || norm(path).startsWith(norm(r) + "\\"));

  return (
    <div className="card" style={{ background: "var(--panel2)" }}>
      <b>Truy cập dự án có sẵn</b>
      {banner}
      {linked && (
        <div className="msg">
          Đang liên kết với {project.source_type === "github" ? "GitHub" : "thư mục máy"}: <code>{project.source_ref}</code>
          {project.source_branch ? <> (nhánh <code>{project.source_branch}</code>)</> : null}.
          <button className="btn" style={{ marginLeft: 10 }} disabled={busy} onClick={async () => {
            if (await run(async () => setRes(await api<Result>(`/projects/${project.id}/sync`, { method: "POST" })), "Đã cập nhật từ nguồn.")) onDone();
          }}>Cập nhật lại từ nguồn</button>
        </div>
      )}
      <p className="row tight">
        <button className={`btn ${tab === "github" ? "" : "ghost"}`} onClick={() => setTab("github")}>Từ GitHub</button>
        <button className={`btn ${tab === "folder" ? "" : "ghost"}`} onClick={() => setTab("folder")}>Từ thư mục trên máy tính</button>
      </p>

      {tab === "github" && (
        <form onSubmit={async (e) => {
          e.preventDefault();
          if (await run(async () => setRes(await api<Result>(`/projects/${project.id}/import/github`, { method: "POST", body: { url, branch } })), "Đã tải mã nguồn từ GitHub.")) onDone();
        }}>
          <div className="row">
            <Field label="Địa chỉ repo (https://github.com/chủ/tên-repo)"><input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://github.com/ban/game-cua-ban" required /></Field>
            <Field label="Nhánh (để trống = nhánh mặc định)"><input value={branch} onChange={(e) => setBranch(e.target.value)} placeholder="main" /></Field>
          </div>
          <p className="muted">Hệ thống tải một bản sao nông (không có lịch sử, không có submodule) bằng Git trên máy bạn. Repo riêng tư cần máy này đã đăng nhập GitHub (Git Credential Manager); hệ thống không lưu mật khẩu/token. Nếu không tải được, hãy tải .zip từ GitHub rồi upload.</p>
          <button className="btn" disabled={busy || !url}>{busy ? "Đang tải…" : "Tải từ GitHub"}</button>
        </form>
      )}

      {tab === "folder" && (
        <div>
          {noRoots && (
            <div className="msg">
              Chưa có thư mục nào được phép truy cập. {role === "owner" ? "Vào Cài đặt & Bảo mật → “Thư mục dự án trên máy” để thêm thư mục chứa các game của bạn (ví dụ C:\\Games)." : "Nhờ chủ studio thêm trong Cài đặt & Bảo mật."}
            </div>
          )}
          {roots.data && (roots.data.paths.length > 0 || role === "owner") && (
            <>
              {roots.data.paths.length > 0 && <p className="muted">Chỉ truy cập được trong: {roots.data.paths.map((p) => <code key={p} style={{ marginRight: 8 }}>{p}</code>)}</p>}
              <div className="row tight" style={{ alignItems: "flex-end" }}>
                <div style={{ flex: "1 1 320px" }}><Field label="Thư mục dự án trên máy"><input value={path} onChange={(e) => setPath(e.target.value)} placeholder={(roots.data.paths[0] ?? "C:\\Games") + "\\TenGame"} /></Field></div>
                <button className="btn ghost" type="button" onClick={() => setBrowsePath(browsePath === null ? "" : null)}>{browsePath === null ? "Duyệt thư mục…" : "Ẩn danh sách"}</button>
              </div>
              {browsePath !== null && (
                <div className="card" style={{ maxHeight: 220, overflow: "auto" }}>
                  <div className="muted">{dirs.data?.path || "Các thư mục gốc được phép"}</div>
                  {dirs.data?.path && <p><a href="#" onClick={(e) => { e.preventDefault(); setBrowsePath(dirs.data!.parent); }}>⬆ Lên trên</a></p>}
                  {dirs.error && <div className="msg bad">{dirs.error}</div>}
                  {dirs.data?.dirs.map((d) => (
                    <div key={d} style={{ display: "flex", gap: 10, padding: "3px 0" }}>
                      <a href="#" onClick={(e) => { e.preventDefault(); setBrowsePath(d); }}>📁 {d.split(/[\\/]/).filter(Boolean).pop() || d}</a>
                      <a href="#" className="muted" onClick={(e) => { e.preventDefault(); setPath(d); }}>chọn</a>
                    </div>))}
                  {dirs.data && dirs.data.dirs.length === 0 && <span className="muted">Không có thư mục con.</span>}
                </div>
              )}
              <p className="muted">Hệ thống SAO CHÉP mã nguồn vào workspace của dự án (không sửa, không xóa gì trong thư mục gốc của bạn). Bỏ qua .git, node_modules, tệp bí mật (.env, khóa riêng) và symlink.</p>
              <button className="btn" disabled={busy || !path} onClick={async () => {
                if (await run(async () => setRes(await api<Result>(`/projects/${project.id}/import/folder`, { method: "POST", body: { path, grant: outside } })), "Đã nhập từ thư mục.")) { onDone(); roots.reload(); }
              }}>{busy ? "Đang sao chép…" : outside ? "Cấp quyền truy cập thư mục này & nhập" : "Nhập từ thư mục này"}</button>
              {outside && <p className="muted">Thư mục này chưa nằm trong vùng được phép. Bấm nút trên là bạn (chủ studio) cho phép hệ thống truy cập thư mục đó; có thể gỡ lại trong Cài đặt.</p>}
            </>
          )}
        </div>
      )}
      <ResultMsg r={res} />
    </div>
  );
}

/** Cài đặt (chủ studio): các thư mục gốc trên máy mà hệ thống được phép đọc để nhập dự án. */
export function ImportRoots() {
  const roots = useLoad<{ paths: string[] }>("/system/import-roots");
  const [text, setText] = useState<string | null>(null);
  const { run, busy, banner } = useAction();
  const value = text ?? (roots.data?.paths.join("\n") ?? "");
  return (
    <div className="card">
      <b>Thư mục dự án trên máy</b>
      <p className="muted">Để nhập dự án từ thư mục trên máy tính, hãy khai báo thư mục chứa các game của bạn (mỗi dòng một đường dẫn tuyệt đối, ví dụ <code>C:\Games</code>). Hệ thống chỉ đọc được bên trong các thư mục này; không cho phép cả ổ đĩa. Nếu bạn mở ứng dụng ra internet (Tailscale…), chỉ khai báo thư mục thật sự cần.</p>
      {banner}
      <textarea value={value} onChange={(e) => setText(e.target.value)} placeholder={"C:\\Games"} />
      <p><button className="btn" disabled={busy} onClick={async () => {
        if (await run(() => api("/system/import-roots", { method: "PUT", body: { paths: value.split("\n").map((x) => x.trim()).filter(Boolean) } }), "Đã lưu.")) { setText(null); roots.reload(); }
      }}>Lưu</button></p>
    </div>
  );
}

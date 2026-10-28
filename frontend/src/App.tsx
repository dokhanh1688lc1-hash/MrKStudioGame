import { useEffect, useState } from "react";
import { api, getToken, setToken, useLoad } from "./api";
import { Field, useAction } from "./ui";
import { Agents, Approvals, Budgets, Dashboard, Logs, Pipeline, Projects, Providers, Settings, Tasks } from "./pages";

const PAGES: [string, string][] = [
  ["dashboard", "CEO Dashboard"], ["projects", "Dự án"], ["pipeline", "Pipeline sản xuất"], ["tasks", "Task Center"], ["agents", "Phòng ban & Agent"],
  ["providers", "AI Provider & Routing"], ["approvals", "Approval Center"], ["budgets", "Ngân sách & Chi phí"],
  ["logs", "Activity Logs"], ["settings", "Cài đặt & Bảo mật"],
];
const SOON = ["Market Research", "Product & Game Design", "Art Studio", "Audio Studio", "Game Development", "QA & Testing",
  "Monetization", "Marketing", "Data & Analytics", "DevOps & Release", "IP & Compliance", "Telegram & Operations", "Asset Library"];

function Login({ onDone }: { onDone: () => void }) {
  const [u, setU] = useState("owner");
  const [p, setP] = useState("");
  const { run, busy, banner } = useAction();
  return (
    <form className="card login" onSubmit={async (e) => {
      e.preventDefault();
      await run(async () => { const r = await api("/auth/login", { method: "POST", body: { username: u, password: p } }); setToken(r.token); onDone(); }, "OK");
    }}>
      <h2>MrK Studio Game</h2>
      <Field label="Tên đăng nhập"><input value={u} onChange={(e) => setU(e.target.value)} autoFocus /></Field>
      <Field label="Mật khẩu"><input type="password" value={p} onChange={(e) => setP(e.target.value)} /></Field>
      <p><button className="btn" disabled={busy || !p}>Đăng nhập</button></p>
      {banner}
    </form>
  );
}

export default function App() {
  const [authed, setAuthed] = useState(!!getToken());
  const [page, setPage] = useState(() => location.hash.slice(1) || "dashboard");
  useEffect(() => { location.hash = page; }, [page]);
  const me = useLoad<{ username: string; role: string }>(authed ? "/auth/me" : null);
  const state = useLoad<{ emergency_stop: boolean }>(authed ? "/system/state" : null, [page]);

  if (!authed) return <Login onDone={() => setAuthed(true)} />;
  const role = me.data?.role || "viewer";
  const go = (p: string) => setPage(p);
  return (
    <div className="layout">
      <nav className="side">
        <h1>🎮 MrK Studio Game</h1>
        {PAGES.map(([k, label]) => (
          <button key={k} className={`nav ${page === k ? "on" : ""}`} onClick={() => go(k)}>{label}</button>
        ))}
        <div className="soon">Chưa triển khai (Phase 2+)</div>
        <ul className="soonlist">{SOON.map((s) => <li key={s}>{s}</li>)}</ul>
        <p className="muted" style={{ margin: "14px 8px", fontSize: 13 }}>
          {me.data?.username} ({role})<br />
          <a href="#" onClick={(e) => { e.preventDefault(); setToken(""); setAuthed(false); }}>Đăng xuất</a>
        </p>
      </nav>
      <main>
        {state.data?.emergency_stop && <div className="stop">⛔ EMERGENCY STOP đang bật — mọi nhiệm vụ mới bị chặn. Tắt trong “Cài đặt & Bảo mật”.</div>}
        {page === "dashboard" && <Dashboard go={go} />}
        {page === "projects" && <Projects role={role} />}
        {page === "pipeline" && <Pipeline role={role} />}
        {page === "tasks" && <Tasks role={role} />}
        {page === "agents" && <Agents role={role} />}
        {page === "providers" && <Providers role={role} />}
        {page === "approvals" && <Approvals role={role} />}
        {page === "budgets" && <Budgets role={role} />}
        {page === "logs" && <Logs role={role} />}
        {page === "settings" && <Settings role={role} />}
      </main>
    </div>
  );
}

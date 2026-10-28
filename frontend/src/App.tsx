import { useEffect, useRef, useState } from "react";
import { api, getToken, setToken, useLoad } from "./api";
import { Field, useAction } from "./ui";
import { Assets } from "./Assets";
import { Center } from "./Center";
import { CeoInbox } from "./Ceo";
import { Lessons } from "./Lessons";
import { Office } from "./Office";
import { Agents, Approvals, Budgets, Dashboard, Logs, Pipeline, Projects, Providers, Settings, Tasks } from "./pages";

const PAGES: [string, string][] = [
  ["center", "Trung tâm CEO"], ["office", "Văn phòng studio"], ["ceo", "Hộp thư CEO"], ["dashboard", "CEO Dashboard"], ["projects", "Dự án"], ["pipeline", "Pipeline sản xuất"], ["tasks", "Task Center"], ["assets", "Thư viện tài sản"], ["lessons", "Sổ bài học"], ["agents", "Phòng ban & Agent"],
  ["providers", "AI Provider & Routing"], ["approvals", "Approval Center"], ["budgets", "Giới hạn lượt chạy"],
  ["logs", "Activity Logs"], ["settings", "Cài đặt & Bảo mật"],
];
const SOON = ["Telegram"];

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
  const [page, setPage] = useState(() => location.hash.slice(1) || "center");
  useEffect(() => { location.hash = page; }, [page]);
  useEffect(() => { const h = () => { const v = location.hash.slice(1); if (v) setPage(v); }; window.addEventListener("hashchange", h); return () => window.removeEventListener("hashchange", h); }, []);
  const me = useLoad<{ username: string; role: string }>(authed ? "/auth/me" : null);
  const [beat, setBeat] = useState(0);
  useEffect(() => { const t = setInterval(() => setBeat((x) => x + 1), 10000); return () => clearInterval(t); }, []);
  const ceoBox = useLoad<{ pending: number }>(authed ? "/ceo/inbox?limit=1" : null, [page, beat]);
  const lessonBox = useLoad<{ counts: { suggested: number } }>(authed ? "/lessons?limit=0" : null, [page, beat]);
  const att = useLoad<any>(authed ? "/ceo/attention" : null, [page, beat]);
  const attPrev = useRef<Record<string, number> | null>(null);
  useEffect(() => {   // tiêu đề tab + thông báo trình duyệt khi có việc mới / tăng thêm
    const d = att.data; if (!d) return;
    const n = d.counts.urgent + d.counts.warn;
    document.title = (n ? `(${n}) ` : "") + "MrK Studio Game";
    const cur: Record<string, number> = {}; d.items.forEach((i: any) => { cur[i.key] = i.count; });
    if (attPrev.current && typeof Notification !== "undefined" && Notification.permission === "granted") {
      d.items.filter((i: any) => i.severity !== "info" && i.count > (attPrev.current![i.key] ?? 0)).slice(0, 3)
        .forEach((i: any) => { try { new Notification("MrK Studio Game", { body: i.title, tag: i.key }); } catch { /* bỏ qua */ } });
    }
    attPrev.current = cur;
  }, [att.data]);
  const state = useLoad<{ emergency_stop: boolean }>(authed ? "/system/state" : null, [page]);

  if (!authed) return <Login onDone={() => setAuthed(true)} />;
  const role = me.data?.role || "viewer";
  const go = (p: string) => setPage(p);
  return (
    <div className="layout">
      <nav className="side">
        <h1>🎮 MrK Studio Game</h1>
        {PAGES.map(([k, label]) => (
          <button key={k} className={`nav ${page === k ? "on" : ""}`} onClick={() => go(k)}>{label}{k === "ceo" && ceoBox.data?.pending ? <span className="navbadge">{ceoBox.data.pending}</span> : null}{k === "center" && att.data && att.data.counts.urgent + att.data.counts.warn > 0 ? <span className={`navbadge ${att.data.counts.urgent ? "" : "warnb"}`}>{att.data.counts.urgent + att.data.counts.warn}</span> : null}{k === "lessons" && lessonBox.data?.counts.suggested ? <span className="navbadge">{lessonBox.data.counts.suggested}</span> : null}</button>
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
        {page !== "center" && att.data?.counts.urgent > 0 && (
          <div className="stop urgentbar">🔴 {att.data.counts.urgent} việc KHẨN cần bạn: {att.data.items.find((i: any) => i.severity === "urgent")?.title}
            {" "}<button className="btn" onClick={() => go("center")}>Mở Trung tâm CEO</button></div>)}
        {page === "center" && <Center role={role} go={go} data={att.data} loading={att.loading} error={att.error} />}
        {page === "assets" && <Assets role={role} go={go} />}
        {page === "lessons" && <Lessons role={role} />}
        {page === "ceo" && <CeoInbox role={role} go={go} />}
        {page === "office" && <Office role={role} go={go} />}
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

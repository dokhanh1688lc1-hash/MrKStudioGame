import { useEffect, useState } from "react";
import { useLoad } from "./api";
import { Badge } from "./ui";

type Dept = {
  key: string; name: string; description: string; family: string; agents: number; running_title: string;
  running: number; waiting: number; queued: number; done: number; failed: number;
};
type Kind = "lobby" | "code" | "design" | "art" | "audio" | "qa" | "generic";
type Poster = "chart" | "coin" | "mega" | "cloud" | "search" | "shield" | "wallet" | "chat";

// Tên phòng (Việt + Anh) và kiểu minh họa cho từng phòng ban
const ROOMS: Record<string, { vi: string; en: string; kind: Kind; poster?: Poster; span: number }> = {
  ceo: { vi: "Sảnh điều hành", en: "CEO Office", kind: "lobby", span: 4 },
  audio: { vi: "Phòng âm thanh & nhạc game", en: "Audio / Sound Design", kind: "audio", span: 4 },
  qa: { vi: "Phòng kiểm thử chất lượng (QA)", en: "QA Testing / Debugging", kind: "qa", span: 4 },
  game_dev: { vi: "Phòng phát triển & lập trình", en: "Game Development / Coding", kind: "code", span: 4 },
  game_design: { vi: "Phòng thiết kế trò chơi", en: "Game Design & Level Design", kind: "design", span: 4 },
  art: { vi: "Phòng mỹ thuật & đồ họa", en: "Concept Art / Assets", kind: "art", span: 4 },
  market_research: { vi: "Phòng nghiên cứu thị trường", en: "Market Research", kind: "generic", poster: "search", span: 3 },
  monetization: { vi: "Phòng kinh tế & doanh thu", en: "Monetization & Economy", kind: "generic", poster: "coin", span: 3 },
  marketing: { vi: "Phòng marketing", en: "Marketing Studio", kind: "generic", poster: "mega", span: 3 },
  analytics: { vi: "Phòng dữ liệu & phân tích", en: "Data & Analytics", kind: "generic", poster: "chart", span: 3 },
  devops: { vi: "Phòng build & phát hành", en: "DevOps & Release", kind: "generic", poster: "cloud", span: 3 },
  finance: { vi: "Phòng tài chính & tài nguyên", en: "Finance & Resources", kind: "generic", poster: "wallet", span: 3 },
  compliance: { vi: "Phòng bản quyền & pháp lý", en: "IP, Legal & Compliance", kind: "generic", poster: "shield", span: 3 },
  operations: { vi: "Phòng vận hành & thông báo", en: "Operations", kind: "generic", poster: "chat", span: 3 },
};

const SKIN = ["#f1c7a0", "#c98d62", "#8d5a3b", "#e8b48a", "#6e4630"];
const HAIR = ["#2b1d14", "#5a3a22", "#161616", "#b5651d", "#7a2e2e", "#d9b44a"];
const SHIRT = ["#4f7cff", "#e5586b", "#34b27b", "#f0a030", "#8c63e0", "#2fb5c8"];

function state(d: Dept): "run" | "wait" | "idle" { return d.running > 0 ? "run" : d.waiting > 0 ? "wait" : "idle"; }

function Person({ x, y, i, active, vr = false }: { x: number; y: number; i: number; active: boolean; vr?: boolean }) {
  const skin = SKIN[i % SKIN.length], hair = HAIR[(i * 2 + 1) % HAIR.length], shirt = SHIRT[(i * 5 + 2) % SHIRT.length];
  return (
    <g transform={`translate(${x} ${y})`} className={active ? "ofc-typing" : ""}>
      <rect x="-9" y="2" width="18" height="17" rx="6" fill={shirt} />
      <circle cx="0" cy="-7" r="7" fill={skin} />
      <path d="M-7.5 -8 q0 -9 7.5 -9 q7.5 0 7.5 9 q-4 -4 -7.5 -4 q-3.5 0 -7.5 4z" fill={hair} />
      {vr && <rect x="-8" y="-9" width="16" height="6" rx="2" fill="#222" />}
      <rect x="-9" y="16" width="18" height="3" rx="1.5" fill="rgba(0,0,0,.18)" />
    </g>
  );
}

function Monitor({ x, y, w = 30, h = 20, glow, tone, lines = true }: { x: number; y: number; w?: number; h?: number; glow: string; tone: string; lines?: boolean }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect width={w} height={h} rx="2" fill="#1b2233" />
      <rect x="2" y="2" width={w - 4} height={h - 4} rx="1" fill={glow} className={tone === "run" ? "ofc-pulse" : ""} opacity={tone === "idle" ? 0.55 : 0.95} />
      {lines && [0, 1, 2].map((k) => <rect key={k} x="4" y={5 + k * 4} width={8 + ((k * 7) % 12)} height="1.6" fill="rgba(255,255,255,.6)" />)}
      <rect x={w / 2 - 2} y={h} width="4" height="4" fill="#1b2233" />
      <rect x={w / 2 - 7} y={h + 3} width="14" height="2" rx="1" fill="#1b2233" />
    </g>
  );
}

function Desk({ x, y, i, tone, active, w = 54, vr = false }: { x: number; y: number; i: number; tone: string; active: boolean; w?: number; vr?: boolean }) {
  const glow = tone === "run" ? "#2fd08a" : tone === "wait" ? "#f5a524" : "#5b86d8";
  return (
    <g>
      <Person x={x + w / 2} y={y - 4} i={i} active={active} vr={vr} />
      <rect x={x} y={y + 14} width={w} height="9" rx="2" fill="var(--ofc-desk)" />
      <rect x={x + 3} y={y + 22} width="3" height="9" fill="var(--ofc-desk2)" />
      <rect x={x + w - 6} y={y + 22} width="3" height="9" fill="var(--ofc-desk2)" />
      <Monitor x={x + w / 2 - 15} y={y - 8} glow={glow} tone={tone} />
    </g>
  );
}

function Plant({ x, y }: { x: number; y: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <path d="M0 0 q-10 -10 -6 -22 q8 6 6 22z M0 0 q10 -12 5 -26 q-9 8 -5 26z M0 0 q-2 -14 2 -24 q4 10 -2 24z" fill="#3a9b5c" />
      <rect x="-6" y="0" width="12" height="9" rx="2" fill="#b0623c" />
    </g>
  );
}

function PosterIcon({ kind, x, y }: { kind: Poster; x: number; y: number }) {
  const c = "#fff";
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect width="46" height="34" rx="3" fill="#2b3a67" />
      {kind === "chart" && <g fill="#6fc3ff">{[0, 1, 2, 3].map((k) => <rect key={k} x={7 + k * 9} y={26 - (6 + k * 5)} width="6" height={6 + k * 5} />)}</g>}
      {kind === "coin" && <><circle cx="23" cy="17" r="10" fill="#f5c542" /><text x="23" y="21" fontSize="11" textAnchor="middle" fill="#7a5a00" fontWeight="700">$</text></>}
      {kind === "mega" && <path d="M10 14 l16 -7 v20 l-16 -7z M26 10 q8 7 0 14" fill="#ff7a8a" stroke="#ff7a8a" strokeWidth="2" />}
      {kind === "cloud" && <path d="M13 24 q-6 0 -6 -6 q0 -5 6 -5 q2 -7 10 -6 q8 0 9 7 q6 0 6 5 q0 5 -6 5z" fill="#8fd0ff" />}
      {kind === "search" && <><circle cx="21" cy="15" r="8" fill="none" stroke={c} strokeWidth="3" /><path d="M27 21 l9 8" stroke={c} strokeWidth="3.5" /></>}
      {kind === "shield" && <path d="M23 5 l12 4 v9 q0 9 -12 13 q-12 -4 -12 -13 v-9z" fill="#6ee0a6" />}
      {kind === "wallet" && <><rect x="8" y="10" width="30" height="19" rx="3" fill="#e7a85a" /><circle cx="32" cy="19" r="2.5" fill="#fff" /></>}
      {kind === "chat" && <><rect x="8" y="6" width="25" height="15" rx="4" fill="#9ad0ff" /><path d="M14 21 l-2 7 l8 -7z" fill="#9ad0ff" /><rect x="22" y="16" width="18" height="11" rx="3" fill="#fff" opacity=".85" /></>}
    </g>
  );
}

function Scene({ kind, poster, tone, n }: { kind: Kind; poster?: Poster; tone: "run" | "wait" | "idle"; n: number }) {
  const act = tone === "run";
  const glow = tone === "run" ? "#2fd08a" : tone === "wait" ? "#f5a524" : "#5b86d8";
  const people = Math.max(2, Math.min(n + 1, 3));
  return (
    <svg viewBox="0 0 300 170" className="ofc-scene" role="img" aria-hidden="true">
      <defs>
        <pattern id="plank" width="30" height="10" patternUnits="userSpaceOnUse"><rect width="30" height="10" fill="var(--ofc-floor)" /><path d="M0 9.5h30M12 0v10" stroke="rgba(0,0,0,.12)" /></pattern>
      </defs>
      <rect width="300" height="72" fill="var(--ofc-wall)" />
      <rect y="72" width="300" height="98" fill="url(#plank)" />
      <rect y="70" width="300" height="4" fill="rgba(0,0,0,.18)" />

      {kind === "code" && <>
        <rect x="14" y="14" width="86" height="48" rx="3" fill="#f7f9fc" stroke="#9aa6c0" />
        {[[28, 30], [52, 24], [76, 34], [52, 46]].map(([cx, cy], k) => <circle key={k} cx={cx} cy={cy} r="5" fill="none" stroke="#4f7cff" strokeWidth="2" />)}
        <path d="M33 29 L47 25 M57 26 L71 33 M52 29 V41 M33 31 L47 45" stroke="#4f7cff" strokeWidth="1.5" />
        <rect x="118" y="18" width="60" height="36" rx="3" fill="#10172a" />
        {[0, 1, 2, 3, 4].map((k) => <rect key={k} x="124" y={24 + k * 6} width={20 + ((k * 13) % 30)} height="2.4" fill={k % 2 ? "#6fc3ff" : "#7be0a8"} />)}
        {[0, 1, 2].map((k) => <Desk key={k} x={18 + k * 92} y={100} i={k} tone={tone} active={act} />)}
        <Desk x={64} y={136} i={4} tone={tone} active={act} w={50} />
      </>}

      {kind === "design" && <>
        <rect x="22" y="10" width="170" height="54" rx="3" fill="#10172a" />
        <rect x="26" y="14" width="162" height="46" fill="#3c6fa8" /><path d="M26 60 l45 -26 l30 16 l35 -22 l52 32z" fill="#2f8d58" /><circle cx="150" cy="26" r="6" fill="#ffd96a" />
        <rect x="210" y="14" width="30" height="46" rx="2" fill="#27304d" /><rect x="246" y="14" width="30" height="46" rx="2" fill="#27304d" />
        {[0, 1].map((k) => <Desk key={k} x={22 + k * 120} y={104} i={k + 1} tone={tone} active={act} vr={k === 0} />)}
        <Desk x={200} y={128} i={5} tone={tone} active={act} w={48} />
      </>}

      {kind === "art" && <>
        <rect x="16" y="12" width="40" height="52" rx="3" fill="#4a2b73" /><circle cx="36" cy="30" r="8" fill="#ff8aa0" /><path d="M24 58 q12 -22 24 0z" fill="#ffd36b" />
        <rect x="62" y="16" width="34" height="46" rx="3" fill="#1d5a6b" /><rect x="70" y="26" width="18" height="26" rx="3" fill="#7be0d4" />
        <rect x="150" y="12" width="124" height="52" rx="3" fill="#10172a" />
        <rect x="154" y="16" width="52" height="44" fill="#26324f" /><circle cx="180" cy="34" r="9" fill="#ff7a8a" /><rect x="170" y="44" width="20" height="14" rx="3" fill="#6fa8ff" />
        {[0, 1, 2].map((k) => <rect key={k} x={214 + k * 18} y={20 + (k % 2) * 6} width="14" height="14" rx="2" fill={["#ffd36b", "#6fa8ff", "#7be0a8"][k]} />)}
        {[0, 1, 2].map((k) => <Desk key={k} x={16 + k * 96} y={104} i={k + 3} tone={tone} active={act} />)}
      </>}

      {kind === "audio" && <>
        <rect x="14" y="10" width="272" height="58" rx="4" fill="rgba(160,210,255,.28)" stroke="rgba(160,210,255,.8)" />
        <rect x="26" y="20" width="26" height="38" rx="4" fill="#232a40" /><circle cx="39" cy="46" r="7" fill="#3a4466" /><circle cx="39" cy="30" r="3" fill="#7a5cff" />
        <rect x="248" y="20" width="26" height="38" rx="4" fill="#232a40" /><circle cx="261" cy="46" r="7" fill="#3a4466" /><circle cx="261" cy="30" r="3" fill="#7a5cff" />
        <rect x="100" y="22" width="100" height="26" rx="3" fill="#2a1f4d" />
        {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((k) => <rect key={k} x={106 + k * 10} y={30 - ((k * 7) % 10)} width="4" height={8 + ((k * 7) % 10)} fill={tone === "run" ? "#2fd08a" : "#8a74ff"} className={tone === "run" ? "ofc-eq" : ""} />)}
        <rect x="70" y="102" width="160" height="14" rx="3" fill="var(--ofc-desk)" />
        {[0, 1, 2, 3, 4, 5, 6, 7].map((k) => <g key={k}><rect x={80 + k * 18} y="104" width="3" height="10" fill="#222" /><rect x={78.5 + k * 18} y={106 + (k * 3) % 5} width="6" height="3" rx="1" fill={k % 2 ? "#ffd36b" : "#6fc3ff"} /></g>)}
        <Person x={150} y={96} i={2} active={act} />
        <path d="M143 87 q7 -9 14 0" fill="none" stroke="#222" strokeWidth="2" />
        <Desk x={30} y={132} i={6} tone={tone} active={act} w={50} />
      </>}

      {kind === "qa" && <>
        <rect x="150" y="10" width="136" height="54" rx="3" fill="#f7f9fc" stroke="#9aa6c0" />
        {[0, 1, 2].map((k) => <g key={k}><rect x="158" y={18 + k * 14} width="10" height="10" rx="2" fill={k === 2 ? "#ff7a8a" : "#7be0a8"} /><rect x="174" y={21 + k * 14} width={60 - k * 8} height="3" fill="#9aa6c0" /></g>)}
        {[0, 1, 2, 3].map((k) => <rect key={k} x={252 + (k % 2) * 14} y={18 + Math.floor(k / 2) * 18} width="10" height="14" rx="2" fill={["#6fc3ff", "#ffd36b", "#7be0a8", "#ff9ab0"][k]} />)}
        <rect x="16" y="14" width="100" height="46" rx="3" fill="#10172a" />
        <rect x="22" y="20" width="40" height="34" fill="#2c3b66" /><path d="M26 50 l10 -12 l8 7 l10 -16" fill="none" stroke="#7be0a8" strokeWidth="2" />
        <circle cx="86" cy="36" r="12" fill="none" stroke="#ff7a8a" strokeWidth="3" /><path d="M78 28 l16 16 M94 28 l-16 16" stroke="#ff7a8a" strokeWidth="2.5" />
        {[0, 1, 2].map((k) => <Desk key={k} x={16 + k * 96} y={104} i={k + 2} tone={tone} active={act} />)}
        <Desk x={60} y={136} i={7} tone={tone} active={act} w={50} />
      </>}

      {kind === "lobby" && <>
        <rect x="100" y="14" width="100" height="34" rx="4" fill="#202a47" /><text x="150" y="36" textAnchor="middle" fontSize="15" fontWeight="800" fill="#fff" letterSpacing="1">MrK STUDIO</text>
        <circle cx="38" cy="30" r="14" fill="#fff" stroke="#9aa6c0" strokeWidth="2" /><path d="M38 30 V21 M38 30 l7 4" stroke="#333" strokeWidth="2" />
        <rect x="222" y="14" width="46" height="34" rx="3" fill="#6b3f8c" /><circle cx="245" cy="31" r="9" fill="#ffd36b" />
        <rect x="40" y="104" width="86" height="26" rx="10" fill="#e58a4a" /><rect x="40" y="96" width="86" height="14" rx="7" fill="#f0a265" />
        <rect x="152" y="112" width="40" height="10" rx="3" fill="var(--ofc-desk)" /><rect x="162" y="106" width="8" height="6" fill="#fff" /><path d="M172 106 q4 -8 8 0z" fill="#ff7a8a" />
        <Plant x={26} y={150} /><Plant x={276} y={150} />
        <Desk x={210} y={110} i={0} tone={tone} active={act} w={64} />
        <Person x={80} y={98} i={3} active={false} />
      </>}

      {kind === "generic" && <>
        <PosterIcon kind={poster ?? "chart"} x={22} y={16} />
        <rect x="86" y="14" width="96" height="42" rx="3" fill="#f7f9fc" stroke="#9aa6c0" />
        {[0, 1, 2].map((k) => <rect key={k} x="94" y={22 + k * 11} width={50 + ((k * 17) % 30)} height="3" fill="#9aa6c0" />)}
        <circle cx="210" cy="32" r="14" fill="#fff" stroke="#9aa6c0" strokeWidth="2" /><path d="M210 32 V24 M210 32 l6 3" stroke="#333" strokeWidth="2" />
        {Array.from({ length: people }).map((_, k) => <Desk key={k} x={18 + k * 92} y={104} i={k + 8} tone={tone} active={act} />)}
        <Plant x={278} y={92} />
      </>}

      <rect x="0" y="0" width="300" height="170" fill="none" />
      <circle cx="286" cy="12" r="4.5" fill={glow} className={act ? "ofc-pulse" : ""} />
    </svg>
  );
}

function Room({ d, selected, multi, checked, onClick }: { d: Dept; selected: boolean; multi: boolean; checked: boolean; onClick: () => void }) {
  const r = ROOMS[d.key] ?? { vi: d.name, en: d.key, kind: "generic" as Kind, span: 3 };
  const st = state(d);
  return (
    <button className={`ofc-room span${r.span} ${st} ${selected ? "sel" : ""}`} onClick={onClick} aria-pressed={multi ? checked : selected}
      title={d.description}>
      <span className="ofc-sign"><b>{r.vi}</b><i>{r.en}</i></span>
      {multi && <span className={`ofc-check ${checked ? "on" : ""}`}>{checked ? "✓" : ""}</span>}
      <Scene kind={r.kind} poster={r.poster} tone={st} n={d.agents} />
      <span className="ofc-foot">
        <span className={`ofc-pill ${st}`}>{st === "run" ? "Đang làm việc" : st === "wait" ? "Chờ duyệt / bị chặn" : "Đang rảnh"}</span>
        <span className="ofc-chips">
          <span title="Đang chạy">▶ {d.running}</span><span title="Chờ duyệt / bị chặn">⏳ {d.waiting}</span>
          <span title="Đã giao, chưa chạy">📋 {d.queued}</span><span title="Hoàn thành">✔ {d.done}</span>
          {d.failed > 0 && <span title="Thất bại" className="bad">✖ {d.failed}</span>}
        </span>
        {d.running_title && <span className="ofc-now">Đang làm: {d.running_title}</span>}
      </span>
    </button>
  );
}

function Detail({ d, go }: { d: Dept; go: (p: string) => void }) {
  const r = ROOMS[d.key];
  const tasks = useLoad<{ items: any[] }>(`/tasks?department=${d.key}&limit=6`, [d.running, d.done, d.queued]);
  const tpls = useLoad<Record<string, any[]>>("/tasks/templates/all");
  const mine = tpls.data?.[d.key] ?? [];
  return (
    <div className="card">
      <div className="row" style={{ alignItems: "center" }}>
        <div><h3 style={{ margin: 0 }}>{r?.vi ?? d.name}</h3><div className="muted">{d.name} · {d.description}</div>
          <div className="muted">Dùng {d.family === "openai" ? "ChatGPT (Codex)" : "Claude (Claude Code)"} · {d.agents} agent đang bật</div></div>
        <div style={{ flex: "0 0 auto" }}>
          <button className="btn" onClick={() => { try { localStorage.setItem("mrk.preDepts", JSON.stringify([d.key])); } catch { /* bỏ qua */ } go("tasks"); }}>Giao việc cho phòng này</button>
        </div>
      </div>
      {mine.length > 0 && (
        <p className="row tight" style={{ alignItems: "center" }}>
          <span className="muted">Giao nhanh bằng mẫu:</span>
          {mine.map((t) => (
            <button key={t.title} className="btn ghost" title={t.objective}
              onClick={() => { try { localStorage.setItem("mrk.preTask", JSON.stringify({ department: d.key, ...t })); } catch { /* bỏ qua */ } go("tasks"); }}>{t.title}</button>))}
        </p>
      )}
      {tasks.data?.items.length ? (
        <div className="tablewrap"><table><thead><tr><th>ID</th><th>Nhiệm vụ</th><th>Trạng thái</th></tr></thead>
          <tbody>{tasks.data.items.map((t) => <tr key={t.id}><td>#{t.id}</td><td>{t.title}</td><td><Badge v={t.status} /></td></tr>)}</tbody></table></div>
      ) : <p className="muted">Phòng này chưa có nhiệm vụ nào.</p>}
    </div>
  );
}

export function Office({ role, go }: { role: string; go: (p: string) => void }) {
  const [tick, setTick] = useState(0);
  const office = useLoad<Dept[]>("/office", [tick]);
  const ceoBox = useLoad<{ pending: number }>("/ceo/inbox?limit=1", [tick]);
  const [sel, setSel] = useState<string>("");
  const [multi, setMulti] = useState(false);
  const [picked, setPicked] = useState<string[]>([]);
  useEffect(() => { const t = setInterval(() => setTick((x) => x + 1), 5000); return () => clearInterval(t); }, []);
  const canEdit = role === "owner" || role === "manager";
  const depts = office.data ?? [];
  const order = Object.keys(ROOMS);
  const sorted = [...depts].sort((a, b) => order.indexOf(a.key) - order.indexOf(b.key));
  const cur = depts.find((d) => d.key === sel);
  const running = depts.reduce((s, d) => s + d.running, 0);
  const waiting = depts.reduce((s, d) => s + d.waiting, 0);

  return (
    <>
      <h2>Văn phòng studio</h2>
      <div className="ofc-bar card">
        <span><b>{depts.length}</b> phòng ban · <b>{running}</b> nhiệm vụ đang chạy · <b>{waiting}</b> đang chờ duyệt/bị chặn</span>
        <span className="muted">Tự cập nhật mỗi 5 giây</span>
        <button className="btn ghost" onClick={() => go("ceo")}>📥 Hộp thư CEO{ceoBox.data?.pending ? ` (${ceoBox.data.pending} chờ quyết định)` : ""}</button>
        {canEdit && (
          <span className="ofc-actions">
            <button className={`btn ${multi ? "" : "ghost"}`} onClick={() => { setMulti(!multi); setPicked([]); }}>
              {multi ? "Thoát chế độ chọn nhiều" : "Chọn nhiều phòng để giao việc"}</button>
            {multi && <>
              <button className="btn ghost" onClick={() => setPicked(depts.map((d) => d.key))}>Chọn tất cả</button>
              <button className="btn" disabled={picked.length === 0} onClick={() => { try { localStorage.setItem("mrk.preDepts", JSON.stringify(picked)); } catch { /* bỏ qua */ } go("tasks"); }}>
                Giao việc cho {picked.length} phòng</button></>}
          </span>
        )}
      </div>
      {office.error && <div className="msg bad">{office.error}</div>}
      <div className="ofc-floor">
        {sorted.map((d) => (
          <Room key={d.key} d={d} selected={sel === d.key} multi={multi} checked={picked.includes(d.key)}
            onClick={() => multi ? setPicked(picked.includes(d.key) ? picked.filter((k) => k !== d.key) : [...picked, d.key]) : setSel(sel === d.key ? "" : d.key)} />
        ))}
      </div>
      {cur && !multi && <Detail d={cur} go={go} />}
      {!cur && !multi && <p className="muted">Bấm vào một phòng để xem nhiệm vụ và giao việc. Đèn xanh = đang làm việc, vàng = chờ duyệt, xám = rảnh.</p>}
    </>
  );
}

import { useEffect, useRef, useState } from "react";
import { useLoad, utc } from "./api";
import { Async, Empty } from "./ui";

const SEV: Record<string, { label: string; icon: string }> = { urgent: { label: "Khẩn", icon: "🔴" }, warn: { label: "Cần xử lý", icon: "🟠" }, info: { label: "Nên xem", icon: "🔵" } };
const SEEN_KEY = "mrk.seen";
const readSeen = (): Record<string, number> => { try { return JSON.parse(localStorage.getItem(SEEN_KEY) || "{}"); } catch { return {}; } };

export function Center({ role, go, data, loading, error }: { role: string; go: (p: string) => void; data: any; loading: boolean; error: string }) {
  const dash = useLoad<any>("/dashboard", [data?.generated_at]);
  const office = useLoad<any[]>("/office", [data?.generated_at]);
  const audit = useLoad<{ items: any[] }>(role === "viewer" ? null : "/audit?limit=10", [data?.generated_at]);
  const seen = useRef<Record<string, number>>(readSeen());     // chụp trạng thái "đã xem" lúc mở trang để gắn nhãn MỚI
  const latest = useRef<any>(null);
  latest.current = data;
  const [perm, setPerm] = useState<string>(typeof Notification === "undefined" ? "unsupported" : Notification.permission);
  useEffect(() => () => {   // rời trang: ghi nhận đã xem
    try { const m: Record<string, number> = {}; (latest.current?.items ?? []).forEach((i: any) => { m[i.key] = i.count; }); localStorage.setItem(SEEN_KEY, JSON.stringify(m)); } catch { /* bỏ qua */ }
  }, []);

  const c = data?.counts ?? { urgent: 0, warn: 0, info: 0 };
  const todo = c.urgent + c.warn;
  const tone = c.urgent ? "bad" : c.warn ? "warn" : "ok";

  return (
    <>
      <h2>Trung tâm CEO</h2>
      <Async loading={loading && !data} error={error}>
        {data && (
          <>
            <div className={`cbanner ${tone}`}>
              <div className="cbig">{todo === 0 ? "✅ Không có việc nào cần bạn xử lý" : `${c.urgent ? "🔴" : "🟠"} ${todo} việc cần bạn xử lý${c.urgent ? ` — ${c.urgent} việc KHẨN` : ""}`}</div>
              <div className="muted">Cập nhật tự động mỗi 10 giây · {utc(data.generated_at)}</div>
            </div>
            <div className="kpis">
              {(["urgent", "warn", "info"] as const).map((k) => <div key={k} className={`kpi ${k}`}><b>{c[k]}</b><span>{SEV[k].icon} {SEV[k].label}</span></div>)}
              <div className="kpi"><b>{dash.data?.runs_today ?? "—"}</b><span>Lượt chạy AI hôm nay</span></div>
              <div className="kpi"><b>{dash.data?.tasks_by_status?.Running ?? 0}</b><span>Đang chạy</span></div>
            </div>
            {perm === "default" && <p><button className="btn ghost" onClick={async () => setPerm(await Notification.requestPermission())}>🔔 Bật thông báo trên trình duyệt khi có việc mới</button></p>}
            {perm === "denied" && <p className="muted">Thông báo trình duyệt đang bị chặn — bật lại trong cài đặt trang web nếu muốn. Số việc vẫn hiện trên tiêu đề tab và thanh bên.</p>}

            {data.items.length === 0 ? <Empty text="Mọi thứ đang ổn. Khi có việc cần bạn (kết quả chờ quyết định, lỗi, hết lượt…), nó sẽ hiện ở đây kèm cách xử lý." /> : (
              <div className="alist">
                {data.items.map((i: any) => (
                  <div key={i.key} className={`acard ${i.severity}`}>
                    <div className="ahead">
                      <b>{SEV[i.severity].icon} {i.title}</b>
                      {(seen.current[i.key] ?? 0) < i.count && <span className="newtag">MỚI</span>}
                      <span style={{ flex: 1 }} />
                      <button className="btn" onClick={() => go(i.page || "ceo")}>{i.action || "Mở"} →</button>
                    </div>
                    {i.detail && <div className="muted">{i.detail}</div>}
                    {i.steps.length > 0 && <div className="asteps"><b>Bạn cần làm:</b><ol>{i.steps.map((st: string, n: number) => <li key={n}>{st}</li>)}</ol></div>}
                    {i.samples.length > 0 && <ul className="asamples">{i.samples.map((sm: any) => <li key={sm.id}><b>#{sm.id}</b> {sm.title} <span className="muted">— {sm.detail}</span></li>)}{i.count > i.samples.length && <li className="muted">… và {i.count - i.samples.length} mục khác</li>}</ul>}
                  </div>
                ))}
              </div>
            )}

            <h3>Sức khỏe các phòng ban</h3>
            <Async loading={office.loading} error={office.error}>
              <div className="dgrid">
                {office.data?.map((d: any) => (
                  <button key={d.key} className={`dcard ${d.failed ? "bad" : d.running ? "run" : ""}`} onClick={() => go("tasks")} title="Mở Task Center">
                    <b>{d.name}</b>
                    <span>{d.running ? `⚙ Đang chạy: ${d.running_title || d.running}` : d.queued ? `⏳ ${d.queued} chờ chạy` : "Rảnh"}</span>
                    <span className="muted">Xong {d.done}{d.failed ? ` · ` : ""}{d.failed ? <b style={{ color: "var(--bad)" }}>Lỗi {d.failed}</b> : null}{d.waiting ? ` · Chờ duyệt ${d.waiting}` : ""}</span>
                  </button>
                ))}
              </div>
            </Async>

            {role !== "viewer" && (
              <>
                <h3>Hoạt động gần đây</h3>
                <Async loading={audit.loading} error={audit.error}>
                  {audit.data?.items.length ? <ul className="timeline">{audit.data.items.map((a) => <li key={a.id}><span className="muted">{utc(a.created_at)}</span> <b>{a.actor}</b> · {a.action}{a.detail ? <span className="muted"> — {a.detail.slice(0, 90)}</span> : null}</li>)}</ul> : <Empty text="Chưa có hoạt động." />}
                </Async>
              </>
            )}
          </>
        )}
      </Async>
    </>
  );
}

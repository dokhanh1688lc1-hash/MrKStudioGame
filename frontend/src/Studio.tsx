import { useState } from "react";
import { api, useLoad } from "./api";
import { Async, Badge, Empty, useAction } from "./ui";

const STATUSES = ["Research", "Concept", "Pre-production", "Prototype", "Production", "QA", "Release Preparation", "Live Operations", "Paused", "Archived"];

export function Studio({ role, go }: { role: string; go: (p: string) => void }) {
  const [tick, setTick] = useState(0);
  const ov = useLoad<{ items: any[] }>("/studio/overview", [tick]);
  const { run, busy, banner } = useAction();
  const manager = role === "owner" || role === "manager";
  const setStatus = (id: number, status: string) => run(() => api(`/projects/${id}`, { method: "PATCH", body: { status } }), status === "Paused" ? "Đã tạm dừng dự án — nhiệm vụ mới sẽ không chạy cho đến khi tiếp tục." : "Đã cập nhật trạng thái dự án.").then(() => setTick((x) => x + 1));
  return (
    <>
      <h2>Studio Manager</h2>{banner}
      <p className="muted">Tổng quan mọi dự án: tiến độ, tài sản, kiểm thử, build và mức sẵn sàng phát hành. Tạm dừng một dự án sẽ chặn chạy nhiệm vụ mới của dự án đó.</p>
      <p className="row tight"><button className="btn" onClick={() => go("projects")}>+ Tạo / quản lý dự án</button><button className="btn ghost" onClick={() => go("tasks")}>Giao nhiệm vụ</button><button className="btn ghost" onClick={() => go("center")}>Trung tâm CEO</button></p>
      <Async loading={ov.loading && !ov.data} error={ov.error}>
        {ov.data?.items.length ? ov.data.items.map((p) => (
          <div key={p.id} className="card">
            <div className="row tight"><b style={{ fontSize: 18 }}>{p.name}</b><Badge v={p.status === "Paused" ? "Blocked" : "ok"} /> <span className="muted">{p.status}{p.genre ? ` · ${p.genre}` : ""}{p.platform ? ` · ${p.platform}` : ""}</span><span style={{ flex: 1 }} />
              {manager && p.status !== "Paused" && p.status !== "Archived" && <button className="btn ghost" disabled={busy} onClick={() => setStatus(p.id, "Paused")}>⏸ Tạm dừng</button>}
              {manager && p.status === "Paused" && <button className="btn" disabled={busy} onClick={() => setStatus(p.id, "Production")}>▶ Tiếp tục (Production)</button>}
              {manager && <select value={p.status} disabled={busy} onChange={(e) => setStatus(p.id, e.target.value)}>{STATUSES.map((s) => <option key={s}>{s}</option>)}</select>}</div>
            <div className="bar big"><i style={{ width: `${p.tasks.pct}%` }} /></div>
            <div className="kpis">
              <div className="kpi"><b>{p.tasks.done}/{p.tasks.total}</b><span>Nhiệm vụ xong ({p.tasks.pct}%){p.tasks.running ? ` · ${p.tasks.running} đang chạy` : ""}{p.tasks.failed ? ` · ${p.tasks.failed} lỗi` : ""}</span></div>
              <div className="kpi"><b>{p.assets.approved}/{p.assets.total}</b><span>Tài sản đã duyệt{p.assets.problems ? ` · ${p.assets.problems} có vấn đề` : ""}</span></div>
              <div className="kpi"><b>{p.tests.passed}/{p.tests.total}</b><span>Test Passed{p.tests.failed ? ` · ${p.tests.failed} lỗi` : ""}</span></div>
              <div className="kpi"><b>{p.builds_ready}</b><span>Build sẵn sàng</span></div>
              <div className="kpi"><b>{p.docs}</b><span>Tài liệu</span></div>
              <div className={`kpi ${p.release.ready ? "" : "warn"}`}><b>{p.release.done}/{p.release.total}</b><span>Checklist phát hành{p.release.ready ? " ✅" : ""}</span></div>
            </div>
          </div>)) : <Empty text="Chưa có dự án. Bấm “Tạo / quản lý dự án”." />}
      </Async>
    </>
  );
}

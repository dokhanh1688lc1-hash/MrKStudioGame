import { useEffect, useState } from "react";
import { api, useLoad } from "./api";
import { Async, Badge, Empty, Field, useAction } from "./ui";
import { AnalyticsPanel, AssetsMini, BuildsPanel, ChecklistPanel, DocsPanel, FinancePanel, Perm, TestsPanel, perm } from "./Panels";

type Spec = { goal: string; outputs: string; rules: string; docs?: string[]; panels: string[] };
/** Nội dung rút từ MASTER PROMPT: mục tiêu, đầu ra và giới hạn bắt buộc của từng phòng ban. */
export const SPECS: Record<string, Spec> = {
  market_research: { goal: "Nghiên cứu xu hướng, đối thủ, người chơi mục tiêu; tìm khoảng trống sản phẩm.", outputs: "Báo cáo, nguồn tham khảo, giả thuyết, đánh giá độ tin cậy, khuyến nghị hành động.",
    rules: "Không bịa số liệu thị trường. Phân biệt dữ liệu đã xác minh, giả thuyết và dự đoán.", docs: ["market_report"], panels: ["docs"] },
  game_design: { goal: "Ý tưởng, GDD, core loop, tiến trình, UX, phạm vi MVP, backlog có tiêu chí nghiệm thu.", outputs: "GDD, tài liệu thiết kế, backlog MVP.",
    rules: "Mọi sản phẩm phải có bản sắc riêng — không sao chép tài sản, giao diện, nhân vật hoặc nội dung độc quyền của game khác.", docs: ["gdd", "design"], panels: ["docs"] },
  art: { goal: "Art Bible, phong cách thống nhất, brief nhân vật/môi trường/UI, quản lý nguồn gốc tài sản đồ họa.", outputs: "Art Bible, brief, prompt, danh mục tài sản.",
    rules: "Chưa có công cụ tạo ảnh thì chỉ tạo brief/prompt. Không tuyên bố đã tạo ảnh khi chưa có tệp thật.", docs: ["art_bible"], panels: ["docs", "assets_image"] },
  audio: { goal: "Audio Bible, danh mục nhạc và SFX, brief/prompt âm thanh, quản lý nguồn và giấy phép.", outputs: "Audio Bible, danh mục âm thanh, brief.",
    rules: "Không dùng nhạc/âm thanh thương mại khi chưa xác minh quyền sử dụng.", docs: ["audio_bible"], panels: ["docs", "assets_audio"] },
  game_dev: { goal: "Dự án Godot 4, scene, script, UI, gameplay, lưu tiến trình, tích hợp tài sản, build.", outputs: "Mã nguồn (đề xuất sửa file chờ bạn duyệt), tài liệu kỹ thuật, hướng dẫn chạy/build.",
    rules: "Mỗi game có workspace riêng; mọi thay đổi file trên máy đều cần chủ studio bấm Áp dụng. Studio âm thanh đang tạm dừng: Dev giữ danh mục/chỗ đặt âm thanh, phòng Pháp lý rà soát nguồn và giấy phép.", docs: ["tech", "audio_bible"], panels: ["docs", "assets_audio", "builds_only"] },
  qa: { goal: "Test case, kiểm thử gameplay/luồng chính/lưu tiến trình, báo cáo lỗi có mức độ, xác nhận sửa lỗi, hồi quy.", outputs: "Test case, kết quả chạy, báo cáo lỗi.",
    rules: "Trạng thái test: Passed, Failed, Blocked, Not Run. Không đánh dấu Passed khi test chưa chạy.", docs: ["qa_report"], panels: ["tests", "docs"] },
  monetization: { goal: "Quảng cáo phù hợp gameplay, vật phẩm/tiền tệ, mô hình miễn phí/trả phí, thử nghiệm A/B, KPI khi có dữ liệu thật.", outputs: "Kế hoạch kiếm tiền, thiết kế kinh tế game, kế hoạch A/B.",
    rules: "Không bịa doanh thu hoặc cam kết lợi nhuận. Tránh thiết kế gây khó chịu hay ép người chơi chi tiền.", docs: ["monetization"], panels: ["docs", "finance"] },
  marketing: { goal: "Định vị, tên game, mô tả cửa hàng, ASO, kế hoạch ra mắt, lịch nội dung.", outputs: "Kế hoạch ra mắt, nội dung cửa hàng, brief ảnh/trailer.",
    rules: "Không tự đăng nội dung công khai hay chạy quảng cáo trả phí khi chưa được cấp quyền và phê duyệt.", docs: ["marketing", "store_listing"], panels: ["docs"] },
  analytics: { goal: "Retention, session, conversion, crash, doanh thu, cohort, so sánh phiên bản, phát hiện bất thường.", outputs: "Báo cáo kèm nguồn dữ liệu, khoảng thời gian, hạn chế.",
    rules: "Không tự suy diễn dữ liệu chưa có. Mọi báo cáo phải ghi nguồn, khoảng thời gian và hạn chế.", panels: ["analytics"] },
  devops: { goal: "Cấu hình môi trường, quy trình build, version, changelog, metadata và checklist cửa hàng.", outputs: "Bản build, changelog, checklist phát hành.",
    rules: "Không tự phát hành công khai, ký thỏa thuận hay đổi thông tin tài khoản khi chưa được chủ studio phê duyệt.", docs: ["release_notes"], panels: ["builds", "checklist", "docs"] },
  finance: { goal: "Ngân sách theo dự án/phòng ban, chi phí dịch vụ, so sánh thực tế với hạn mức, doanh thu và lợi nhuận khi có dữ liệu.", outputs: "Sổ chi phí/doanh thu, tổng hợp lợi nhuận, cảnh báo hạn mức.",
    rules: "Phân biệt chi phí ước tính và thực tế. Doanh thu chỉ tính khi chủ studio xác nhận.", panels: ["finance"] },
  compliance: { goal: "Nguồn gốc tài sản, giấy phép, kiểm tra checklist bản quyền và chính sách nền tảng, đánh dấu tài sản chưa rõ nguồn.", outputs: "Hồ sơ nguồn gốc, checklist bản quyền, cảnh báo.",
    rules: "AI không thể khẳng định chắc chắn không vi phạm bản quyền hay tuân thủ pháp luật — cần người có chuyên môn rà soát trước phát hành.", docs: ["legal"], panels: ["assets_all", "assets_audio", "checklist_legal", "docs"] },
  operations: { goal: "Thông báo tiến độ/lỗi/ngân sách, tra cứu và tạo yêu cầu, tạm dừng/tiếp tục tác vụ, chuyển yêu cầu nhạy cảm sang Approval Center.", outputs: "Thông báo và báo cáo nhanh.",
    rules: "Bắt buộc xác thực Telegram user ID, phân quyền, audit log, bảo vệ bot token.", panels: ["telegram"] },
};
export const DEPT_ORDER = ["market_research", "game_design", "art", "game_dev", "qa", "monetization", "marketing", "analytics", "devops", "finance", "compliance", "operations"];

function useProject() {
  const projects = useLoad<{ items: any[] }>("/projects?limit=100");
  const [pid, setPid] = useState<string>(() => { try { return localStorage.getItem("mrk.proj") || ""; } catch { return ""; } });
  useEffect(() => { try { localStorage.setItem("mrk.proj", pid); } catch { /* bỏ qua */ } }, [pid]);
  useEffect(() => { if (projects.data && !projects.data.items.some((p) => String(p.id) === pid)) setPid(projects.data.items[0] ? String(projects.data.items[0].id) : ""); }, [projects.data]);  // eslint-disable-line
  return { projects, pid, setPid };
}

function QuickAssign({ dkey, pid, p, onDone }: { dkey: string; pid: number; p: Perm; onDone: () => void }) {
  const tpls = useLoad<Record<string, any[]>>("/tasks/templates/all");
  const [f, setF] = useState({ title: "", objective: "", expected_output: "", acceptance_criteria: "", run_now: false });
  const { run, busy, banner } = useAction();
  if (!p.manager) return null;
  const list = tpls.data?.[dkey] ?? [];
  return (
    <form className="card" onSubmit={async (e) => {
      e.preventDefault();
      const { run_now, ...rest } = f;
      if (await run(() => api("/tasks/bulk", { method: "POST", body: { ...rest, project_id: pid, department_keys: [dkey], run_now } }), run_now ? "Đã giao và bắt đầu chạy." : "Đã giao việc cho phòng ban.")) { setF({ ...f, title: "", objective: "" }); onDone(); setTimeout(onDone, 1500); }
    }}>
      <b>Giao việc nhanh cho phòng này</b>{banner}
      {list.length > 0 && <Field label="Dùng mẫu"><select value="" onChange={(e) => { const t = list[Number(e.target.value)]; if (t) setF({ ...f, title: t.title, objective: t.objective, expected_output: t.expected_output, acceptance_criteria: t.acceptance_criteria }); }}>
        <option value="">— chọn mẫu —</option>{list.map((t, i) => <option key={i} value={i}>{t.title}</option>)}</select></Field>}
      <div className="row"><Field label="Tiêu đề *"><input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} required /></Field></div>
      <Field label="Mục tiêu *"><textarea value={f.objective} onChange={(e) => setF({ ...f, objective: e.target.value })} required /></Field>
      <p className="row tight"><label style={{ margin: 0 }}><input type="checkbox" style={{ width: "auto" }} checked={f.run_now} onChange={(e) => setF({ ...f, run_now: e.target.checked })} /> Chạy AI ngay (tính vào giới hạn lượt chạy)</label>
        <button className="btn" disabled={busy}>Giao việc</button></p>
    </form>
  );
}

function TaskRow({ t, pid, docKind, p, refresh }: { t: any; pid: number; docKind?: string; p: Perm; refresh: () => void }) {
  const [open, setOpen] = useState(false);
  const d = useLoad<any>(open ? `/tasks/${t.id}` : null, [open, t.status]);
  const { run, busy, banner } = useAction();
  return (
    <>
      <tr><td>#{t.id}</td><td>{t.title}</td><td><Badge v={t.status} /></td>
        <td className="row tight">
          <button className="btn ghost" onClick={() => setOpen(!open)}>{open ? "Ẩn" : "Xem"}</button>
          {p.manager && ["Pending", "Planned", "Assigned", "Blocked", "Failed"].includes(t.status) && <button className="btn" disabled={busy} onClick={async () => { await run(() => api(`/tasks/${t.id}/run`, { method: "POST" }), "Đã bắt đầu chạy."); refresh(); setTimeout(refresh, 1500); }}>Chạy</button>}
          {p.manager && t.status === "Completed" && docKind && <button className="btn ghost" disabled={busy} onClick={() => run(() => api(`/projects/${pid}/documents/from-task/${t.id}`, { method: "POST", body: { kind: docKind } }), "Đã lưu thành tài liệu (bản nháp) — xem ở mục Tài liệu.").then(refresh)}>Lưu thành tài liệu</button>}
        </td></tr>
      {(open || banner) && <tr><td colSpan={4}>{banner}{open && d.data && (<>
        {d.data.help && <div className="helpbox"><b>⚠ {d.data.help.title}</b><div className="muted">{d.data.error}</div><ol>{d.data.help.steps.map((s: string, i: number) => <li key={i}>{s}</li>)}</ol></div>}
        {d.data.result ? <pre className="out">{d.data.result}</pre> : !d.data.help && <span className="muted">Chưa có kết quả.</span>}</>)}</td></tr>}
    </>
  );
}

export function DeptPage({ dkey, role, go }: { dkey: string; role: string; go: (p: string) => void }) {
  const spec = SPECS[dkey];
  const p = perm(role);
  const depts = useLoad<any[]>("/departments");
  const dept = depts.data?.find((d) => d.key === dkey);
  const { projects, pid, setPid } = useProject();
  const [tick, setTick] = useState(0);
  const refresh = () => setTick((x) => x + 1);
  useEffect(() => { const h = setInterval(refresh, 8000); return () => clearInterval(h); }, []);
  const tasks = useLoad<{ items: any[]; total: number }>(pid ? `/tasks?project_id=${pid}&department=${dkey}&limit=8` : null, [tick, pid]);
  const prog = useLoad<any>(pid ? `/tasks/progress?project_id=${pid}` : null, [tick, pid]);
  const lessons = useLoad<{ items: any[] }>(`/lessons?department=${dkey}&status=active`, [tick]);
  const num = pid ? Number(pid) : 0;
  const mine = prog.data?.departments.find((x: any) => x.key === dkey);
  if (!spec) return <Empty text="Không có trang cho phòng ban này." />;
  const needsProject = !(spec.panels.length === 1 && spec.panels[0] === "finance") && spec.panels[0] !== "telegram";

  return (
    <>
      <h2>{dept?.name ?? dkey}</h2>
      <div className="card">
        <p><b>Mục tiêu:</b> {spec.goal}</p>
        <p><b>Đầu ra:</b> {spec.outputs}</p>
        <p style={{ color: "var(--warn)" }}><b>Giới hạn bắt buộc:</b> {spec.rules}</p>
        {dept && <p className="muted">AI ưu tiên: {dept.preferred_provider === "openai" ? "ChatGPT (Codex)" : "Claude Code"} — đổi ở Phòng ban & Agent / AI Provider & Routing.</p>}
      </div>
      {spec.panels[0] !== "telegram" && (
        <div className="card"><div className="row">
          <Field label="Dự án"><select value={pid} onChange={(e) => setPid(e.target.value)}><option value="">— chọn dự án —</option>{projects.data?.items.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select></Field>
          {mine && <Field label={`Tiến độ phòng này trong dự án: ${mine.done}/${mine.total} (${mine.pct}%)`}><div className="bar big"><i style={{ width: `${mine.pct}%` }} /></div></Field>}
        </div></div>)}

      {spec.panels[0] === "telegram" && (
        <div className="card"><b>🚧 Chưa triển khai (Not Implemented)</b>
          <p>Bot Telegram được bỏ qua theo quyết định của chủ studio. Khi làm sẽ cần: xác thực Telegram user ID (danh sách được phép), phân quyền theo vai trò, ghi audit log, bảo vệ bot token, chuyển yêu cầu nhạy cảm sang Approval Center.</p>
          <p>Hiện tại thông báo được xem ở <a href="#center">Trung tâm CEO</a> (thanh bên, tiêu đề tab, thông báo trình duyệt).</p></div>)}

      {needsProject && !pid && <div className="card"><Empty text="Hãy tạo/chọn một dự án để dùng trang này." /></div>}
      {num > 0 && <>
        <QuickAssign dkey={dkey} pid={num} p={p} onDone={refresh} />
        <div className="card"><b>Việc của phòng này trong dự án</b>{" "}<button className="btn ghost" onClick={() => go("tasks")}>Mở Task Center →</button>
          <Async loading={tasks.loading && !tasks.data} error={tasks.error}>
            {tasks.data?.items.length ? <div className="tablewrap"><table><thead><tr><th>ID</th><th>Tiêu đề</th><th>Trạng thái</th><th></th></tr></thead><tbody>
              {tasks.data.items.map((t) => <TaskRow key={t.id} t={t} pid={num} docKind={spec.docs?.[0]} p={p} refresh={refresh} />)}</tbody></table></div> : <Empty text="Chưa có nhiệm vụ nào. Giao việc ở form phía trên." />}
          </Async></div>
        {spec.panels.map((k) => {
          if (k === "docs") return <DocsPanel key={k} pid={num} kinds={spec.docs!} p={p} />;
          if (k === "tests") return <TestsPanel key={k} pid={num} p={p} />;
          if (k === "builds") return <BuildsPanel key={k} pid={num} p={p} />;
          if (k === "builds_only") return <BuildsPanel key={k} pid={num} p={p} />;
          if (k === "checklist") return <ChecklistPanel key={k} pid={num} p={p} />;
          if (k === "checklist_legal") return <ChecklistPanel key={k} pid={num} p={p} only={["licenses_reviewed", "assets_approved", "privacy_policy", "store_metadata"]} />;
          if (k === "finance") return <FinancePanel key={k} pid={num} p={p} />;
          if (k === "analytics") return <AnalyticsPanel key={k} pid={num} p={p} />;
          if (k === "assets_image") return <AssetsMini key={k} pid={num} kind="image" go={go} />;
          if (k === "assets_audio") return <AssetsMini key={k} pid={num} kind="audio" go={go} />;
          if (k === "assets_all") return <AssetsMini key={k} pid={num} go={go} />;
          return null;
        })}
      </>}
      {!num && dkey === "finance" && <FinancePanel pid={null} p={p} />}

      <div className="card"><b>Bài học của phòng này</b>{" "}<button className="btn ghost" onClick={() => go("lessons")}>Mở Sổ bài học →</button>
        <Async loading={lessons.loading && !lessons.data} error={lessons.error}>
          {lessons.data?.items.length ? <ul>{lessons.data.items.slice(0, 6).map((l) => <li key={l.id}>{l.text} <span className="muted">({l.project_id ? "riêng dự án" : "mọi dự án"}, đã dùng {l.uses} lần)</span></li>)}</ul> : <Empty text="Chưa có bài học đang dùng. Ghi chú của bạn khi Chấp nhận/Sửa lại trong Hộp thư CEO sẽ trở thành bài học." />}
        </Async></div>
    </>
  );
}

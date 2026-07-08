import { useEffect, useMemo, useState } from "react";
import { backendApi } from "../api/backendApi";
import { ChecklistTable } from "../components/ChecklistTable";
import { EvidenceDrawer } from "../components/EvidenceDrawer";
import type { ChecklistItem, MissingPolicyItem, Project } from "../types";

export function ResultViewer({ project }: { project: Project }) {
  const [items, setItems] = useState<ChecklistItem[]>([]);
  const [missing, setMissing] = useState<MissingPolicyItem[]>([]);
  const [moduleFilter, setModuleFilter] = useState("");
  const [confidenceFilter, setConfidenceFilter] = useState("");
  const [drawerItem, setDrawerItem] = useState<ChecklistItem | null>(null);
  const [message, setMessage] = useState("");
  const load = () => {
    backendApi.listChecklist(project.id).then(setItems);
    backendApi.listMissing(project.id).then(setMissing);
  };
  useEffect(() => { load(); }, [project.id]);

  const filtered = useMemo(() => items.filter((item) => {
    if (moduleFilter && item.module !== moduleFilter) return false;
    if (confidenceFilter && item.confidence !== confidenceFilter) return false;
    return true;
  }), [items, moduleFilter, confidenceFilter]);
  const modules = Array.from(new Set(items.map((item) => item.module).filter(Boolean)));

  const exportFile = async (format: "xlsx" | "docx" | "json") => {
    const result = await backendApi.exportProject(project.id, format);
    setMessage(`已导出：${result.path}`);
  };

  return (
    <div>
      <div className="page-head">
        <div><h1>结果查看</h1><p>查看、筛选和导出访谈清单；点击行查看证据片段。</p></div>
        <div className="row-actions"><button onClick={() => exportFile("xlsx")}>导出 Excel</button><button onClick={() => exportFile("docx")}>导出 Word</button><button onClick={() => exportFile("json")}>导出 JSON</button></div>
      </div>
      {message && <div className="notice">{message}</div>}
      <div className="filters">
        <select value={moduleFilter} onChange={(e) => setModuleFilter(e.target.value)}><option value="">全部模块</option>{modules.map((module) => <option key={module} value={module}>{module}</option>)}</select>
        <select value={confidenceFilter} onChange={(e) => setConfidenceFilter(e.target.value)}><option value="">全部置信度</option>{["高", "中", "低", "无依据"].map((value) => <option key={value} value={value}>{value}</option>)}</select>
      </div>
      <ChecklistTable items={filtered} onOpenEvidence={setDrawerItem} />
      <div className="panel">
        <div className="panel-title">制度缺失项</div>
        {missing.length === 0 ? <div className="muted">暂无制度缺失项</div> : missing.map((item) => <div className="missing" key={item.id}><strong>{item.module}</strong><span>{item.issue}</span></div>)}
      </div>
      <EvidenceDrawer item={drawerItem} onClose={() => setDrawerItem(null)} />
    </div>
  );
}


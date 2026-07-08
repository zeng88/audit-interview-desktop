import { useState } from "react";
import { backendApi } from "../api/backendApi";
import type { Project } from "../types";

export function ProjectCreate({ onCreated, onCancel }: { onCreated: (project: Project) => void; onCancel: () => void }) {
  const [form, setForm] = useState({
    project_name: "",
    company_name: "",
    industry: "",
    audit_objective: "",
    audit_period: "",
    focus_areas: "",
  });
  const [error, setError] = useState("");

  const update = (key: string, value: string) => setForm((prev) => ({ ...prev, [key]: value }));
  const submit = async () => {
    setError("");
    try {
      onCreated(await backendApi.createProject(form));
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>新建项目</h1>
          <p>录入项目背景，后续生成问题会使用这些上下文。</p>
        </div>
      </div>
      {error && <div className="alert">{error}</div>}
      <div className="form-grid">
        <label>项目名称<input value={form.project_name} onChange={(e) => update("project_name", e.target.value)} /></label>
        <label>公司名称<input value={form.company_name} onChange={(e) => update("company_name", e.target.value)} /></label>
        <label>所属行业<input value={form.industry} onChange={(e) => update("industry", e.target.value)} /></label>
        <label>审计期间<input value={form.audit_period} onChange={(e) => update("audit_period", e.target.value)} /></label>
        <label className="wide">审计目标<textarea value={form.audit_objective} onChange={(e) => update("audit_objective", e.target.value)} /></label>
        <label className="wide">关注模块<textarea value={form.focus_areas} placeholder="例如：采购管理,合同管理,付款管理" onChange={(e) => update("focus_areas", e.target.value)} /></label>
      </div>
      <div className="actions">
        <button onClick={onCancel}>取消</button>
        <button className="primary" onClick={submit} disabled={!form.project_name}>创建并进入</button>
      </div>
    </div>
  );
}


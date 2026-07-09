import { useEffect, useState } from "react";
import { backendApi } from "../api/backendApi";
import { TaskLogPanel } from "../components/TaskLogPanel";
import type { ModelConfig, Project, TaskLog } from "../types";

export function GenerateChecklist({ project }: { project: Project }) {
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [logs, setLogs] = useState<TaskLog[]>([]);
  const [questionCount, setQuestionCount] = useState(20);
  const [modules, setModules] = useState(project.focus_areas || "采购管理,合同管理,付款管理");
  const [message, setMessage] = useState("");
  const [running, setRunning] = useState(false);
  // 多模型场景下优先使用用户设置的默认模型，未设置时再回退到列表首个模型。
  const chat = models.find((item) => item.config_type === "chat" && item.is_default) || models.find((item) => item.config_type === "chat");
  const embedding = models.find((item) => item.config_type === "embedding" && item.is_default) || models.find((item) => item.config_type === "embedding");
  const loadLogs = () => backendApi.listLogs(project.id).then(setLogs);
  useEffect(() => { backendApi.listModelConfigs().then(setModels); loadLogs(); }, [project.id]);
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(loadLogs, 1000);
    return () => window.clearInterval(timer);
  }, [running, project.id]);

  const generate = async () => {
    setRunning(true);
    setMessage("生成中...");
    try {
      const result = await backendApi.generateChecklist(project.id, {
        chat_model_config_id: chat?.id,
        embedding_model_config_id: embedding?.id,
        question_count: questionCount,
        modules: modules.split(/[,，]/).map((item) => item.trim()).filter(Boolean),
      });
      setMessage(`生成完成：${JSON.stringify(result)}`);
      await loadLogs();
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      setMessage(`生成失败：${detail}`);
      await loadLogs();
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <div className="page-head"><div><h1>生成清单</h1><p>基于项目背景、关注模块和制度检索结果生成访谈问题及依据。</p></div></div>
      <div className="form-grid">
        <label>推理模型<input value={chat?.config_name || "本地降级"} readOnly /></label>
        <label>向量模型<input value={embedding?.config_name || "未配置"} readOnly /></label>
        <label>问题数量<input type="number" value={questionCount} onChange={(e) => setQuestionCount(Number(e.target.value))} /></label>
        <label className="wide">关注模块<textarea value={modules} onChange={(e) => setModules(e.target.value)} /></label>
      </div>
      <div className="actions"><button className="primary" disabled={!embedding || running} onClick={generate}>{running ? "生成中..." : "开始生成"}</button></div>
      {message && <div className="notice">{message}</div>}
      <TaskLogPanel logs={logs} />
    </div>
  );
}

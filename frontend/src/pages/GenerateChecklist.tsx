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
  const chat = models.find((item) => item.config_type === "chat");
  const embedding = models.find((item) => item.config_type === "embedding");
  const loadLogs = () => backendApi.listLogs(project.id).then(setLogs);
  useEffect(() => { backendApi.listModelConfigs().then(setModels); loadLogs(); }, [project.id]);

  const generate = async () => {
    setMessage("生成中...");
    const result = await backendApi.generateChecklist(project.id, {
      chat_model_config_id: chat?.id,
      embedding_model_config_id: embedding?.id,
      question_count: questionCount,
      modules: modules.split(/[,，]/).map((item) => item.trim()).filter(Boolean),
    });
    setMessage(`生成完成：${JSON.stringify(result)}`);
    await loadLogs();
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
      <div className="actions"><button className="primary" disabled={!embedding} onClick={generate}>开始生成</button></div>
      {message && <div className="notice">{message}</div>}
      <TaskLogPanel logs={logs} />
    </div>
  );
}


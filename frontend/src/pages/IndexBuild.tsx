import { useEffect, useState } from "react";
import { backendApi } from "../api/backendApi";
import { TaskLogPanel } from "../components/TaskLogPanel";
import type { ModelConfig, Project, TaskLog } from "../types";

export function IndexBuild({ project }: { project: Project }) {
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [logs, setLogs] = useState<TaskLog[]>([]);
  const [query, setQuery] = useState("采购需求审批流程是什么？");
  const [result, setResult] = useState("");
  const [running, setRunning] = useState("");
  // 构建和检索都优先走默认向量模型，保证多个模型时用户选择生效。
  const embedding = models.find((item) => item.config_type === "embedding" && item.is_default) || models.find((item) => item.config_type === "embedding");
  const embeddingBatchSize = Math.min(embedding?.embedding_batch_size || 10, 10);
  const loadLogs = () => backendApi.listLogs(project.id).then(setLogs);
  useEffect(() => { backendApi.listModelConfigs("embedding").then(setModels); loadLogs(); }, [project.id]);
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(loadLogs, 1000);
    return () => window.clearInterval(timer);
  }, [running, project.id]);

  const run = async (name: string, action: () => Promise<unknown>) => {
    setRunning(name);
    setResult(`${name}执行中...`);
    try {
      const data = await action();
      setResult(JSON.stringify(data, null, 2));
      await loadLogs();
    } finally {
      setRunning("");
    }
  };

  return (
    <div>
      <div className="page-head"><div><h1>索引构建</h1><p>按顺序解析文件、生成切片、构建向量索引，再做检索测试。</p></div></div>
      <div className="steps">
        <button disabled={!!running} onClick={() => run("解析文件", () => backendApi.parseFiles(project.id))}>1 解析文件</button>
        <button disabled={!!running} onClick={() => run("生成切片", () => backendApi.chunkFiles(project.id, 800, 120))}>2 生成切片</button>
        <button disabled={!embedding || !!running} onClick={() => run("构建向量索引", () => backendApi.buildVectorIndex(project.id, embedding!.id, embeddingBatchSize))}>3 构建向量索引</button>
      </div>
      {running && <div className="notice">{running}执行中，页面会自动刷新进度。</div>}
      <div className="search-row">
        <input value={query} onChange={(e) => setQuery(e.target.value)} />
        <button className="primary" disabled={!embedding || !!running} onClick={() => run("检索测试", () => backendApi.searchTest(project.id, query, embedding?.id))}>检索测试</button>
      </div>
      <pre className="output">{result}</pre>
      <TaskLogPanel logs={logs} />
    </div>
  );
}

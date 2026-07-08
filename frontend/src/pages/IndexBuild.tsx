import { useEffect, useState } from "react";
import { backendApi } from "../api/backendApi";
import { TaskLogPanel } from "../components/TaskLogPanel";
import type { ModelConfig, Project, TaskLog } from "../types";

export function IndexBuild({ project }: { project: Project }) {
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [logs, setLogs] = useState<TaskLog[]>([]);
  const [query, setQuery] = useState("采购需求审批流程是什么？");
  const [result, setResult] = useState("");
  const embedding = models.find((item) => item.config_type === "embedding");
  const loadLogs = () => backendApi.listLogs(project.id).then(setLogs);
  useEffect(() => { backendApi.listModelConfigs("embedding").then(setModels); loadLogs(); }, [project.id]);

  const run = async (name: string, action: () => Promise<unknown>) => {
    setResult(`${name}执行中...`);
    const data = await action();
    setResult(JSON.stringify(data, null, 2));
    await loadLogs();
  };

  return (
    <div>
      <div className="page-head"><div><h1>索引构建</h1><p>按顺序解析文件、生成切片、构建向量索引，再做检索测试。</p></div></div>
      <div className="steps">
        <button onClick={() => run("解析文件", () => backendApi.parseFiles(project.id))}>1 解析文件</button>
        <button onClick={() => run("生成切片", () => backendApi.chunkFiles(project.id, 800, 120))}>2 生成切片</button>
        <button disabled={!embedding} onClick={() => run("构建向量索引", () => backendApi.buildVectorIndex(project.id, embedding!.id, 16))}>3 构建向量索引</button>
      </div>
      <div className="search-row">
        <input value={query} onChange={(e) => setQuery(e.target.value)} />
        <button className="primary" disabled={!embedding} onClick={() => run("检索测试", () => backendApi.searchTest(project.id, query, embedding?.id))}>检索测试</button>
      </div>
      <pre className="output">{result}</pre>
      <TaskLogPanel logs={logs} />
    </div>
  );
}


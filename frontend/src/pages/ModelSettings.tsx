import { useEffect, useState } from "react";
import { backendApi } from "../api/backendApi";
import type { ModelConfig } from "../types";

const emptyForm = {
  config_name: "",
  config_type: "chat" as "chat" | "embedding",
  provider: "openai-compatible",
  base_url: "",
  api_key: "",
  model: "",
  temperature: 0.2,
  max_tokens: 4096,
  embedding_dimension: 64,
  embedding_batch_size: 16,
  timeout_seconds: 120,
  is_default: 1,
};

export function ModelSettings() {
  const [configs, setConfigs] = useState<ModelConfig[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [message, setMessage] = useState("");
  const load = () => backendApi.listModelConfigs().then(setConfigs);
  useEffect(() => { load(); }, []);
  const update = (key: string, value: string | number) => setForm((prev) => ({ ...prev, [key]: value }));

  const save = async () => {
    await backendApi.createModelConfig(form);
    setForm(emptyForm);
    await load();
  };

  return (
    <div>
      <div className="page-head"><div><h1>模型配置</h1><p>可配置 OpenAI-compatible 推理模型和向量模型；不填密钥时走本地降级模式。</p></div></div>
      <div className="form-grid">
        <label>类型<select value={form.config_type} onChange={(e) => update("config_type", e.target.value)}><option value="chat">推理模型</option><option value="embedding">向量模型</option></select></label>
        <label>配置名称<input value={form.config_name} onChange={(e) => update("config_name", e.target.value)} /></label>
        <label>Base URL<input value={form.base_url} onChange={(e) => update("base_url", e.target.value)} /></label>
        <label>API Key<input value={form.api_key} onChange={(e) => update("api_key", e.target.value)} /></label>
        <label>模型<input value={form.model} onChange={(e) => update("model", e.target.value)} /></label>
        <label>向量维度<input type="number" value={form.embedding_dimension} onChange={(e) => update("embedding_dimension", Number(e.target.value))} /></label>
      </div>
      <div className="actions"><button className="primary" disabled={!form.config_name || !form.model} onClick={save}>保存配置</button></div>
      {message && <div className="notice">{message}</div>}
      <div className="table-wrap">
        <table>
          <thead><tr><th>名称</th><th>类型</th><th>模型</th><th>默认</th><th>操作</th></tr></thead>
          <tbody>
            {configs.map((config) => (
              <tr key={config.id}>
                <td>{config.config_name}</td>
                <td>{config.config_type}</td>
                <td>{config.model}</td>
                <td>{config.is_default ? "是" : "否"}</td>
                <td className="row-actions">
                  <button onClick={() => backendApi.testModelConfig(config.id).then((r) => setMessage(JSON.stringify(r)))}>测试</button>
                  <button onClick={() => backendApi.deleteModelConfig(config.id).then(load)}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}


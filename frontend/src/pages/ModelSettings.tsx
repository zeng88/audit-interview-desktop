import { useEffect, useState } from "react";
import { backendApi } from "../api/backendApi";
import type { ModelConfig } from "../types";

type ModelForm = Omit<ModelConfig, "id">;

const emptyForm: ModelForm = {
  config_name: "",
  config_type: "chat" as "chat" | "embedding",
  provider: "openai-compatible",
  base_url: "",
  api_key: "",
  model: "",
  temperature: 0.2,
  max_tokens: 4096,
  embedding_dimension: 1024,
  embedding_batch_size: 16,
  timeout_seconds: 120,
  is_default: 1,
};

const embeddingDimensions = [64, 384, 768, 1024, 1536, 2048, 3072];

export function ModelSettings() {
  const [configs, setConfigs] = useState<ModelConfig[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<ModelForm>(emptyForm);
  const [message, setMessage] = useState("");
  const load = () => backendApi.listModelConfigs().then(setConfigs);
  useEffect(() => { load(); }, []);
  const update = <K extends keyof ModelForm>(key: K, value: ModelForm[K]) => setForm((prev) => ({ ...prev, [key]: value }));

  const buildPayload = () => {
    // 推理模型不提交向量参数，避免后期维护时误把无关字段展示或写入。
    const payload = form.config_type === "chat"
      ? {
          config_name: form.config_name,
          config_type: form.config_type,
          provider: form.provider,
          base_url: form.base_url,
          api_key: form.api_key,
          model: form.model,
          temperature: form.temperature,
          max_tokens: form.max_tokens,
          timeout_seconds: form.timeout_seconds,
          is_default: form.is_default,
        }
      : form;
    return payload;
  };

  const resetForm = () => {
    setEditingId(null);
    setForm(emptyForm);
    setMessage("");
  };

  const save = async () => {
    const payload = buildPayload();
    if (editingId) {
      await backendApi.updateModelConfig(editingId, payload);
      setMessage("模型配置已更新");
    } else {
      await backendApi.createModelConfig(payload);
      setMessage("模型配置已保存");
    }
    setEditingId(null);
    setForm(emptyForm);
    await load();
  };

  const edit = (config: ModelConfig) => {
    // 编辑时回填所有可维护字段，API Key 为空时允许用户重新输入。
    setEditingId(config.id);
    setForm({
      config_name: config.config_name,
      config_type: config.config_type,
      provider: config.provider,
      base_url: config.base_url,
      api_key: config.api_key || "",
      model: config.model,
      temperature: config.temperature ?? 0.2,
      max_tokens: config.max_tokens ?? 4096,
      embedding_dimension: config.embedding_dimension || 1024,
      embedding_batch_size: config.embedding_batch_size || 16,
      timeout_seconds: config.timeout_seconds || 120,
      is_default: config.is_default ? 1 : 0,
    });
    setMessage(`正在编辑：${config.config_name}`);
  };

  const setDefault = async (config: ModelConfig) => {
    // 默认模型由后端按模型类型互斥处理，前端只负责触发用户选择。
    await backendApi.setDefaultModel(config.id);
    setMessage(`已将 ${config.config_name} 设为默认${config.config_type === "chat" ? "推理模型" : "向量模型"}`);
    await load();
  };

  const remove = async (config: ModelConfig) => {
    await backendApi.deleteModelConfig(config.id);
    if (editingId === config.id) resetForm();
    await load();
  };

  return (
    <div>
      <div className="page-head"><div><h1>模型配置</h1><p>可配置 OpenAI-compatible 推理模型和向量模型；不填密钥时走本地降级模式。</p></div></div>
      <div className="form-grid">
        <label>类型<select value={form.config_type} onChange={(e) => update("config_type", e.target.value as ModelForm["config_type"])}><option value="chat">推理模型</option><option value="embedding">向量模型</option></select></label>
        <label>配置名称<input value={form.config_name} onChange={(e) => update("config_name", e.target.value)} /></label>
        <label>Provider<input value={form.provider} onChange={(e) => update("provider", e.target.value)} /></label>
        <label>Base URL<input value={form.base_url} onChange={(e) => update("base_url", e.target.value)} /></label>
        <label>API Key<input value={form.api_key} onChange={(e) => update("api_key", e.target.value)} /></label>
        <label>模型<input value={form.model} onChange={(e) => update("model", e.target.value)} /></label>
        {form.config_type === "chat" && (
          <>
            <label>Temperature<input type="number" step="0.1" value={form.temperature} onChange={(e) => update("temperature", Number(e.target.value))} /></label>
            <label>Max Tokens<input type="number" value={form.max_tokens} onChange={(e) => update("max_tokens", Number(e.target.value))} /></label>
          </>
        )}
        {form.config_type === "embedding" && (
          <>
            <label>向量维度<select value={form.embedding_dimension} onChange={(e) => update("embedding_dimension", Number(e.target.value))}>{embeddingDimensions.map((dimension) => <option key={dimension} value={dimension}>{dimension}</option>)}</select></label>
            <label>Batch Size<input type="number" value={form.embedding_batch_size} onChange={(e) => update("embedding_batch_size", Number(e.target.value))} /></label>
          </>
        )}
        <label>Timeout 秒<input type="number" value={form.timeout_seconds} onChange={(e) => update("timeout_seconds", Number(e.target.value))} /></label>
        <label className="inline-check"><input type="checkbox" checked={Boolean(form.is_default)} onChange={(e) => update("is_default", e.target.checked ? 1 : 0)} /> 设为默认模型</label>
      </div>
      <div className="actions">
        <button className="primary" disabled={!form.config_name || !form.model} onClick={save}>{editingId ? "保存修改" : "保存配置"}</button>
        {editingId && <button onClick={resetForm}>取消编辑</button>}
      </div>
      {message && <div className="notice">{message}</div>}
      <div className="table-wrap">
        <table>
          <thead><tr><th>名称</th><th>类型</th><th>Provider</th><th>地址</th><th>模型</th><th>维度</th><th>默认</th><th>操作</th></tr></thead>
          <tbody>
            {configs.map((config) => (
              <tr key={config.id}>
                <td>{config.config_name}</td>
                <td>{config.config_type}</td>
                <td>{config.provider}</td>
                <td className="muted">{config.base_url || "-"}</td>
                <td>{config.model}</td>
                <td>{config.config_type === "embedding" ? config.embedding_dimension : "-"}</td>
                <td>{config.is_default ? "是" : "否"}</td>
                <td className="row-actions">
                  <button onClick={() => edit(config)}>编辑</button>
                  <button disabled={Boolean(config.is_default)} onClick={() => setDefault(config)}>设为默认</button>
                  <button onClick={() => backendApi.testModelConfig(config.id).then((r) => setMessage(JSON.stringify(r)))}>测试</button>
                  <button onClick={() => remove(config)}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

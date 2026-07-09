import type { AuditFile, ChecklistItem, MissingPolicyItem, ModelConfig, Project, StorageLocation, TaskLog } from "../types";

const API_BASE = import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8765";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: options.body instanceof FormData ? options.headers : { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!response.ok) {
    const text = await response.text();
    let detail = "";
    try {
      const data = JSON.parse(text) as { detail?: unknown };
      detail = typeof data.detail === "string" ? data.detail : "";
    } catch {
      // 非 JSON 错误保持原始文本，便于排查代理或网关异常。
    }
    throw new Error(detail || text || `请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const backendApi = {
  health: () => request<{ status: string; version: string }>("/health"),
  storageLocation: () => request<StorageLocation>("/storage-location"),
  listProjects: () => request<Project[]>("/projects"),
  createProject: (data: Partial<Project>) => request<Project>("/projects", { method: "POST", body: JSON.stringify(data) }),
  deleteProject: (id: number) => request<{ ok: boolean }>(`/projects/${id}`, { method: "DELETE" }),
  listFiles: (projectId: number) => request<AuditFile[]>(`/projects/${projectId}/files`),
  uploadFile: (projectId: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<AuditFile>(`/projects/${projectId}/files`, { method: "POST", body: form });
  },
  deleteFile: (projectId: number, fileId: number) => request<{ ok: boolean }>(`/projects/${projectId}/files/${fileId}`, { method: "DELETE" }),
  parseFiles: (projectId: number) => request<Record<string, number>>(`/projects/${projectId}/parse`, { method: "POST" }),
  chunkFiles: (projectId: number, chunkSize: number, overlap: number) =>
    request<Record<string, number>>(`/projects/${projectId}/chunk`, { method: "POST", body: JSON.stringify({ chunk_size: chunkSize, overlap }) }),
  listModelConfigs: (configType?: "chat" | "embedding") =>
    request<ModelConfig[]>(`/model-configs${configType ? `?config_type=${configType}` : ""}`),
  createModelConfig: (data: Partial<ModelConfig>) => request<ModelConfig>("/model-configs", { method: "POST", body: JSON.stringify(data) }),
  updateModelConfig: (id: number, data: Partial<ModelConfig>) => request<ModelConfig>(`/model-configs/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteModelConfig: (id: number) => request<{ ok: boolean }>(`/model-configs/${id}`, { method: "DELETE" }),
  setDefaultModel: (id: number) => request<ModelConfig>(`/model-configs/${id}/default`, { method: "POST" }),
  testModelConfig: (id: number) => request<Record<string, unknown>>(`/model-configs/${id}/test`, { method: "POST" }),
  buildVectorIndex: (projectId: number, embeddingId: number, batchSize: number) =>
    request<Record<string, unknown>>(`/projects/${projectId}/build-vector-index`, {
      method: "POST",
      body: JSON.stringify({ embedding_model_config_id: embeddingId, batch_size: batchSize }),
    }),
  searchTest: (projectId: number, query: string, embeddingId?: number, topK = 10) =>
    request<{ results: Array<Record<string, unknown>> }>(`/projects/${projectId}/search-test`, {
      method: "POST",
      body: JSON.stringify({ query, embedding_model_config_id: embeddingId, top_k: topK }),
    }),
  generateChecklist: (projectId: number, data: Record<string, unknown>) =>
    request<Record<string, number>>(`/projects/${projectId}/generate-checklist`, { method: "POST", body: JSON.stringify(data) }),
  listChecklist: (projectId: number) => request<ChecklistItem[]>(`/projects/${projectId}/checklist`),
  updateChecklist: (projectId: number, itemId: number, data: Partial<ChecklistItem>) =>
    request<ChecklistItem>(`/projects/${projectId}/checklist/${itemId}`, { method: "PUT", body: JSON.stringify(data) }),
  listMissing: (projectId: number) => request<MissingPolicyItem[]>(`/projects/${projectId}/missing-policy-items`),
  exportProject: (projectId: number, format: "xlsx" | "docx" | "json") =>
    request<{ path: string; file_name: string }>(`/projects/${projectId}/export`, { method: "POST", body: JSON.stringify({ format }) }),
  listLogs: (projectId: number) => request<TaskLog[]>(`/projects/${projectId}/logs`),
  taskProgress: (projectId: number, taskType?: string) =>
    request<TaskLog | Record<string, never>>(`/projects/${projectId}/task-progress${taskType ? `?task_type=${taskType}` : ""}`),
};

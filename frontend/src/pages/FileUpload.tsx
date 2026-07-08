import { useEffect, useState } from "react";
import { backendApi } from "../api/backendApi";
import type { AuditFile, Project } from "../types";

export function FileUpload({ project }: { project: Project }) {
  const [files, setFiles] = useState<AuditFile[]>([]);
  const [message, setMessage] = useState("");
  const load = () => backendApi.listFiles(project.id).then(setFiles);
  useEffect(() => { load(); }, [project.id]);

  const upload = async (selected: FileList | null) => {
    if (!selected) return;
    setMessage("上传中...");
    for (const file of Array.from(selected)) await backendApi.uploadFile(project.id, file);
    await load();
    setMessage("上传完成");
  };

  return (
    <div>
      <div className="page-head"><div><h1>文件上传</h1><p>支持 PDF、DOCX、XLSX、TXT、CSV、Markdown。</p></div></div>
      <label className="dropzone">
        <input type="file" multiple accept=".pdf,.docx,.xlsx,.txt,.csv,.md,.markdown" onChange={(e) => upload(e.target.files)} />
        <strong>选择或拖入制度文件</strong>
        <span>文件将保存在本地 storage 目录</span>
      </label>
      {message && <div className="notice">{message}</div>}
      <div className="table-wrap">
        <table>
          <thead><tr><th>文件名</th><th>类型</th><th>大小</th><th>解析状态</th><th>错误</th><th>操作</th></tr></thead>
          <tbody>
            {files.map((file) => (
              <tr key={file.id}>
                <td>{file.original_name}</td>
                <td>{file.file_type}</td>
                <td>{Math.round(file.file_size / 1024)} KB</td>
                <td><span className={`pill ${file.parse_status}`}>{file.parse_status}</span></td>
                <td>{file.parse_error || "-"}</td>
                <td><button onClick={() => backendApi.deleteFile(project.id, file.id).then(load)}>删除</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

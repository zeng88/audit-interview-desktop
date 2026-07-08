import { useEffect, useState } from "react";
import { backendApi } from "../api/backendApi";
import type { Project } from "../types";

export function ProjectList({ onCreate, onOpen }: { onCreate: () => void; onOpen: (project: Project) => void }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState("");

  const load = () => backendApi.listProjects().then(setProjects).catch((err) => setError(err.message));
  useEffect(() => { load(); }, []);

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>项目</h1>
          <p>管理本地审计项目和已生成的访谈清单。</p>
        </div>
        <button className="primary" onClick={onCreate}>新建项目</button>
      </div>
      {error && <div className="alert">{error}</div>}
      <div className="project-grid">
        {projects.map((project) => (
          <article className="project-card" key={project.id} onClick={() => onOpen(project)}>
            <strong>{project.project_name}</strong>
            <span>{project.company_name || "未填写公司"}</span>
            <div className="meta">
              <span>{project.industry || "未填写行业"}</span>
              <span>{project.file_count || 0} 文件</span>
              <span>{project.checklist_count || 0} 清单</span>
            </div>
            <button
              onClick={(event) => {
                event.stopPropagation();
                if (confirm("确认删除该项目？")) backendApi.deleteProject(project.id).then(load);
              }}
            >
              删除
            </button>
          </article>
        ))}
      </div>
      {projects.length === 0 && <div className="empty">暂无项目，请新建一个审计项目。</div>}
    </div>
  );
}


import { useEffect, useState } from "react";
import { backendApi } from "./api/backendApi";
import type { Project } from "./types";
import { FileUpload } from "./pages/FileUpload";
import { GenerateChecklist } from "./pages/GenerateChecklist";
import { IndexBuild } from "./pages/IndexBuild";
import { ModelSettings } from "./pages/ModelSettings";
import { ProjectCreate } from "./pages/ProjectCreate";
import { ProjectList } from "./pages/ProjectList";
import { ResultViewer } from "./pages/ResultViewer";

type Page = "projects" | "create" | "files" | "models" | "index" | "generate" | "results";

const navItems: Array<{ key: Page; label: string; needsProject?: boolean }> = [
  { key: "projects", label: "项目" },
  { key: "files", label: "文件", needsProject: true },
  { key: "models", label: "模型配置" },
  { key: "index", label: "索引构建", needsProject: true },
  { key: "generate", label: "生成清单", needsProject: true },
  { key: "results", label: "结果查看", needsProject: true },
];

export default function App() {
  const [page, setPage] = useState<Page>("projects");
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [backendStatus, setBackendStatus] = useState("检查中");

  useEffect(() => {
    backendApi
      .health()
      .then((data) => setBackendStatus(`${data.status} v${data.version}`))
      .catch(() => setBackendStatus("未连接"));
  }, []);

  const renderPage = () => {
    if (page === "projects") {
      return <ProjectList onCreate={() => setPage("create")} onOpen={(project) => { setCurrentProject(project); setPage("files"); }} />;
    }
    if (page === "create") {
      return <ProjectCreate onCreated={(project) => { setCurrentProject(project); setPage("files"); }} onCancel={() => setPage("projects")} />;
    }
    if (page === "models") return <ModelSettings />;
    if (!currentProject) return <div className="empty">请先选择一个项目。</div>;
    if (page === "files") return <FileUpload project={currentProject} />;
    if (page === "index") return <IndexBuild project={currentProject} />;
    if (page === "generate") return <GenerateChecklist project={currentProject} />;
    if (page === "results") return <ResultViewer project={currentProject} />;
    return null;
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">AI</span>
          <div>
            <strong>审计访谈清单</strong>
            <small>本地生成工具</small>
          </div>
        </div>
        <nav>
          {navItems.map((item) => (
            <button
              key={item.key}
              className={page === item.key ? "active" : ""}
              disabled={item.needsProject && !currentProject}
              onClick={() => setPage(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="workspace">
        <header className="topbar">
          <div>
            <strong>{currentProject?.project_name || "未选择项目"}</strong>
            <span>{currentProject?.company_name || "请从项目列表进入"}</span>
          </div>
          <div className={`status ${backendStatus.includes("ok") ? "good" : "bad"}`}>后端：{backendStatus}</div>
        </header>
        <section className="content">{renderPage()}</section>
      </main>
    </div>
  );
}


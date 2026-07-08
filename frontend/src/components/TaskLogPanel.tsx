import type { TaskLog } from "../types";

export function TaskLogPanel({ logs }: { logs: TaskLog[] }) {
  return (
    <div className="panel">
      <div className="panel-title">任务日志</div>
      <div className="log-list">
        {logs.length === 0 && <div className="muted">暂无日志</div>}
        {logs.map((log) => (
          <div className="log-line" key={log.id}>
            <span className={`pill ${log.status}`}>{log.status}</span>
            <span>{log.task_type}</span>
            <span>
              {log.message}
              {log.progress_total > 0 && (
                <span className="progress-inline">
                  <span className="progress-bar"><i style={{ width: `${log.progress_percent}%` }} /></span>
                  <b>{log.progress_percent}%</b>
                </span>
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

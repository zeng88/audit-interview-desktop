import type { TaskLog } from "../types";

const taskLabels: Record<string, string> = {
  upload: "上传文件",
  parse: "解析文件",
  chunk: "生成切片",
  embedding: "构建向量索引",
  retrieval: "检索证据",
  checklist: "生成清单",
  export: "导出结果",
};

const statusLabels: Record<string, string> = {
  running: "进行中",
  success: "正常完成",
  finished: "正常完成",
  failed: "失败",
  warning: "提醒",
};

function taskName(taskType: string) {
  return taskLabels[taskType] || taskType;
}

function statusName(status: string) {
  return statusLabels[status] || status;
}

export function TaskLogPanel({ logs }: { logs: TaskLog[] }) {
  const latest = logs[0];
  const latestTaskType = latest?.task_type;
  const latestStartIndex = latestTaskType
    ? logs.findIndex((log) => log.task_type === latestTaskType && log.status === "running" && log.message.startsWith("开始"))
    : -1;
  const currentRunLogs = latestStartIndex >= 0 ? logs.slice(0, latestStartIndex + 1) : logs.slice(0, 12);
  const currentPercent = latest?.progress_total > 0 ? latest.progress_percent : latest?.status === "success" || latest?.status === "finished" ? 100 : 0;
  const issues = currentRunLogs
    .filter((log) => log.status === "failed" || log.status === "warning")
    .filter((log, index, list) => list.findIndex((item) => item.message === log.message) === index)
    .slice(0, 4);

  return (
    <div className="panel">
      <div className="panel-title">任务进度</div>
      {!latest && <div className="muted">暂无任务记录</div>}
      {latest && (
        <div className="task-summary">
          <div className="task-summary-head">
            <span className={`pill ${latest.status}`}>{statusName(latest.status)}</span>
            <strong>{taskName(latest.task_type)}</strong>
          </div>
          <div className="task-message">{latest.message}</div>
          <div className="progress-inline">
            <span className="progress-bar wide-progress"><i style={{ width: `${currentPercent}%` }} /></span>
            <b>{currentPercent}%</b>
          </div>
        </div>
      )}
      {issues.length > 0 && (
        <div className="issue-box">
          <strong>需要关注的问题</strong>
          {issues.map((log) => (
            <div className="issue-line" key={log.id}>
              <span className={`pill ${log.status}`}>{statusName(log.status)}</span>
              <span>{taskName(log.task_type)}：{log.message}</span>
            </div>
          ))}
        </div>
      )}
      {logs.length > 0 && (
        <details className="log-details">
          <summary>查看详细日志</summary>
          <div className="log-list">
            {currentRunLogs.map((log) => (
              <div className="log-line" key={log.id}>
                <span className={`pill ${log.status}`}>{statusName(log.status)}</span>
                <span>{taskName(log.task_type)}</span>
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
        </details>
      )}
    </div>
  );
}

import type { ChecklistItem } from "../types";

export function ChecklistTable({
  items,
  onOpenEvidence,
}: {
  items: ChecklistItem[];
  onOpenEvidence: (item: ChecklistItem) => void;
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>编号</th>
            <th>模块</th>
            <th>访谈对象</th>
            <th>访谈问题</th>
            <th>制度依据答案</th>
            <th>置信度</th>
            <th>生成方式</th>
            <th>来源</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={item.id} onClick={() => onOpenEvidence(item)}>
              <td>{index + 1}</td>
              <td>{item.module}</td>
              <td>{item.interview_role}</td>
              <td>{item.interview_question}</td>
              <td>{item.expected_answer}</td>
              <td><span className={`confidence c-${item.confidence}`}>{item.confidence}</span></td>
              <td><span className={`pill ${item.generation_source === "configured_model" ? "success" : "warning"}`}>{item.generation_source === "configured_model" ? "配置模型" : "本地模板"}</span></td>
              <td>{item.source_file || "无依据"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

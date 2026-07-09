import type { ChecklistItem } from "../types";

export function EvidenceDrawer({ item, onClose }: { item: ChecklistItem | null; onClose: () => void }) {
  if (!item) return null;
  return (
    <div className="drawer-mask" onClick={onClose}>
      <aside className="drawer" onClick={(event) => event.stopPropagation()}>
        <div className="drawer-head">
          <strong>证据片段</strong>
          <button onClick={onClose}>关闭</button>
        </div>
        <dl>
          <dt>生成方式</dt>
          <dd>{item.generation_source === "configured_model" ? "配置模型生成" : "本地模板/规则生成"}</dd>
          <dt>生成说明</dt>
          <dd>{item.generation_note || "无"}</dd>
          <dt>来源文件</dt>
          <dd>{item.source_file || "无"}</dd>
          <dt>来源位置</dt>
          <dd>{item.source_location || "无"}</dd>
          <dt>原文摘录</dt>
          <dd className="quote">{item.evidence_quote || "无明确摘录"}</dd>
          <dt>建议追问</dt>
          <dd>{item.follow_up_question}</dd>
          <dt>风险提示</dt>
          <dd>{item.risk_hint}</dd>
        </dl>
      </aside>
    </div>
  );
}

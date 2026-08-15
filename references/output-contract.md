# 输入与输出契约

## 目录

- [`candidates.json` v3](#candidatesjson-v3)
- [`signals.json`](#signalsjson)
- [`brief.md`](#briefmd)
- [对话输出](#对话输出)

## `candidates.json` v3

顶层结构：

```json
{
  "schema_version": 3,
  "generated_at": "2026-07-20T09:00:00+01:00",
  "window_hours": 72,
  "signals": []
}
```

每个事件簇使用以下结构。未知互动字段直接省略，不填猜测值。

```json
{
  "id": "stable-short-id",
  "event_key": "company-product-event-date",
  "entity": "Example AI",
  "title": "English source-grounded event title",
  "type": "official-release",
  "event_time": "2026-07-20T02:30:00Z",
  "summary_cn": "发生了什么，避免评价先行。",
  "why_now_cn": "为什么它在此刻重要。",
  "audience_cn": "每周整理多渠道资料的内容运营。",
  "user_need_cn": "判断是否值得改变资料整理流程。",
  "work_task_cn": "把访谈、聊天记录和网页整理成选题简报。",
  "old_workflow_cn": "分别搜索、复制、去重，再手工整理结构。",
  "friction_cn": "时间耗在搬运与去重，判断被挤到最后。",
  "ai_change_cn": "AI 可以连续读取多份材料并给出带来源的初稿。",
  "new_workflow_cn": "人定问题和标准，AI 搜集整理，人核验来源与结论。",
  "human_role_cn": "决定问题、判断可信度并为最终结论负责。",
  "readiness": "try-now",
  "readiness_reason_cn": "产品已开放，但来源完整度仍需小任务验证。",
  "next_action_cn": "先用一份非敏感旧资料做同任务对比。",
  "topic_thesis_cn": "价值不在多一个聊天框，而在把资料搬运让给 AI。",
  "visual_proof_cn": "同任务旧流程与新流程并排，并展示来源核验节点。",
  "content_angle_cn": "从资料整理这项工作切入。",
  "hook_cn": "如果你每周都要拼一份简报，这次更新最先省掉的是来回复制。",
  "verification": "verified",
  "judgments": {
    "authority": 95,
    "evidence_quality": 90,
    "impact": 84,
    "productivity_leverage": 88,
    "workflow_clarity": 92,
    "practicality": 80,
    "audience_resonance": 86,
    "visual_evidence": 88,
    "novelty": 68,
    "search_demand": 72,
    "discussion_value": 70,
    "emotional_payoff": 74
  },
  "flags": [],
  "sources": [
    {
      "platform": "x",
      "source_name": "Original publisher",
      "url": "https://x.com/example/status/123",
      "published_at": "2026-07-20T02:30:00Z",
      "role": "primary",
      "supports_cn": "证实发布时间、核心能力和官方演示。",
      "is_primary": true,
      "engagement": {"likes": 4200, "reposts": 780, "replies": 260}
    }
  ]
}
```

v3 的生产力字段不是装饰信息。只有当来源或清楚标注的编辑推断能支持工作任务、旧流程、变化节点和成熟度时，才写高分；不能把每条技术新闻强行包装成人人都能立刻使用。

`readiness` 只能是：

- `use-now`：能力已公开、路径清楚、普通目标用户现在能完成任务。
- `try-now`：现在能小范围试，但仍有成本、权限、稳定性或核验要求。
- `watch`：与工作相关，但现在不值得迁移流程。
- `future`：主要是方向信号，尚无可执行产品或可靠路径。

所有 judgments 分数为 0–100，必须完整填写。`search_demand` 没有趋势、重复查询或工作流讨论证据时不得高于 40。v2 仍可用于历史项目；新雷达一律写 v3。

允许的 `verification`：`verified`、`attributed`、`reported`、`community-observed`、`unverified`。推荐 `type`：`official-release`、`executive-signal`、`research`、`community-breakout`、`impressive-build`、`business-org`、`controversy-risk`。

`sources[].role` 可使用 `primary`、`independent-verification`、`community-reaction`、`counter-signal`、`demand-evidence` 或 `visual-proof`。在 `supports_cn` 中写清它实际证明了什么。社区关注不能证明产品能力；官方演示不能证明所有人的实际收益。

## `signals.json`

排序器为每个事件补充：

- `scores`：热度、可信度、信号分、选题分、优先级与各生产力选题维度。
- `topic_gate_passed` 与 `topic_gate_reason`：是否值得进入内容主榜及原因。
- `readiness_label_cn`：现在可用、可以试用、暂时观望或长期趋势。
- `tier`：`S / A / B / Watch`。

顶层 `signals` 只包含同时通过信号门和选题门的主榜事件；`watchlist` 保留未过门但值得监测的信号。保存后序号即冻结。

## `brief.md`

### 开头

写明研究窗口、生成时间、扫描范围、候选簇数量、数据限制和一句主线判断。主线优先概括哪类工作正在发生什么变化，而不是罗列公司发布。

### 主榜总表

使用以下列：

| # | 级别 | 工作场景 | 改变哪一步 | 现在能否用 | 事件 | Priority | 信号分 | 选题分 |
|---:|:---:|---|---|---|---|---:|---:|---:|

事件标题链接到最重要的一手来源，分数保留一位小数。普通用户先看到自己是否相关，再决定是否展开技术细节。

### 事件卡

每条按以下顺序写：

1. **这对工作有什么实际影响**：谁在做什么任务，最痛的一步是什么。
2. **原来怎么做，现在怎么做**：用同一个任务对比工作流；明确 AI 只改变哪一步。
3. **现在能不能用**：给 readiness、理由、人的责任和最小下一步。
4. **新闻与技术依据**：发生了什么，新技术为什么足以支持这项变化。
5. **证据与边界**：一手来源、独立证据、尚未确认部分，区分事实与编辑推断。
6. **内容与视觉机会**：给选题主张、工作场景开场、推荐载体，以及能证明前后变化的画面。

如果事件与普通人的可识别任务没有可信连接，直说它是行业观察或长期趋势，不虚构工作场景。

### 今日三选

最多选 3 个，优先考虑工作流变化是否清楚、现在是否有最小行动、能否得到一手画面，以及是否有独特判断。格式：

```text
选题：
适用人群与任务：
原来最卡的一步：
AI 改变哪一步：
新工作流：
人仍需负责：
可用程度与理由：
今天能做的最小动作：
新闻依据：
推荐形式与视觉证据：
制作成本：低 / 中 / 高
时效寿命：当天 / 3 天 / 1 周以上
```

### 观察名单

最多 3 条。明确是证据不足、工作连接不清、尚未发布，还是接近 72 小时边界；不要靠焦虑强行升榜。

## 对话输出

即使同时保存文件，也在对话中展示一句主线、完整编号主榜、今日三选，以及 `brief.md` 与 `signals.json` 的可点击路径。主榜先回答这对普通人的工作有什么影响，不要只回复文件已生成。

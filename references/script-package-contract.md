# 稿件包与事实账本契约

## 目录

- [`script-package.json` v2](#script-packagejson-v2)
- [`claim-ledger.json`](#claim-ledgerjson)
- [验证与注册](#验证与注册)

每条入选新闻独立保存 `script-package.json`、`claim-ledger.json`、`script.md` 和纯口播 `script.txt`。视频只读取当前已确认的 `script.txt`。

## `script-package.json` v2

```json
{
  "schema_version": 2,
  "source_signal_id": "openai-product-event-date",
  "radar_rank": 1,
  "persona_id": "acemode-productivity-editor-v1",
  "target_duration_seconds": 60,
  "story_promise_cn": "帮助内容运营判断是否值得把资料整理交给 AI。",
  "productivity_frame": {
    "audience_cn": "每周整理多渠道素材的内容运营",
    "work_task_cn": "把访谈、聊天记录和资料整理成选题简报",
    "old_workflow_cn": "分别搜索、复制、去重，再手工整理结构",
    "friction_cn": "时间耗在搬运与去重，真正的判断被挤到最后",
    "ai_change_cn": "AI 开始能连续读取多份材料并产出带来源的初稿",
    "new_workflow_cn": "人定义问题和标准，AI 搜集整理，人核验来源与结论",
    "human_role_cn": "决定问题、判断来源可信度并对最终结论负责",
    "readiness": "try-now",
    "readiness_reason_cn": "产品已开放，但稳定性和来源完整度需要用小任务验证",
    "next_action_cn": "先用一份非敏感旧资料做同任务对比，不迁移整个流程"
  },
  "titles_cn": [
    "资料整理可以少一步",
    "别急着把研究全交给AI",
    "新模型先改变这项工作",
    "AI整理后还要查什么",
    "这次更新值得谁试"
  ],
  "segments": [
    {
      "id": "seg-01",
      "role": "hook",
      "text_cn": "如果你每周都要把几份资料拼成一份简报，这次更新最先省掉的是来回复制这一步。",
      "claim_refs": ["claim-01"]
    },
    {
      "id": "seg-02",
      "role": "old-workflow",
      "text_cn": "以前你要分别搜索、复制、去重，再自己整理结构。",
      "claim_refs": ["claim-02"]
    },
    {
      "id": "seg-03",
      "role": "news",
      "text_cn": "这次产品更新让 AI 可以连续读取多份材料，并给出带来源的初稿。",
      "claim_refs": ["claim-01"]
    },
    {
      "id": "seg-04",
      "role": "new-workflow",
      "text_cn": "新的分工是你先定问题和标准，AI 负责搜集整理，你再核验来源和结论。",
      "claim_refs": ["claim-01", "claim-03"]
    },
    {
      "id": "seg-05",
      "role": "boundary",
      "text_cn": "它已经可以试，但还不适合直接处理敏感资料，引用完整度也要人工检查。",
      "claim_refs": ["claim-04"]
    },
    {
      "id": "seg-06",
      "role": "action",
      "text_cn": "最稳妥的做法，是先拿一份非敏感旧资料做同任务对比。",
      "claim_refs": ["claim-03"]
    },
    {
      "id": "seg-07",
      "role": "closing",
      "text_cn": "这里是 AceMode，帮你把新工具变成真正能用的生产力。",
      "claim_refs": []
    }
  ],
  "narration_cn": "如果你每周都要把几份资料拼成一份简报，这次更新最先省掉的是来回复制这一步。\n以前你要分别搜索、复制、去重，再自己整理结构。\n这次产品更新让 AI 可以连续读取多份材料，并给出带来源的初稿。\n新的分工是你先定问题和标准，AI 负责搜集整理，你再核验来源和结论。\n它已经可以试，但还不适合直接处理敏感资料，引用完整度也要人工检查。\n最稳妥的做法，是先拿一份非敏感旧资料做同任务对比。\n这里是 AceMode，帮你把新工具变成真正能用的生产力。",
  "closing_text_cn": "这里是 AceMode，帮你把新工具变成真正能用的生产力。"
}
```

允许角色为 `hook`、`old-workflow`、`change`、`news`、`proof`、`new-workflow`、`boundary`、`action`、`closing`。v2 默认至少包含 hook、old-workflow、news、new-workflow、boundary、action、closing；短稿可把 change 或 proof 合并到相邻段。除 closing 外每段都要引用事实账本。

`productivity_frame.readiness` 只能是 `use-now`、`try-now`、`watch`、`future`。默认人设为 `acemode-productivity-editor-v1`，不要求固定广告句；最后一个 closing 可直接用行动建议自然收束。仅当用户明确要求 AI芝士派 栏目风格时使用 `ai-cheese-pie-v1`，并保留其固定结尾。

## `claim-ledger.json`

```json
{
  "schema_version": 1,
  "source_signal_id": "openai-product-event-date",
  "sources": [
    {
      "id": "src-01",
      "url": "https://example.com/original",
      "source_name": "Original publisher",
      "supports_cn": "它实际证明的事实。",
      "verification": "verified",
      "from_radar": true
    },
    {
      "id": "src-02",
      "url": "https://example.com/workflow-observation",
      "source_name": "Independent workflow test",
      "supports_cn": "记录旧流程步骤以及在同任务中观察到的交接变化。",
      "verification": "reported",
      "from_radar": false
    }
  ],
  "claims": [
    {
      "id": "claim-01",
      "text_cn": "产品已支持连续读取多份材料并给出带来源的初稿。",
      "kind": "fact",
      "source_ids": ["src-01"],
      "boundary_cn": "适用范围或仍未知部分。",
      "recheck_before_production": true
    },
    {
      "id": "claim-02",
      "text_cn": "旧流程通常包含分别搜索、复制、去重与结构整理。",
      "kind": "observation",
      "source_ids": ["src-02"],
      "boundary_cn": "不同团队的具体步骤会有差异。",
      "recheck_before_production": false
    },
    {
      "id": "claim-03",
      "text_cn": "可把流程调整为人定标准、AI整理、人核验。",
      "kind": "inference",
      "source_ids": ["src-01", "src-02"],
      "boundary_cn": "这是基于能力与小范围工作流测试的编辑建议，不是通用效率结论。",
      "recheck_before_production": true
    },
    {
      "id": "claim-04",
      "text_cn": "当前更适合用非敏感资料做小范围试用。",
      "kind": "inference",
      "source_ids": ["src-01", "src-02"],
      "boundary_cn": "敏感数据政策、稳定性与引用完整度仍需按环境核验。",
      "recheck_before_production": true
    }
  ]
}
```

`kind` 可用 `fact`、`number`、`quote`、`observation` 或 `inference`。推断必须写 `boundary_cn`。工作流收益没有同任务实测时，用 inference 或 observation 并清楚限定，不能写成确定事实。

`from_radar: true` 的 URL 必须存在于 `selected-signal.json`；写稿时新增来源标为 false。

## 验证与注册

```bash
python3 <skill-dir>/scripts/validate_script_package.py \
  <story-dir>/script-package.json \
  <story-dir>/claim-ledger.json \
  --selected <story-dir>/selected-signal.json
```

状态脚本注册时会再次验证，生成 `script.md` 与 `script.txt`，并把 package、claim ledger、可读稿和纯口播一起封入哈希。不要直接修改已注册的 `script.md` 或 `script.txt`；修改 package 后重新验证、注册与展示。

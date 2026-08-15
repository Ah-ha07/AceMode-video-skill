# 生产前来源复核契约

稿件确认后、视频制作前，重新打开所有 `recheck_before_production: true` 的 claim 所引用来源，并保存 `source-recheck.json`：

```json
{
  "schema_version": 1,
  "source_signal_id": "openai-product-event-date",
  "checks": [
    {
      "claim_id": "claim-01",
      "source_ids": ["src-01", "src-02"],
      "checked_at": "2026-08-12T10:00:00Z",
      "result": "unchanged",
      "notes_cn": "官方页面与独立实测仍支持原稿；定价地区限制未变化。"
    }
  ]
}
```

每个需要复核的 claim 恰好出现一次，`source_ids` 至少覆盖该 claim 的全部来源，`notes_cn` 写实际检查内容。`result` 只能是 `unchanged` 或 `material-change`。任一 claim 有实质变化，整体状态会自动退回 `SCRIPT_DRAFT`；不能用一条泛泛的没变化代替逐项复核。

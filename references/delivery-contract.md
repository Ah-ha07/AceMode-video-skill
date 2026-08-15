# 交付规格契约

`delivery-spec.json` 是视频生产前的冻结单。它解决的不是文件格式问题，而是防止团队做到一半才发现语言、时长、画幅、声音、品牌或发布用途理解不一致。

至少记录：

- `story_id`、BCP-47 `language`、`target_duration_seconds`；
- `delivery_scope`: `internal` 或 `public`；
- 每个 profile 的画幅、宽高和原生 Remotion composition；
- 已确认的 TTS provider、voice ID、确认依据与 receipt；
- 必须开启的 TTS-timed captions 及最大行数；
- `opaque-cut` 或有明确设计理由的 `designed-overlap`；
- 品牌是否开启及确认 receipt；
- Visual Director 方向确认 receipt。

随包 `assets/remotion-template/delivery-spec.json` 是起点。填写后运行：

```bash
python3 <skill-dir>/scripts/validate_delivery_spec.py \
  <video-dir>/delivery-spec.json \
  --story-id <story-id> \
  --story-file <video-dir>/src/story.json \
  --review-manifest <video-dir>/qa/review-package.json \
  --voice-manifest <video-dir>/audio/tts-manifest.json \
  --caption-manifest <video-dir>/src/captions.json \
  --source-ledger <video-dir>/source-ledger.json
```

`public` 会把未清权、需替换或未知权利素材作为错误；`internal` 可以保留这些素材用于团队审片，但会给出 blocker 警告，最终只能走 `complete-internal`。改变 delivery spec 的任何实质字段都要重新登记审片包并取得完整渲染确认。

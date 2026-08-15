# 最终视频 QA 契约

完整渲染后先人工保存 `visual-review.json`：

```json
{
  "schema_version": 1,
  "reviewer": "reviewer name or agent role",
  "reviewed_at": "2026-08-12T12:00:00Z",
  "opening_reviewed": true,
  "transitions_reviewed": true,
  "final_frame_reviewed": true,
  "captions_reviewed": true,
  "caption_timing_reviewed": true,
  "audio_gaps_reviewed": true,
  "transition_midpoints_reviewed": true,
  "safe_areas_reviewed": true,
  "rights_attributions_reviewed": true,
  "notes": "检查了封面、转场中点、字幕与结尾署名。"
}
```

然后运行：

```bash
python3 <skill-dir>/scripts/verify_final_video.py \
  <final-video.mp4> <video-dir>/src/story.json <video-dir>/source-ledger.json \
  --story-id <story-id> \
  --scope public \
  --visual-review <video-dir>/qa/visual-review.json \
  --output <video-dir>/qa/final-delivery.json
```

公开版使用 `--scope public`，内部审片版使用 `--scope internal`。两者都重新执行普通 story 验证、FFprobe 流/尺寸/时长核对、FFmpeg 全片解码，并要求最终文件同时有视频与音频；脚本还记录超过 0.8 秒的静音、超过 0.25 秒的近黑场和响度测量。内部版允许 publication validation 标为 `blocked`，但不得被描述为公开可用。

随后生成 `cost-manifest.json`。`newsroom_state.py complete` 或 `complete-internal` 会再次调用验证器并覆盖 QA 报告，同时校验成本清单，因此伪造 passed JSON 不能完成登记。

# 成本与用量记录

一条视频的成本由四部分组成：模型推理、联网/素材服务、TTS、以及本地渲染机器时间。Remotion 和 FFmpeg 本地渲染本身不消耗 LLM token；Codex 在研究、写稿、编码和审查时才消耗模型 token。

不要根据对话长度自行估算真实 token 或金额。只有宿主/API 返回 usage 时，才记录 input、cached input、output 和 reasoning token；看不到 usage 时写清 unavailable 原因。TTS 记录 provider、voice ID、实测秒数和段数；渲染记录成片秒数、帧数与 wall time。

```bash
python3 <skill-dir>/scripts/build_cost_manifest.py \
  --output <video-dir>/qa/cost-manifest.json \
  --model-provider openai --model <actual-model> \
  --tokens-unavailable-reason "宿主未暴露本任务 usage" \
  --script <story-dir>/script.txt \
  --tts-manifest <video-dir>/audio/tts-manifest.json \
  --render <video-dir>/renders/final.mp4 \
  --render-frames <actual-frames> \
  --render-wall-seconds <measured-seconds>
```

若宿主给出精确 usage，用 `--input-tokens`、`--cached-input-tokens`、`--output-tokens` 和可选 `--reasoning-output-tokens` 替代 unavailable 参数。API 单价和套餐经常变化，金额应在项目外按当时供应商账单计算，不写死在 Skill 里。

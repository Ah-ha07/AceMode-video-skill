# 旁白同步字幕契约

字幕是口播的时间索引，不是 scene 的装饰性标签。唯一可信时间源是最终 TTS manifest；稿件、声音或语速变化后必须重新生成字幕。

```bash
python3 <skill-dir>/scripts/caption_pipeline.py generate \
  <video-dir>/audio/tts-manifest.json \
  --language en-US \
  --max-words 9 --max-chars 52 \
  --output <video-dir>/src/captions.json
```

生成器保留品牌名、缩写和原文大小写，只把句子分成移动端可读短语。每个 cue 必须有整数 `startMs` / `endMs`，不能重叠，至少 350ms，不超过两行移动端预算；TTS manifest 应明确 `timingUnit: seconds|milliseconds`。字幕清单必须记录源 voice manifest 的 SHA-256。

Remotion 在所有 scene 之外只渲染一套 `TimedCaptions`。字幕安全区独立于标题、人物和证据卡；9:16 的底部要为平台 UI 留出更大空间。最终人工 QA 要同时确认文本正确、切换时间贴合旁白、没有 scene 边界双字幕、最后一句没有被截断。

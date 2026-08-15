# AceMode Newsroom

把最近 72 小时的 AI / 科技热点，转化为普通人能理解、能判断、能行动的生产力内容，并完成选题、稿件确认、声音试音、视觉导演、Remotion 审片和最终视频交付。

AceMode 的核心不是播报模型名称和参数，而是回答：这条新闻会改变谁的哪项工作，原来怎么做，现在 AI 改变哪一步，人的责任还剩什么，以及它现在能用还是仍属于趋势。

## 主要能力

- 冻结热点榜单与选题序号，跨轮次保留项目状态。
- 从具体工作场景切入，生成带事实账本的 AceMode 英文或中文稿件。
- 分别确认完整稿件、TTS 声音、Visual Director 方向与最终审片包。
- 原生支持 16:9 `EditorialDocumentary` 与 9:16 `VerticalNewsroom`，不使用横版裁切冒充竖版。
- 根据最终 TTS 时间戳生成全局旁白同步字幕。
- 自动生成封面、前三秒预览、关键帧板和逐切点转场检查。
- 区分内部审片版和公开发布版，保留素材权利与署名边界。
- 记录 LLM token、TTS 用量和本地渲染时间；宿主没有真实 usage 时明确标记 unavailable。

## 安装

```bash
git clone https://github.com/Ah-ha07/AceMode-video-skill.git \
  ~/.codex/skills/acemode-newsroom
```

重新打开 Codex 或 Cursor 后，可以这样开始：

```text
使用 $acemode-newsroom 查找最近 72 小时最值得普通人关注的 AI 热点。
```

也可以直接说：

```text
先列出今天会改变普通人工作流的 AI 新闻，我选好后再写稿和做视频。
```

## 运行环境

热点阶段需要联网搜索。视频阶段需要 Python、Node.js、npm、FFmpeg、FFprobe、项目本地 Remotion CLI 和 Chrome/Chromium。默认火山引擎 TTS 需要相应账号、凭证与 voice ID 权限。

```bash
python3 scripts/preflight.py --stage video --with-tts \
  --video-project <video-project> \
  --browser-executable <chrome-or-chromium>
```

完整工作流、确认门和失败处理以 [SKILL.md](SKILL.md) 为准。

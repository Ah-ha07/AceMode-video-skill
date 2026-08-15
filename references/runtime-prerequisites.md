# 运行环境与分发边界

这个 Skill 的代码、模板和编辑参考资料是自包含的，但运行环境不是零依赖。热点雷达需要联网搜索；视频阶段需要本地 Node.js、npm、FFmpeg、FFprobe 和 Remotion 依赖；默认 TTS 需要火山引擎账号与对应声音权限。

## 预检

只检查本地命令：

```bash
python3 <skill-dir>/scripts/preflight.py --stage video
```

同时检查默认 TTS 凭证：

```bash
python3 <skill-dir>/scripts/preflight.py --stage video --with-tts \
  --video-project <video-dir> \
  --browser-executable <existing-chrome-or-chromium>
```

凭证可放在环境变量 `VOLCANO_APP_ID`、`VOLCANO_ACCESS_TOKEN`，或 macOS Keychain 服务 `codex-volcano-app-id`、`codex-volcano-access-token`。预检只报告是否可用，不输出凭证内容。

## Remotion 安装

scaffold 后在视频项目目录运行 `npm ci`，严格使用随包 `package-lock.json`。`build_review_package.py` 只接受项目本地的 `node_modules/.bin/remotion`，不会通过裸 `npx` 临时下载未知版本。Remotion 插件只提供知识/操作能力，不等于项目 npm 依赖；本地 CLI 也不等于 Chromium 已安装。预检会把这三层分别报告。只有明确允许联网下载浏览器时才使用 `--allow-browser-download`。

## 画幅能力

随包 Remotion 模板包含独立的 16:9 `EditorialDocumentary` 与 9:16 `VerticalNewsroom`。二者共享事实、音频和字幕时间，但不共享完成版几何。需要其他画幅时，依据 `aspect-ratio-directing.md` 新建原生 composition、story 和审片包；不能只改宽高、缩放或裁切另一版。

## 声音边界

默认声音不可用时，停下来说明缺少什么。换成其他 TTS、系统声音或用户录音会改变声音身份，必须得到用户确认；新音频会使旧预览与完整渲染确认失效。`synthesize_volcano_dayi.mjs --help` 不需要凭证。

## 对外分发

公开发布到 GitHub 或应用商店前，维护者需要确认自己有权分发所复制或改写的品牌资料、模板和参考文本，并为仓库补充适合的 LICENSE 与第三方依赖声明。npm 依赖仍遵循各自许可证。本 Skill 不会替发布者自动授予 AceMode 商标、wordmark 或第三方素材的使用权。

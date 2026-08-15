# 从定稿到视频的交接

只在故事状态为 `SCRIPT_APPROVED` 后进入。口播唯一输入是 story 目录中的 `script.txt`，事实边界来自 `claim-ledger.json`，工作流叙事来自 `script-package.json` 的 `productivity_frame`。不要从聊天消息重新抄稿，也不要用新事实偷偷改镜头结论。

## 生产前复核与项目环境

逐项重开所有 `recheck_before_production: true` 的来源，按 `source-recheck-contract.md` 保存 `source-recheck.json` 并运行 `recheck --manifest`。任一结果为 `material-change` 会退回修稿；全部为 `unchanged` 才能继续。

在 story 目录建立项目：

```bash
python3 <skill-dir>/scripts/scaffold_project.py <story-dir>/video --install
python3 <skill-dir>/scripts/preflight.py --stage video --with-tts \
  --video-project <story-dir>/video \
  --browser-executable <existing-chrome-or-chromium>
```

Cursor/Codex 的 Remotion 插件、npm 包、项目本地 CLI 和 Chromium 是四个不同层次；插件存在不代表项目依赖和浏览器已就绪。只使用 `package-lock.json` 和项目本地 `node_modules/.bin/remotion`。

## 锁定交付规格

先复制并填写随包 `delivery-spec.json`，读取 `delivery-contract.md`。一次锁定语言、目标时长、`internal`/`public`、所有画幅与原生 composition、声音确认依据、字幕、转场、品牌和导演确认凭证，后续不能静默漂移。

随包提供两个独立的 30fps 几何基线：`EditorialDocumentary`（1920×1080）和 `VerticalNewsroom`（1080×1920）。示例 story 只是结构演示；实际总帧数以最终 TTS 实测时长为准。多画幅读取 `aspect-ratio-directing.md`，分别导演与审片；不能直接改另一版尺寸、裁切或缩放完成版。

## Visual Director

来源复核后、逐镜 scene plan 前读取 `visual-director.md`。保存 `director-treatment.md`、一张 concept board 和至少三张关键风格帧，明确观众记忆、情绪曲线、视觉母题、色彩角色、镜头因果和拒绝规则。先展示给用户确认；未确认时不扩写完整 storyboard。

确认后运行：

```bash
python3 <skill-dir>/scripts/validate_director_pack.py \
  --treatment <video-dir>/director/director-treatment.md \
  --board <video-dir>/director/concept-board.png \
  --frame <video-dir>/director/style-frame-01.png \
  --frame <video-dir>/director/style-frame-02.png \
  --frame <video-dir>/director/style-frame-03.png
```

镜头优先证明同一任务的旧流程、AI 改变点、新流程和人工检查点。没有同任务实测时，用步骤和可观察产物表达，不制作虚假百分比、计时器或倍数动画。

## 证据、声音与字幕

把 claim ledger 转成 `research.md` 的事实脊柱，再建立 `source-ledger.json`；读取 `research-and-rights.md`。人物故事读取 `person-led-story.md`，抠图或规范化读取 `asset-preprocessing.md`。直接证据不可用时标记 context 或 illustrative，不生成冒充真实人物、产品界面或事件的画面。

先用正文 1–2 句制作 2–3 个短试音，用 `voice_audition.py create` 建清单；用户听后用 `voice_audition.py approve` 记录选择。中文可把火山引擎大壹 2.0 作为候选；英文必须使用明确支持英文且试听通过的 voice ID。获批候选的 `provider + voice_id` 必须与 delivery spec 和最终 TTS manifest 一致，不可静默换声。

完整火山 TTS 示例：

```bash
node <skill-dir>/scripts/synthesize_volcano_dayi.mjs \
  --input <story-dir>/script.txt \
  --output <video-dir>/public/audio/voiceover.wav \
  --manifest <video-dir>/audio/tts-manifest.json
```

TTS manifest 是字幕时间唯一来源：

```bash
python3 <skill-dir>/scripts/caption_pipeline.py generate \
  <video-dir>/audio/tts-manifest.json \
  --language <BCP-47-language> \
  --output <video-dir>/src/captions.json
```

Remotion 必须在最外层渲染一套全局 timed captions。相邻 scene 的静态 `caption` 字段不能作为旁白字幕源，否则 scene overlap 会产生双字幕，也无法逐句对齐。

## Scene、预览与转场检查

场景通常 4–8 秒，每个 beat 只有一个传播任务。读取 `story-schema.md`、`style-grammar.md`、`emotion-motion-curve.md` 和 `opening-and-evidence-motion.md`。frame 0 是封面；1.5 秒内出现任务证据；3 秒内落下第一个工作回报。AceMode 内容声音不自动等于 AceMode 发布者品牌，品牌开启必须单独确认。

先验证 story，再分别生成审片包和逐切点检查：

```bash
python3 <skill-dir>/scripts/validate_story.py \
  <video-dir>/src/story.json <video-dir>/source-ledger.json

python3 <skill-dir>/scripts/build_review_package.py <video-dir> \
  --story src/story.json --composition EditorialDocumentary

python3 <skill-dir>/scripts/build_transition_review.py <video-dir> \
  --story src/story.json --composition EditorialDocumentary
```

转场检查为每个 scene boundary 生成切前、切点、切后三帧，专门排除双标题、旧字幕残留、透明叠层和切点黑帧。脚本初次只写 `status: ready`；实际看完转场板后再登记审阅，不能把生成图片等同于检查通过：

```bash
python3 <skill-dir>/scripts/build_transition_review.py \
  --approve-manifest <video-dir>/qa/transition-review.json \
  --review-receipt <current-review-turn-id> \
  --reviewer <reviewer-name>
```

## 登记审片包

`mark-preview` 要把影响用户判断与最终渲染的产物都显式登记：

```bash
python3 <skill-dir>/scripts/newsroom_state.py mark-preview \
  <project-dir> <story-id> \
  --scene-plan <video-dir>/scene-plan.json \
  --delivery-spec <video-dir>/delivery-spec.json \
  --source-ledger <video-dir>/source-ledger.json \
  --voice-manifest <video-dir>/audio/tts-manifest.json \
  --caption-manifest <video-dir>/src/captions.json \
  --voice-audition <video-dir>/audio/voice-audition.json \
  --director-treatment <video-dir>/director/director-treatment.md \
  --director-board <video-dir>/director/concept-board.png \
  --director-frame <video-dir>/director/style-frame-01.png \
  --director-frame <video-dir>/director/style-frame-02.png \
  --director-frame <video-dir>/director/style-frame-03.png \
  --review-manifest <video-dir>/qa/review-package.json \
  --transition-review <video-dir>/qa/transition-review.json \
  --transition-board <video-dir>/qa/transition-board.png \
  --story-file <video-dir>/src/story.json \
  --remotion-src-dir <video-dir>/src \
  --render-config <video-dir>/package.json \
  --render-config <video-dir>/package-lock.json \
  --asset <video-dir>/public/audio/voiceover.wav \
  --asset <video-dir>/public/assets/primary.jpg \
  --cover <video-dir>/qa/cover-frame.png \
  --opening <video-dir>/qa/opening-preview.mp4 \
  --board <video-dir>/qa/review-board.png
```

多画幅时，按同一顺序为每个 profile 重复 review manifest、transition review/board、story、cover、opening 和 board。命令会交叉核对 delivery spec、声音、字幕来源哈希、scene plan、story、review 和 transition manifest，并冻结完整 Remotion `src/` 树与锁定配置。

向用户展示每个画幅的封面、带声音开场、代表帧板、转场板、实测时长、目标误差和 publication blockers，再用 `present-preview --receipt ...` 记录当前审片包展示，等待独立的完整渲染确认。

## 完整渲染与交付

只有 `RENDER_APPROVED` 才能渲染整片。Remotion 默认使用 `--log=error`，调试时才开 verbose，避免构建噪声占用模型上下文。读取 `final-qa-contract.md`、`cost-and-usage.md` 与 `qa-gates.md`，保存 `visual-review.json` 和 `cost-manifest.json`。

公开版使用 `complete`，必须通过 publication 验证；仅团队审阅且仍有素材替换项时使用 `complete-internal`。两者都要求真实音视频流、完整解码、字幕/转场人工复核和成本清单，不能靠伪造 passed JSON 跳过。

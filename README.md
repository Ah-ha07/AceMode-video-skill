# Editorial Documentary Video Skill

一个面向 Codex / Agent 工作流的编辑型纪录片视频技能。它把事实研究、旁白锁定、词级时间轴、素材权利台账、镜头导演表、Remotion 动效和发布前 QA 串成一条可复现的生产流程。

适合 45 秒到 6 分钟的科技、商业、人物、历史、体育和新闻叙事。它不是通用幻灯片模板：旁白时间是唯一节拍源，画面必须承担证据、解释或情绪推进中的至少一种职责。

## 核心能力

- 16:9、9:16 和多比例的原生导演，不做简单裁切转换
- 封面即第 0 帧，前三秒完成封面到故事的转换和证据揭示
- 锁定旁白后测量真实时长，并使用词级时间戳驱动中文字幕
- 用 `scene-plan.json` 管理镜头任务、能量、布局、运动和素材对应关系
- 用 `source-ledger.json` 分离本地剪辑许可与公开发布许可
- 提供可复用的 Remotion 模板、项目脚手架、审片包和发布校验脚本
- 在完整渲染前强制经过封面、三秒预览和关键帧板审阅

## 安装

将仓库克隆到 Codex 技能目录：

```bash
git clone https://github.com/Ah-ha07/editorial-documentary-video-skill.git \
  ~/.codex/skills/editorial-documentary-video
```

重新打开 Codex 会话后，可通过技能名 `editorial-documentary-video` 使用。

## 目录

```text
SKILL.md                         技能主规范
agents/openai.yaml               Agent 元数据
references/                      导演、版权、比例与 QA 参考规范
scripts/scaffold_project.py      创建 Remotion 项目
scripts/build_review_package.py  生成审片包
scripts/validate_story.py        校验故事和发布权利
scripts/synthesize_volcano_dayi.mjs  分段生成默认中文旁白
assets/remotion-template/        数据驱动的 Remotion 模板
```

## 最短工作流

1. 研究事实并锁定 `script.txt`。
2. 生成或录制旁白，测量真实时长并获得词级时间戳。
3. 完成 `scene-plan.json` 和 `source-ledger.json`。
4. 创建项目并放入旁白和已登记素材。
5. 运行故事校验，生成封面、三秒预览和关键帧审片板。
6. 用户明确确认后才渲染完整视频，并执行最终媒体 QA。

```bash
python scripts/scaffold_project.py videos/my-story

python scripts/validate_story.py \
  videos/my-story/src/story.json \
  videos/my-story/source-ledger.json

python scripts/build_review_package.py videos/my-story
```

公开发布前还应运行严格权利校验：

```bash
python scripts/validate_story.py \
  videos/my-story/src/story.json \
  videos/my-story/source-ledger.json \
  --publication
```

完整的质量规则、失败模式和交付契约以 [SKILL.md](SKILL.md) 为准。

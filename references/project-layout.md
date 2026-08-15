# 项目目录与续接规则

## 默认目录

在用户当前工作区创建：

```text
newsroom/YYYY-MM-DD/HHMM-topic-slug/
├── project.json
├── radar/
│   ├── candidates.json
│   ├── signals.json
│   └── brief.md
└── stories/
    └── 01-signal-id/
        ├── selected-signal.json
        ├── script-package.json
        ├── claim-ledger.json
        ├── script.md
        ├── script.txt
        └── video/
            ├── delivery-spec.json
            ├── research.md
            ├── scene-plan.json
            ├── source-ledger.json
            ├── director/
            │   ├── director-treatment.md
            │   ├── concept-board.png
            │   └── style-frame-*.png
            ├── audio/          # TTS manifest + voice audition
            ├── public/
            ├── src/            # stories + global timed captions
            ├── qa/             # review, transition, final QA, cost
            └── renders/
```

每次新的热点扫描创建新的带时间目录，不覆盖旧榜单。榜单序号绑定这个快照：用户说第 1 个时，读取保存的 `radar/signals.json` 中 `rank: 1` 的项目，不能重新搜索后拿新榜单的第一名替换。

## 跨轮续接

优先使用当前对话里已经展示过的 `project.json`。没有明确路径时，在当前工作区搜索 `newsroom/**/project.json`：只有一个未完成项目时可续接；有多个合理候选时列出项目标题、更新时间和状态，让用户选择。不要依赖聊天记忆猜测当前稿件版本。

进入任何阶段前先运行：

```bash
python3 <skill-dir>/scripts/newsroom_state.py status <project-dir>
```

确认输出中的 `integrity.ok` 为 true。状态命令会复核榜单快照、选题快照、稿件展示版/口播版、审片输入输出及最终成片/QA 报告的哈希；发现缺失或漂移时先恢复或重新登记。

多选题相互独立。第 1 条的稿件确认不得解锁第 2 条的视频；每个 story 都有自己的状态、哈希和确认记录。

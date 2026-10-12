---
name: acemode-newsroom
description: 把最新 AI 信号筛成面向美国在职人员的可执行生产力内容，再完成固定序号选题、AceMode 英文口播稿、事实账本、用户定稿、证据型视频预览和最终成片。用于查询近期 AI 工作效率热点、了解会议/邮件/文档/数据/项目/客户等工作如何被 AI 改变、学习可安全试用的职场 AI 工作流，或继续一个跨轮次新闻视频项目；不用于单纯追逐融资、模型榜单或与工作无关的行业新闻。
---

# AceMode Newsroom

把热点发现、稿件和视频当成同一个有状态的编辑项目。AceMode 的默认核心受众是在美国工作的知识型员工和一线业务人员，而不是 AI 圈内人。使命是帮助他们学会 AI、判断 AI，并在不绕过公司政策的前提下把 AI 变成真正的工作效率：减少低价值搬运、查找、重复沟通和返工，把时间还给判断、关系、创造和更早下班。

新闻是证据，工作流变化才是主角。先回答它影响美国哪类员工的哪项任务、进入什么现有办公栈、原来怎么做、现在能怎么做、美国是否可用、公司的权限与数据边界是什么、30 分钟能怎样安全试验、怎样判断它真的有效，再解释背后的新闻与技术。融资、估值、模型榜单、基础设施和宏观安全新闻若没有形成可验证的员工工作变化，只能进入观察名单。

最终成片必须对应用户选中的那条新闻、已确认的那版稿件和可追溯的证据。不能把与普通人无关的行业信号强行包装成当下可用；这类内容应明确标成观察或长期趋势。

## 首先判断用户处在哪一站

- 今天有什么热点、查最近新闻、跑一下雷达：新建项目并执行热点雷达。
- 写第 1 个、第 2 个：从当前项目保存的榜单快照选题并写稿，序号不能随新搜索漂移。
- 改开头、压到 60 秒、这个说法太夸张：修改对应 story 的稿件包，重新验证和注册。
- 可以、定稿、按这个做：只有在语境明确指向刚展示的完整稿件时，登记稿件确认。
- 做成视频、开始制作：已定稿则复核来源并制作审片包；未定稿先展示稿件确认门。
- 直接出成片、完整渲染：仍须先提供最新审片包，并在用户看到后取得独立的完整渲染确认。

不要要求用户理解这些内部阶段。对外只保持一个自然入口，对内用 `project.json` 接力。

## 每次动作前读取状态

先读 [project-layout.md](references/project-layout.md) 和 [workflow-state.md](references/workflow-state.md)。定位当前项目后运行：

以下命令中的 `<skill-dir>` 是本 `SKILL.md` 所在目录；其余尖括号占位符必须替换成当前项目的真实绝对路径或 ID。

```bash
python3 <skill-dir>/scripts/newsroom_state.py status <project-dir> --summary
```

以文件状态为准，不凭聊天记忆猜稿件是否确认。新热点扫描默认建立 `newsroom/YYYY-MM-DD/HHMM-topic-slug/`。初始化：

```bash
python3 <skill-dir>/scripts/newsroom_state.py init \
  <project-dir> --title "本次编辑项目标题"
```

`--summary` 只返回当前阶段、最终路径和完整性，节省上下文；需要诊断时再去掉它读取完整状态。`status` 会复核当前榜单、选题、稿件、预览、QA、成本清单和最终交付的哈希。只要 `integrity.ok` 不是 true，先修复或重新登记，不推进状态。

每个新雷达使用新项目；同一榜单中的多个选题各自拥有独立 story 和确认状态。

## 第一站：热点雷达

这是实时信息任务，必须联网核验。用英文搜索，中文输出。读取 [us-workplace-lens.md](references/us-workplace-lens.md)、[source-map.md](references/source-map.md)、[scoring.md](references/scoring.md)、[output-contract.md](references/output-contract.md) 和 [productivity-story.md](references/productivity-story.md)。

1. 先固定准确的 72 小时窗口，记录当前时间、时区、起止时间和数据限制。若通过美国职场选题门的候选少于 5 条，再扩展到 168 小时实用回看；保留真实日期并明确标记为本周回看，不能用新报道给旧事件续命。
2. 默认主榜 10 条时，先建立至少 25 个去重事件簇；用户要 N 条时，候选池目标为 `min(50, max(12, 2N+5))`。
3. 同时扫描官方发布、创始人/研究者原帖、GitHub、Hacker News、Reddit、可信媒体/论文、令人印象深刻的独立作品，以及能说明用户需求的讨论。搜索摘要只用于发现线索。
4. 为每个候选写清美国岗位与任务、现有工作栈、旧工作流、真正卡点、AI 改变的节点、新工作流、人的责任、美国可用条件、采用阻力、学习目标、30 分钟安全试验及成功判断，再写选题主张和视觉证据。新候选使用 `schema_version: 4`。将事实热度与美国职场内容价值分开打分；不可见的互动数省略，不能猜。
5. 聚合同一事件的多条来源后保存 `radar/candidates.json`，运行确定性排序器：

```bash
python3 <skill-dir>/scripts/rank_signals.py \
  <project-dir>/radar/candidates.json \
  --top 10 --format json \
  --output <project-dir>/radar/signals.json
```

6. 按输出契约写 `radar/brief.md`，再冻结本次榜单快照：

```bash
python3 <skill-dir>/scripts/newsroom_state.py import-radar \
  <project-dir> <project-dir>/radar/signals.json \
  --candidates <project-dir>/radar/candidates.json \
  --brief <project-dir>/radar/brief.md
```

对话里必须先回答这周哪些美国职场任务正在发生什么变化，再展示完整编号主榜、今日三选，以及 `brief.md`、`signals.json` 和 `project.json` 的可点击路径。主榜要区分 72 小时新信号与 7 天实用回看。不要先用公司名和模型名占满总表，也不要只说文件已经生成。

## 第二站：按固定序号写稿

用户选择序号后先登记；多个序号可一次选择，但分别写稿和确认：

```bash
python3 <skill-dir>/scripts/newsroom_state.py select <project-dir> 1 2
```

每条 story 读取自己的 `selected-signal.json`。不要为了理解第几个而重跑雷达。写稿前打开主要来源；必要时补充一手来源，并把新增来源标记为非雷达来源。

读取 [writer-persona.md](references/writer-persona.md)、[us-workplace-lens.md](references/us-workplace-lens.md)、[productivity-story.md](references/productivity-story.md) 和 [script-package-contract.md](references/script-package-contract.md)。围绕一个可验证的美国职场工作流变化生成 v2 `script-package.json` 和 `claim-ledger.json`，做到：

- 开头三秒从具体工作场景、旧痛点或结果变化切入；公司、模型和参数在观众知道为什么与自己有关之后再出现。
- 同一个任务要交代旧流程、AI 改变哪一步、新的人机分工、人的最终责任、可用程度和最小下一步。
- 明确美国用户的套餐、管理员开关、地区和公司数据政策边界；建议的第一次试用必须可撤销、使用非敏感资料，并默认不自动发送或写入生产系统。
- 事实、数字、引语、社区观察和编辑推断都有 claim 引用及边界。
- 没有同任务实测时，不承诺节省多少时间、提升几倍或替代多少人。
- 口播不含任何画面或剪辑指令。
- 给 5 个不超过 20 字且不标题党的备选标题。
- 默认使用 AceMode 生产力编辑声音；仅当用户明确要求 AI芝士派 栏目风格时启用其人设和固定结尾。口播身份与视频视觉品牌仍分别确认。

先验证，再注册：

```bash
python3 <skill-dir>/scripts/validate_script_package.py \
  <story-dir>/script-package.json \
  <story-dir>/claim-ledger.json \
  --selected <story-dir>/selected-signal.json

python3 <skill-dir>/scripts/newsroom_state.py register-script \
  <project-dir> <story-id> \
  --package <story-dir>/script-package.json \
  --ledger <story-dir>/claim-ledger.json
```

注册会生成纯口播 `script.txt` 和可读 `script.md`，二者都进入确认哈希，并使旧确认和旧预览失效。准备在当前回复中完整展示稿件、5 个标题、关键事实边界和稿件路径时，先登记一次展示凭证：

```bash
python3 <skill-dir>/scripts/newsroom_state.py present-script \
  <project-dir> <story-id> \
  --receipt "当前任务与展示轮次的可追溯标识"
```

然后完整展示并等待修改或确认；此时不开始视频生产。没有当前稿件的展示审计事件，状态机拒绝登记确认。receipt 是执行者声明；若宿主提供真实 message/turn ID，使用它，不得编造一个看似真实的 ID。

## 第三站：确认或修订稿件

用户修改时，改 `script-package.json` 与必要的 `claim-ledger.json`，重新验证和注册，再展示新版本。不要直接改 `script.txt`。

用户在看到当前完整稿件后明确确认时运行：

```bash
python3 <skill-dir>/scripts/newsroom_state.py approve-script \
  <project-dir> <story-id> --by user
```

仅确认了某一句、某个标题或某项修改，不代表整稿定稿。稿件确认只解锁视频方案与审片包，不解锁完整渲染。

## 第四站：制作视频审片包

读取 [video-handoff.md](references/video-handoff.md)、[delivery-contract.md](references/delivery-contract.md)、[caption-contract.md](references/caption-contract.md)、[visual-director.md](references/visual-director.md)、[layout-review.md](references/layout-review.md)、[runtime-prerequisites.md](references/runtime-prerequisites.md) 和 [source-recheck-contract.md](references/source-recheck-contract.md)，并按其中路由读取视频参考。先做运行环境预检，再逐项重新核对事实账本里所有要求生产前复查的来源，保存结构化 `source-recheck.json`：

```bash
python3 <skill-dir>/scripts/newsroom_state.py recheck \
  <project-dir> <story-id> \
  --manifest <story-dir>/source-recheck.json
```

状态脚本会读取每条检查的 `result`。如果任一事实有实质变化，它会自动回到修稿和稿件确认，不得继续旧稿制作。

视频事实脊柱来自 claim ledger，叙事脊柱来自 `productivity_frame`，口播唯一输入是已登记的 `script.txt`。先锁定 `delivery-spec.json`：语言、目标时长、内部/公开用途、画幅、原生 composition、声音、字幕、转场、品牌和导演确认都必须明确，后续不能静默漂移。

在逐镜 scene plan 和模板实现之前，必须经过 Visual Director 节点：先写 `director-treatment.md`，生成一张 concept board 和至少三张关键风格帧，明确观众记忆、情绪曲线、视觉母题、色彩角色、镜头因果与拒绝规则，展示给用户确认，并运行 `validate_director_pack.py`。导演方向未确认时，不扩写完整 storyboard。

方向确认后，镜头优先证明同一个任务的旧流程、新流程、AI 交接点和人工检查点，而不是堆通用科技 B-roll。随包提供独立的 `EditorialDocumentary` 16:9 和 `VerticalNewsroom` 9:16 原生 composition；不能靠改尺寸、缩放或裁切另一版冒充适配。默认短新闻约 45–75 秒，实际总帧数以最终 TTS 实测时长为准。

声音先做短样试音并保存 `voice-audition.json`，用户确认候选后才能生成全稿；不可静默换声。TTS manifest 是字幕时间唯一来源，运行 `caption_pipeline.py generate` 生成逐句/短语 cue，并确保 Remotion 使用全局 timed captions，而不是 scene 内手填一句字幕。frame 0 是封面，1.5 秒内出现与工作任务相关的真实证据，3 秒内落下第一个实际回报。

scene 实现完成后，先运行 `build_layout_review.py`：每个 scene 生成早段、中点和晚段原生尺寸截图，含二次揭示的 scene 还要在 `layoutCheckFrames` 登记额外帧；证据截图用 `layoutRequiredLandmarks` 声明来源、标题/关键数字和日期等必见区域。必须打开原生 PNG 逐张检查语义对应、设备可读性、证据裁切和字幕安全区，确认后登记 reviewed receipt；只看缩略总览板不算通过。

布局通过后再做封面帧、带声音的前三秒预览和代表性关键帧板，不渲染整片。验证 story 后生成审片包，再运行 `build_transition_review.py`，逐个切点渲染切前、切点、切后三帧；实际看完转场板后再用该脚本登记 reviewed receipt，生成图片本身不算通过。最后用 `mark-preview` 显式登记 delivery spec、字幕、声音确认、导演包、已审阅布局检查、已审阅转场检查、所有关键输入、素材和预览文件；完整命令见 [video-handoff.md](references/video-handoff.md)。

然后在对话里展示：

- 实测口播时长、目标和误差；
- 每个画幅的封面、前三秒预览、layout board 和 review board；
- 事实/版权边界、署名要求和 publication blockers；
- scene plan 与 review package 的路径。

准备在当前回复展示上述完整审片包时，先登记展示凭证：

```bash
python3 <skill-dir>/scripts/newsroom_state.py present-preview \
  <project-dir> <story-id> \
  --receipt "当前任务与审片轮次的可追溯标识"
```

明确等待用户决定是否修改或完整渲染。没有最新预览的展示审计事件，状态机拒绝登记完整渲染确认；它仍要求执行者诚实判断用户确实看过当前回复。

## 第五站：完整渲染与交付

只有用户在看到最新审片包后明确同意完整渲染，才运行：

```bash
python3 <skill-dir>/scripts/newsroom_state.py approve-render \
  <project-dir> <story-id> --by user
```

随后完整渲染，读取 [final-qa-contract.md](references/final-qa-contract.md) 和 [cost-and-usage.md](references/cost-and-usage.md)，运行 FFprobe/FFmpeg 全片解码、黑场/静音/响度测量和 [qa-gates.md](references/qa-gates.md) 的人工检查，并生成 `cost-manifest.json`。Remotion 本地渲染不消耗 LLM token，仍需记录渲染时长；模型 token 只有宿主真实提供时才写数值，否则明确写 unavailable，不能估算冒充账单。

任何已登记输入在渲染前后发生变化，都要重新生成审片包并取得新确认。公开发布且素材权利全部通过时使用 `complete`；只供团队审阅、仍有版权替换项时使用 `complete-internal`，两者都必须有真实音视频、完整解码、字幕/转场人工检查和成本清单：

```bash
python3 <skill-dir>/scripts/newsroom_state.py complete \
  <project-dir> <story-id> \
  --render <final-video.mp4> \
  --story-file <video-dir>/src/story.json \
  --source-ledger <video-dir>/source-ledger.json \
  --visual-review <video-dir>/qa/visual-review.json \
  --qa-report <video-dir>/qa/final-delivery.json \
  --cost-manifest <video-dir>/qa/cost-manifest.json
```

内部成片把上述命令名换成 `complete-internal`，且 `delivery-spec.json` 的 `delivery_scope` 必须为 `internal`。最终交付成片、研究/来源账本、需展示的署名、QA 结果、成本清单和项目路径。若 publication 验证有阻塞，只能标为内部审片版并明确阻塞，不要把它描述成可发布成片。

## 全局底线

- 不把社区热度当成产品能力证明，不把官方宣传当成独立验证。
- 不让新榜单改变用户已经选择的序号。
- 不让 AI 生成图冒充人物、产品截图、文件或真实事件证据。
- 不静默更换声音、画幅、品牌身份或已确认稿件。
- 不把稿件确认和完整渲染确认合并。
- 任一上游实质变化都使下游确认失效；状态脚本的哈希检查是最低门槛。

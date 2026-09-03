# 原生尺寸布局检查

布局检查发生在 scene 实现完成之后、常规审片包和整片渲染之前。它解决的不是画面有没有出现，而是观众在目标设备上能不能看懂。缩略总览板只用来发现节奏和构图异常，不能代替打开原生尺寸单帧。

## 必查帧

每个 scene 至少生成三张 100% 原生分辨率截图：入场稳定后的早段、中点和离场前的晚段。scene 内部有二次揭示、布局切换或硬切时，在 story 顶层增加 `layoutCheckFrames`，登记切前、切点和切后等额外帧。

运行：

```bash
python3 <skill-dir>/scripts/build_layout_review.py <video-dir> \
  --story src/story.json \
  --composition <composition-id>
```

脚本输出：

- `qa/layout-review.json`：原生帧、文件哈希、scene、检查理由与必见地标；
- `qa/layout-frames/`：必须逐张打开的原生截图；
- `qa/layout-board.png`：只用于快速纵览，不能据此判断小字可读性。

## 四项检查

1. **语义对应**：当前画面证明当前旁白，不提前剧透下一句，也不拿装饰图冒充证据。
2. **设备可读**：标题、标签、数字和按钮在目标手机或桌面尺寸上无需放大即可辨认。文件像素足够不等于观众看得清。
3. **证据完整**：含来源截图的 scene 在 `layoutRequiredLandmarks` 声明必见地标，例如来源名称、承载主张的标题或数字、日期。所有地标必须同时留在裁切范围内；仅露出网页一角视为失败。
4. **安全区与遮挡**：字幕、平台 UI 安全区、品牌标记、证据和主视觉互不遮挡；长词、两行字幕、动效峰值时也不能溢出。

检查失败就回到布局实现，重新生成整套 layout review。不能沿用旧图、旧哈希或旧 receipt。

## 人工通过

生成图片只会得到 `status: ready`。实际打开总览板和所有原生截图后，才登记通过：

```bash
python3 <skill-dir>/scripts/build_layout_review.py \
  --approve-manifest <video-dir>/qa/layout-review.json \
  --review-receipt <current-review-turn-id> \
  --reviewer <reviewer-name>
```

批准时会重新校验 story、每张原生帧和总览板的哈希。`mark-preview` 强制要求一份已通过且与当前 story、composition、画幅匹配的 layout review，避免后续改了画面却继续使用旧检查结果。

# 内容格式与叙事

以 `docs/AUTHOR_GUIDE.md`、`schemas/v2/`、`packages/gal_protocol/lib/` 和运行代码为准，本参考不替代官方校验器。

## 身份与结构

`.chatgal` 是 ZIP，根层为 `manifest.json`、`home.png`、`characters/`、`stories/`、`events/`，不能套外层目录。JSONC 支持注释和尾逗号。禁止旧 `assets/`、`graph.json`；情景平放于 `stories/`，不用 `index.json`。

manifest 字段为 `packageId/version/name/author/description/variables`。packageId 使用字母数字、点、下划线、连字符，以字母数字开头且不含 `..`；version 是纯数字字符串。不要写旧的 `schemaVersion/engineCompatibility/entrypoints/assetIndex/homeBackground/characterVariables`，兼容报告在包外。

角色目录名 = character.json.id = 游戏名字。字段是 `id/prompt/states/emotions/defaultState/defaultEmotion`；每种状态×情绪都需 `<状态>_<情绪>.png`。基础人格内联，不能放 promptFile 或 portraits 映射。PNG 是当前资源契约，不凭文件能存进 ZIP 就认为 GIF/WebP/音视频可播放。

情景文件 stem 就是 id，入口固定 `start.json`。事件目录名就是事件 id 与控制台展示身份，文件里不再写 id/name。

## 人格、多角色与记忆

基础人格说明身份、口吻、关系起点、行为边界与连续性；当前地点和情境放 scenePrompt。不替玩家行动或捏造往事。动作可写在全角括号中。

一幕可有多个 `characters[]`，项为 `charId/state/emotion/scenePrompt`。在场角色形成该轮的记忆 audience；不在场角色不应知道私下对话。**首个角色**是离场结算取证角色，不拿第二位的私密记忆当证据。本幕 state 锁定服装/形态，模型可在此状态内换情绪；换服装应换幕声明。

## 情景字段

| 字段 | 用途 |
| --- | --- |
| displayName | 情景展示名，与 day 计数配合 |
| background | 相对于 stories/ 的背景文件名，可复用 |
| narration | 固定入场旁白，不是每回合随机开场 |
| atmosphere | 转场气氛；当前聊天页空值会跳过过场，旧 schema 的描述不完全准确 |
| characters | 出场列表与阶段人格 |
| fixedEffects | 入场 `{id,value}` 数值增减，非零且只作用注册的数值变量 |
| settlement | 每个受控变量独立的离场取证提示词和上限 |
| target | 有序出口条件块 |

采用天数时 day 默认0，每天第一幕入场+1。三幕日循环 `start→afternoon→night→start` 只在 start 加天数，夜晚不能提前变次日。聊天中的“明天到了”不触发真实换幕。

## 变量与离场结算

变量在 manifest.variables 唯一注册，字段 `id/type/default/min/max/enum/label/description`。声明层支持 int/number/bool/string/enum，但自动增减和 AI 结算只作用于 int/number；没有通用字符串赋值动作。属主按变量 id 的最长角色名前缀推导。

```json
{"var":"星澄好感","prompt":"愿意主动陪伴或分享且有具体举动时增加；明确抗拒疏远时减少；无证据保持不变。","maxAbsDelta":2,"onNoEvidence":"zero"}
```

一条只判断一个变量，上限写 maxAbsDelta，不在提示词另设一套。zero 无证据保持值，abort 缺少结果拒绝离场。结算后再判出口；最终按注册上下界夹取，重试幂等由引擎处理。不要用旧 judgePrompt/vars 顶层字段。

## 出口、条件与概率

```json
"target":[
 {"require":"\"day\" >= 3 & \"星澄好感\" >= 60","kind":[{"kind":"event","to":"小小约定"}]},
 {"kind":[{"kind":"story","to":"night"},{"kind":"story","to":"detour"}]}
]
```

从上到下首个成立块锁定，块内等概率。重复目标可表达比例，不存在 weight。目的地为 story/event/appShell，回主页用 appShell/home。没有出口合法但停在原处，只有有意设计时保留，否则补保底并检查可达性。

require 用中缀文本：变量名加双引号，数字直接写。支持比较 `> < >= <= == !=`、逻辑 `& | !`、算术 `+ -` 和括号。引号里一律是变量名，不是字符串字面量；不能把 `"路线" == "海边"` 右侧当文本常量。更复杂行为以当前解析器为准。

## 图文事件与选择题

```json
{"slides":[
 {"image":"cover.png","text":["海风停了一下。","她递来折好的纸船。"]},
 {"image":null,"text":["仍沿用同一张图。"]}
],"choice":{"title":"接下来呢？","options":[
 {"text":"继续聊聊","kind":"story","to":"night"},
 {"text":"回到主页","kind":"appShell","to":"home"}
]}}
```

一块是一屏，一张图加多句，text 是句子数组；image 省略或 null 沿用上一张。事件可用与情景相同的 target，或用 choice，**二选一**。choice 有1–5个选项，不带条件或权重；条件提前放在进入事件的出口中。事件台账与图库解锁由引擎处理，不能写旧 onFinish/effects/unlockEnding/endingId。

## 验收

走通新档、跨天循环、条件阈值前后、随机备选、每个 choice、回主页；多角色核对 audience，换幕核对服装与表情矩阵。验证无证据结算与 abort，存档身份与多版本共存。结构通过不代表剧情或模型体验通过。

基线安装上限：ZIP 256 MiB、解压1 GiB、5000条目、单JSON 8 MiB，以目标 `install_limits.dart` 为准。网站缩略图属于包外，不为网页体积牺牲安装包原画质。

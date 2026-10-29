# makeChatGal.skill

让有生图工具和没有生图工具的 agent，都能按真实协议制作 ChatGal 内容包。

面向 [ChatGal](https://github.com/RongShangs/ChatGal) 的开源创作技能。覆盖角色人格、服装与表情矩阵、多角色出场、情景、变量、离场结算、条件分支、随机出口、图文事件、玩家选择、应用设置建议，以及官方校验和 `.chatgal` 打包。

## 有图工具就生图，没图工具就给提示词

| 运行环境 | 交付 |
| --- | --- |
| 实际存在可调用、已授权的生图工具 | agent 正常调用，检查与裁切素材；资源齐全且官方校验通过后交付可导入包 |
| 没有生图工具 | 完整故事源文件、资源清单、每张图片的提示词和待补路径；不制造占位图片、不虚报生图完成 |
| 用户提供现成图片 | 结合授权素材补齐所需资源；只生成或给出缺失部分的提示词 |

此仓库不绑定某一个生图 API、不包含密钥，也不会把“能看图”误认为“能生图”。模板脚本只准备文件，实际生图由使用技能的 agent 调用其工具。

## 安装与使用

技能目录是 [`skills/make-chatgal/`](skills/make-chatgal/)，入口为 `SKILL.md`。将整个目录放入 agent 支持的 skills 目录；Codex 可放到 `~/.codex/skills/make-chatgal/`。其他支持 SKILL.md 的 agent 按各自发现规则安装，也可显式提供入口文件。

示例请求：

> 使用 $make-chatgal，制作一个有两位角色的海边故事。平时三幕循环，达到好感条件后进入图文事件，并让我选择继续日常还是回主页。按当前生图能力处理图片，给出语音朗读的设置建议。

也支持明确要求“本次只准备提示词，不生成图片”。技能保留用户意图，不强迫所有作品采用三幕、同一画风或固定表情数量。

## 版本关联

| 项目 | 当前基线 |
| --- | --- |
| Skill | 0.1.0 |
| ChatGal 应用 | 0.1.6+7 |
| 主项目提交 | `9c833c87303fc9fc5ede9dfcf989f5d5d4119663` |
| 内容协议 | flat v2 / JSONC |
| 内置包 | 默认264、日常9；第三方包独立编号 |

[`compatibility.lock.json`](skills/make-chatgal/compatibility.lock.json) 记录代码提交、应用版本、真实字段、安装限制、能力范围与监控文件指纹。每次创作先检查目标工程；监控文本按 LF 规范化，避免跨系统换行造成误报。

**当前不能把动画、音乐写成包内功能。** 客户端已有 UI 转场与云端 TTS，但不等于支持动画立绘、BGM 或音效资源。未来主项目新增能力时，技能要求审阅解析、验证、渲染及生命周期，更新文档、生成器、资源规则和测试，再更新基线。

提供每日上游监测工作流模板，启用后会在版本/相关代码变化时创建或更新一个兼容维护 issue；不会自动合并、不盲目承诺新能力。具体更新步骤在 [兼容维护参考](skills/make-chatgal/references/compatibility.md)。自动检测不等于自动完成语义维护。

## 本地工具

Python 3.10+。核心脚本使用标准库；裁图与完整 PNG 解码检查需要 Pillow。正式校验需要目标 ChatGal 工程、其 Dart 工具链及 `gal_protocol` 包依赖。

```sh
python -m pip install -r requirements-dev.txt

# 检查目标项目与已审阅基线
python skills/make-chatgal/scripts/upstream.py check --project /path/to/ChatGal

# 在新目录创建源包和逐图提示词（不会调用生图）
python skills/make-chatgal/scripts/init_pack.py \
  --output /path/to/new-work \
  --brief skills/make-chatgal/assets/example-brief.json \
  --template branching --image-mode prompts

# agent 按用户需求改写故事，并完成 asset-plan 中的图片后：
python skills/make-chatgal/scripts/build_pack.py \
  --project /path/to/ChatGal --source /path/to/new-work/pack \
  --output /path/to/release-v1.chatgal
```

`daily` 模板演示三幕循环；`branching` 演示随机情景、条件分支、图文事件、继承画面、选择题和回主页。它们是起点，不是作品限制。正式工具调用主项目同一份 PackageLoader/PackageValidator，不维护另一套条件解释器。打包固定 ZIP 时间戳并回读校验；同版本内容更新可用 `--previous` 防止误发。

缺图或无 Dart 时，可以保留源目录；如需草稿归档，使用 `--draft --output name.draft.zip`。草稿不会被称为可导入成品。主项目不同版本可先审阅，再生成本次任务的独立兼容记录，详见技能参考。

## 能力与设置

内容包字段与应用设置分开处理。供应商、流式输出、回复长度、五层记忆、主题、立绘尺寸、消息留白、字体、云端朗读等，输出无密钥的应用使用建议；不偷偷塞进 manifest，不修改用户配置或存档。TTS 可给音色/语速/试听建议，但不宣称包可绑定每位角色的声音。

主要参考：[作者能力](skills/make-chatgal/references/authoring.md) · [图片流程](skills/make-chatgal/references/artwork.md) · [设置边界](skills/make-chatgal/references/settings.md) · [机器能力表](skills/make-chatgal/references/capabilities.json)。

## 验证与维护

```sh
python -m unittest discover -s tests -v
python tests/runtime_integration.py --project /path/to/ChatGal
python tools/package_skill.py
```

运行时集成使用临时生成的**测试用16像素色块**，通过实际官方校验器和 TransitionCoordinator/EventCoordinator 测试循环、阈值、结算、随机分支与事件。这些夹具不是交给用户的美术素材，也没有包含用户参考图。

首版已通过13项工具测试和上述运行时集成。独立 agent 还完成了无生图环境的双角色创作试跑、逐图提示词、缺图阻断和53项实际运行逻辑检查；该试跑发现的“零张图片仍显示解码方法”报告歧义已修复，报告现在明确记录检查数量和未检查状态。未据此声称已完成真实模型或手机端验收。

`automation/workflows/ci.yml` 提供工具和锁定上游的实际运行检查；`upstream-watch.yml` 提供上游 main 的每日监测。当前发布凭据缺少 GitHub 的 workflow 权限，因此模板尚未作为 Actions 启用。获得授权后，把该目录放到 `.github/workflows/` 即可启用；也可以手动运行本地检查。维护请保持文档、能力表、脚本、锁文件与测试一起更新，不能只刷新哈希让检查变绿。

## 许可与来源

GPL-3.0-only，与主项目许可一致。技能说明和工具在本仓库维护；ChatGal 的协议、官方校验器和客户端属于 [RongShangs/ChatGal](https://github.com/RongShangs/ChatGal)，权威规则仍以目标代码为准。仓库不包含应用安装包、用户角色图、个人配置、存档或服务凭据。

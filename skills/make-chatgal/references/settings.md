# 应用设置与内容包边界

这些能力可配合作品，但当前不是 .chatgal 字段。输出不含密钥的 `settings-recommendations.md`，写用途和实际可调项；用户未要求时不覆盖应用配置或存档。

| 能力 | 真实配置与创作方式 |
| --- | --- |
| 模型供应商 | ProviderPreset: id/name/endpoint/apiKey/model/enabled/isLocal；AppSettings 选择活动项和 streamOutput。本地 OpenAI 兼容服务可无 key，以服务端为准 |
| 回复长度 | replyLength: short/medium/long；配合角色口吻，不伪造包内 maxTokens |
| 请求参数 | ProviderConfig 有 temperature/maxTokens/timeout，但当前 ProviderPreset.toConfig 固定0.8/2048，不等于 UI 全部可调；不捏造 topP/seed/WebSocket 设置 |
| 五层记忆 | MemoryThresholds 控制 L1 保留/坍缩，L2→L3→L4→L5 阈值和批量、L5字符上限和自压缩、L3关键词；不写进包或存档，不承诺无限记忆 |
| 显示 | themeId/showBg/portraitHeight/chatBottomPad/autoRemoveBg；立绘优先真透明，自动抠图只是客户端选项 |
| 字体 | chatFontId/chatFontSize/importedFonts，说明可读字号与授权字体 |
| 云端朗读 | TtsSettings: enabled/endpoint/apiKey/model/voice/speed/format/autoRead/skipActions/sampleText，可附音色与试听建议，无角色级包内语音字段 |
| 日志和选择状态 | logMaxEntries/lastPackageId/lastPackageVersion/lastSaveId 等是应用状态，不是剧情变量，不复制到公开包 |
| 创作与管理 | 创作台可编辑包信息、角色矩阵、情景与事件，包/存档管理可导入导出，世界控制台与记忆回廊用于检查；不绕过校验直接改已安装包 |

记忆基线默认：L1保留30、触发50，每批=触发−保留；L2/L3提升阈值6、批量3；L4阈值4、批量2；L5上限1200字符、自压缩批量2；L3关键词上限12。必须触发>保留。默认值是事实，不是每个作品都必须采用的建议。

TTS 使用 OpenAI 兼容 `/audio/speech` 朗读文本，可自动朗读和跳过括号动作；它不是BGM/音效，也不是包内预录台词。输出格式白名单和参数以 `tts_settings.dart` 为准，不把应用设置写成情景 music/audio/voice 字段。

已有 UI 转场和逐段表情切换不等于动画立绘、帧序列或视频资源能力。新增能力须一起确认解析、验证、资源定位、渲染与存档生命周期。

# 与主项目版本关联、更新与离线边界

## 三种版本分别管理

1. skill 版本：本仓库发行版本。
2. ChatGal 应用版本与源码提交：锁定在 compatibility.lock.json，附被审阅的协议/渲染/设置文件指纹。
3. 内容包版本：独立 packageId 下的纯数字字符串，不必等于应用或 skill 版本。

第三方包更新提高自身版本、保留 packageId。同 packageId+version 内容变化会触发安装哈希冲突，不能靠覆盖 ZIP 混过去。内置默认包更新才需同步 defaultPackageVersion、manifest 及重建工具版本；内置 daily 包同步 dailyPackageVersion。对独立作者包不要改主应用常量。

## 每次创作的预检

`upstream.py check --project ...` 比较目标源码，读取而不修改主项目或联网。提交号改变但被监控内容与版本不变，可以继续；版本不变而代码变了仍会报告漂移。输出退出码3表示待审阅，不等于作品有错。

查看 changedPaths 与新增字段，按用户这次用到的能力读目标解析器、校验器、资源定位、UI 和运行测试。旧能力未受影响可按证据继续；没有源码/离线时以锁定基线创作，不能宣称兼容未知客户端。

需要为新的目标建立已审阅记录时，可输出到**本次工作目录**，不必修改全局安装的技能：

```text
python scripts/upstream.py capture --project <ChatGal目录> --output <工作目录/reviewed-target.json> --reviewed
python scripts/build_pack.py --project <ChatGal目录> --source <pack目录> --output <结果.chatgal> --lock <工作目录/reviewed-target.json>
```

`--reviewed` 是维护者对已完成审阅的记录，不是自动推断新功能的开关。先更新本次涉及的新能力说明、资源计划与代码，再生成记录；不能仅刷新哈希让检查变绿。

## 动画、音乐等新增能力

监控脚本会捕捉 schema、protocol、AI编排、安装、会话/创作台、设置/TTS 的新增或修改文件；新增字段名只作为候选信号。TTS 的 audio/speech 与 UI AnimationController 不是包内音乐/动画的支持证据。

一项能力进入“支持”前，需要：

- 查清真实字段、默认值、路径和媒体格式；播放器/渲染器确实消费字段，而非解析后忽略。
- 明确循环、暂停/切幕/退出时清理、与朗读的关系、回放和存档恢复、错误回退、安装上限。
- 更新 capabilities.json、本参考、相关作者/素材说明与生成器、字段检查、媒体识别和示例。
- 添加该能力的正例、错误配置与退化路径测试，使用官方校验器和适当运行/UI测试。
- 审阅完成后 capture 基线，增加 skill 发行版本并记录兼容范围。原 PNG/旧故事仍需回归检查。

## 维护机制

仓库提供 CI 与每日上游监测的工作流模板；维护者启用后，CI 检查锁定版本，监测任务跟踪上游当前代码，发现漂移时创建或更新一个维护 issue，附差异，不自动承诺新能力、不自动合并代码。尚未启用工作流的环境可手动执行 check。维护者或有授权的 agent 根据差异完成上面的同步更新，再提交/发行。

这避免两个错误：技能永久钉死旧能力，或只把版本号换新就声称支持动画/音乐。自动监测不是自动完成语义维护；README 与发行说明应明确这一点。

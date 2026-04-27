<div align="center">
  <img src="apps/desktop/src-tauri/icons/128x128.png" alt="Eatit" width="96" height="96" />

  <h1>Eatit</h1>

  <p><strong>BYOK 的本地 AI 模拟面试官 · macOS 桌面应用</strong></p>

  <p>
    <a href="#%E5%AE%89%E8%A3%85"><img alt="platform" src="https://img.shields.io/badge/platform-macOS%2012%2B-lightgrey" /></a>
    <a href="#%E6%8A%80%E6%9C%AF%E6%A0%88"><img alt="frontend" src="https://img.shields.io/badge/frontend-Tauri%202%20%2B%20React%2018-blue" /></a>
    <a href="#%E6%8A%80%E6%9C%AF%E6%A0%88"><img alt="backend" src="https://img.shields.io/badge/backend-FastAPI%20%2B%20SQLite-success" /></a>
    <a href="#%E6%8A%80%E6%9C%AF%E6%A0%88"><img alt="asr" src="https://img.shields.io/badge/ASR-faster--whisper%20local-orange" /></a>
  </p>

  <p>
    上传简历与 JD,自定义面试风格,Eatit 用你自己的 LLM Key 给你做一场结构化模拟面试,本地 SQLite,无登录,无云同步。
  </p>
</div>

---

## 为什么选 Eatit

- **完全本地**:简历、面试录音、回答记录、报告全部存在 `~/Library/Application Support/Eatit/`,不上传任何云
- **BYOK(Bring Your Own Key)**:你用自己的 LLM Key 调 OpenAI / DeepSeek / 硅基流动 / 阿里云百炼 / Anthropic / 自定义 base_url,Eatit 不中转、不计费、不接触余额
- **零依赖运行**:macOS 双击 DMG 即开,Python 后端 + SQLite + 本地 ASR 全部打包进 `.app`,不需要装 Docker / Homebrew / 任何运行时
- **真实临场感**:面试官语音播报问题、按住说话录音、实时转写,跟真实电话面试节奏一致
- **AI 全程辅助**:答题时可一键查看参考提纲;每轮答完右侧会有 AI 观察提醒;最终生成带证据绑定的评估报告

## 截图

> *截图位待补,可拖一张 Eatit 实机截图到 `docs/` 后引用*

## 主要功能

| 模块 | 描述 |
| --- | --- |
| 简历 + JD 解析 | ParseAgent 从简历 + JD 提炼匹配点、亮点、风险、可深挖的项目 |
| 自定义面试框架 | 选风格(友好引导 / 标准专业 / 高强度追问)、方向(岗位匹配 / 项目深挖 / 行为综合)、时长(15/20/30 min) |
| 实时面试 | 语音 / 文字双模,本地 faster-whisper 做 ASR,中文语音播报问题 |
| AI 参考答案 | 每轮问题刚出来时后台异步生成提纲 + 完整示例 + 评分关键点 + 常见误区,默认隐藏,一键展开 |
| AI 实时观察 | 每轮答完 AI 给一句 ≤ 60 字的 support / alert / pivot 提醒 |
| 评估报告 | 通过可能性环 + 证据绑定的维度评价 + 下一场行动建议,可一键打印为 PDF |
| 综合分析 | 跨多场面试的 MetaReport,识别长期模式 |

## 安装

### 1) 下载 DMG

从 [Releases](https://github.com/dqh3388ok-cloud/eatit/releases) 下载最新的 `Eatit_x.x.x_aarch64.dmg`(Apple Silicon)。

### 2) 拖到 Applications

打开 DMG,把 `Eatit.app` 拖到 `/Applications/`。

### 3) 首次打开(绕过 Gatekeeper)

> ⚠️ Eatit 当前是 **ad-hoc 签名**(未购买 Apple Developer 证书),首次打开需要绕一次 Gatekeeper。Apple Developer 签名 + 公证在 Roadmap。

**最简单的方式**(macOS 14 / 15 都通用):打开「终端」,粘贴这一行回车

```bash
xattr -cr /Applications/Eatit.app && open /Applications/Eatit.app
```

之后双击就能开,不需要再跑这条。

> 或者:Finder 找到 Eatit → 右键 → 打开(macOS 14 及以下);macOS 15 Sequoia 上需要走「系统设置 → 隐私与安全性 → 仍要打开」。

## 快速上手

1. **配置 LLM Key** —— 设置 → 选 Provider(默认硅基流动) → 粘贴 API Key → 测试连接
2. **上传简历 + JD** —— 拖拽 PDF/文本文件 → 点「开始 AI 解析」
3. **配置面试** —— 选风格 / 方向 / 时长 → 点「开始面试」(等 30–60 秒生成框架)
4. **答题** —— 听 AI 面试官提问(语音/文字),按住说话或键入回答
5. **拿报告** —— 答完点「提前结束」或自然结束,AI 生成带证据绑定的评估报告

## 技术栈

| 层 | 选型 |
| --- | --- |
| 桌面壳 | Tauri 2.10 + Wry(WKWebView) |
| 前端 | React 18 + TypeScript 5 + Vite + XState + TanStack Query + Zustand |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2(async) + Alembic + structlog |
| 数据 | SQLite + WAL 模式 + 本地文件系统(`~/Library/Application Support/Eatit/`) |
| LLM 接入 | LiteLLM + Instructor(强制 JSON) + tenacity(重试) |
| Agent 编排 | LangGraph + asyncio TaskGroup |
| 语音识别 | faster-whisper(CTranslate2 + PyAV)本地推理 |
| 语音合成 | Web Speech API(macOS 系统中文语音) |
| 打包 | PyInstaller(后端 onedir) + Tauri bundler + ad-hoc 签名 |

## 架构

```
┌─────────────────────────────────────────────────────────┐
│   Eatit.app (Tauri 2)                                   │
│  ┌────────────────────────┐   ┌──────────────────────┐  │
│  │  React UI (WebView)    │ ──── invoke ────►        │  │
│  │  - InterviewPage XState│   │  Rust core          │  │
│  │  - WS / REST clients   │   │  - keyring (LLM Key)│  │
│  └────────────────────────┘   │  - spawn backend    │  │
│                  │             │  - open_system_url  │  │
│                  │ 127.0.0.1   └──────────┬───────────┘  │
│                  │             :random      │             │
│                  ▼                          ▼             │
│  ┌─────────────────────────────────────────────────┐  │
│  │ FastAPI backend (PyInstaller frozen)           │  │
│  │ ├─ /api/v1/parse   ParseAgent                  │  │
│  │ ├─ POST /sessions  FrameworkAgent              │  │
│  │ ├─ /ws/sessions    InterviewerAgent + LangGraph│  │
│  │ │                  (assess ∥ compress) →       │  │
│  │ │                  next_question + reference   │  │
│  │ │                  + observer (fire-and-forget)│  │
│  │ └─ POST /report    ReportAgent (TaskQueue)     │  │
│  └────────────────────────────────────────────────┘  │
│                          │                              │
│                          ▼                              │
│       ~/Library/Application Support/Eatit/              │
│       ├─ eatit.db (SQLite + WAL)                        │
│       ├─ cache/                                         │
│       └─ storage/                                       │
└─────────────────────────────────────────────────────────┘

LLM 调用全程走用户的 BYOK 配置,key 仅在请求 header 里以 base64 JSON 携带,
不落库 / 不进日志 / 不进 Sentry。请求结束即从内存丢弃。
```

## 从源码构建

<details>
<summary>展开开发环境配置</summary>

### 前置依赖

- Node.js 20+ 与 `pnpm`(可用 `corepack enable`)
- Python 3.11+ 与 [`uv`](https://docs.astral.sh/uv/)
- Rust 工具链 + `aarch64-apple-darwin` target
- Xcode Command Line Tools

```bash
rustup target add aarch64-apple-darwin
```

### 启动开发模式

```bash
# 1. 安装依赖
pnpm install
cd apps/api && uv sync && cd ../..

# 2. 跑迁移
cd apps/api && uv run alembic upgrade head && cd ../..

# 3. 起后端(终端 A)
cd apps/api && uv run uvicorn app.main:app --reload

# 4. 起桌面 app(终端 B)
pnpm --dir apps/desktop tauri dev
```

### 跑测试

```bash
# 后端
cd apps/api && uv run pytest -v

# 前端 lint + 类型检查
pnpm --dir apps/desktop lint
pnpm --dir apps/desktop exec tsc --noEmit
```

### 打 DMG

```bash
scripts/build-unsigned-dmg.sh
```

产物:`apps/desktop/src-tauri/target/aarch64-apple-darwin/release/bundle/dmg/Eatit_x.x.x_aarch64.dmg`(约 127 MB,冷构建 8–10 min)。

</details>

## 隐私与数据流

- LLM Key 存 macOS Keychain(service=`com.eatit.desktop`)
- 简历 / JD / 面试转写 / 报告全部本地 SQLite,**永不上传**
- LLM 调用直连用户在设置里填的 base_url(默认走对应 provider 官方)
- 无埋点、无 telemetry、无自动更新

## Roadmap

- [x] Phase 1–4 基础闭环(BYOK / 6 Agent / LangGraph / 语音面试)
- [x] Phase 5.1–5.6 打包 + 错误边界 + Sentry scaffold + PDF 导出
- [ ] Phase 5.3:Apple Developer 签名 + 公证(消除 `xattr -cr` 步骤)
- [ ] 一键获取 API Key 跳转(参考 Cherry Studio)
- [ ] 报告深化:拉分/扣分项展开、下一场 drill 建议
- [ ] 面试记录搜索 / 筛选 / 「再来一场同岗位」CTA
- [ ] 跨平台:Windows + Linux 构建(目前仅 Apple Silicon macOS)

## License

License TBD —— 当前仓库尚未添加 LICENSE 文件。在添加前请勿用于商业用途。

## 致谢

- [LiteLLM](https://github.com/BerriAI/litellm) —— provider 抽象
- [Instructor](https://github.com/jxnl/instructor) —— 强制 LLM 输出 schema
- [LangGraph](https://github.com/langchain-ai/langgraph) —— 多 Agent 编排
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) —— 本地 ASR
- [Tauri](https://tauri.app) —— 跨平台桌面壳

# 本地启动与比赛演示

在项目目录运行 `./start-local.ps1`，访问 http://localhost:3001 。后端为 http://127.0.0.1:8000 。本地模式使用持久化 SQLite 数据库 `backend/local.db`，首次启动自动创建表与随机密钥。密钥在已忽略的 `.env.local`，请保留该文件以便解密已保存的模型凭据。Docker 模式仍使用 PostgreSQL。

## 首次配置其他 Windows 电脑

1. 安装 Python 3.12+、Node.js 22。
2. 执行 `python -m venv .venv`。
3. 执行 `.venv/Scripts/python.exe -m pip install -r backend/requirements.txt`。
4. 在 `frontend` 目录执行 `npm ci`。若 Windows 缺少 Tailwind 原生依赖，执行 `npm install --no-save @tailwindcss/oxide-win32-x64-msvc@4.3.3`。
5. 回项目根目录执行 `./start-local.ps1`。

## 演示路径

1. 首页：切换网络图下方的三个流程标签，介绍“识别 → 扩展 → 核查”。此图是流程示意，不是实际分析结果。
2. 注册、登录后进入工作台。
3. 在“模型配置”保存并验证自己的 DeepSeek API Key。
4. 进入“靶点识别”，选择疾病，点击“填入示例问题”，按研究目标编辑后开始识别。
5. 完成后展示候选排序、交互关联网络、候选对比与报告导出。

没有真实 API Key 时无法执行真实大模型识别，不会以演示数据代替结果。本轮验证真实注册登录、疾病目录、提交前交互与后端自动化测试；外部模型端到端调用尚未验证。

## 项目级设计 skill

位于 `.agents/skills/ui-ux-pro-max`，来自 https://github.com/nextlevelbuilder/ui-ux-pro-max-skill 。采用雾白、浅青与蓝绿色的明亮生物科技风首页及研究工作区，无需全局安装。

## Docker 与数据

执行 `docker compose up -d --build` 前须确保 Docker 代理可用。本机 Docker 代理 `127.0.0.1:12450` 下载镜像时连接被拒绝，因此使用本地模式。首次使用 PostgreSQL 需执行 `docker compose run --rm backend alembic upgrade head` 创建表。

快照 JSON 通过 `.gitattributes` 固定为 LF 换行，避免 Windows 换行转换导致 SHA-256 校验失败。

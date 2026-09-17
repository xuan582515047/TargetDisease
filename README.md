# 靶研助手 —— 可解释靶点优选平台

融合大模型与生物关联网络的可解释靶点优选平台：大模型从本地证据池识别种子靶点，
本地 CPU 算法在蛋白功能关联网络上做个性化 PageRank 传播扩展候选，程序核查证据，
通过交互式关联网络展示结果，支持候选对比与报告导出。

## 技术栈

- 后端：FastAPI + SQLAlchemy 2.0 + PostgreSQL + Alembic + NetworkX（CPU 稀疏网络传播）
- 前端：Next.js 16 + React 19 + Tailwind 4 + Cytoscape.js（关联网络可视化）
- 大模型：DeepSeek（外部 API 调用，非本地推理）

## 前提

- 已安装并启动 Docker Desktop（含 Compose v2）。

## 启动

Windows 本地运行（无需 Docker）：参见 [本地启动与比赛演示](docs/LOCAL-DEMO.md)，环境准备好后执行 `./start-local.ps1`，访问 http://localhost:3001 。

以下为原有 Docker 部署方式：

1. 复制 `.env.example` 为 `.env`，填入 `APP_SECRET_KEY` 与 `APP_CREDENTIAL_MASTER_KEY`。
   - `APP_SECRET_KEY`：`python -c "import secrets; print(secrets.token_urlsafe(48))"`
   - `APP_CREDENTIAL_MASTER_KEY`：`python -c "import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"`
2. `docker compose up --build`

- 前端: http://localhost:3001
- 后端: http://localhost:8000（健康检查 `/healthz`）

## 数据准备

平台依赖两个本地快照，均以版本化 JSON 形式保存在 `backend/data/` 下，程序校验后激活。

### 证据快照（Open Targets）

```bash
cd backend
python -m scripts.import_target_evidence --disease MONDO_0004975 --name-zh 阿尔茨海默病
```

生成 `data/target_evidence/` 下 `diseases.json`、`targets.json`、`evidence.json`、`manifest.json`。
数据来源 [Open Targets Platform](https://platform.opentargets.org/)，许可 CC BY 4.0。

### 网络快照（STRING）

```bash
cd backend
python -m scripts.import_target_network --threshold 0.7 --hops 2
```

生成 `data/target_network/` 下 `nodes.json`、`edges.json`、`manifest.json`。
数据来源 [STRING](https://string-db.org/)，许可 CC BY 4.0。边分值为 STRING combined_score
归一化到 0~1 的功能关联置信分，不等于物理结合、药理效应或疾病因果关系。

## API 配置

在「设置 → 模型配置」中填入 DeepSeek API Key。密钥经 AES-GCM 加密后存库，不落明文。

## 容量限制

- 固定计算图上限 2000 节点 / 20000 边；默认保留关联置信分 ≥0.7 的边。
- 默认视图最多 100 节点 / 500 边，超限按关联分值确定性裁剪。
- 每账号最多 1 个活动任务，全局模型并发 2、活动任务总数 10。
- 模型调用超时 120 秒、最多 2 次请求、单任务总时限 300 秒。

## 测试

```bash
cd backend
pip install -r requirements.txt
SECRET_KEY=test-secret CREDENTIAL_MASTER_KEY=$(python -c "import base64;print(base64.urlsafe_b64encode(b'0'*32).decode())") \
  pytest tests/
```

## 目录结构

```
backend/
  app/services/        # 证据/网络快照、模型识别、证据核查、传播、排序、稳定性、报告
  app/api/v1/          # auth/projects/credentials/runs/target-analysis 路由
  scripts/             # Open Targets / STRING 数据导入脚本
  data/                # target_evidence / target_network 快照
frontend/
  app/target-discovery/           # 输入页、结果页、网络页、对比页、报告页
  components/target-network/      # Cytoscape 网络画布与控件
```

## 免责声明

本平台输出为候选优选依据，不构成新靶点发现、因果关系或临床结论。

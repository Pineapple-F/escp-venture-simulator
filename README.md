# ESCP 创投模拟器网站

这是从研究项目中整理出的最小可部署版本，仅包含网站运行所需的前端、Python 后端、指标和预测结果。

## 目录

```text
demo/       前端 HTML、CSS、JavaScript 和展示数据
scripts/    Python 后端
processed/  后端读取的模型指标
external/   后端读取的预测结果
```

## 本地运行

要求 Python 3.10 或更高版本。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/demo_backend.py
```

访问：<http://127.0.0.1:8787/>

检查接口：<http://127.0.0.1:8787/api/status>

## Gemini 助手

AI 助手是可选功能。不要把 API Key 写进代码或提交到 Git：

```bash
export GEMINI_API_KEY="你的密钥"
export GEMINI_MODEL="gemini-3.6-flash"
python scripts/demo_backend.py
```

部署平台中应把 `GEMINI_API_KEY` 保存为 Secret。未配置时，网页会自动使用本地数据回答。

## Docker

```bash
docker build -t escp-venture-simulator .
docker run --rm -p 8787:8080 \
  -e GEMINI_API_KEY="你的密钥" \
  escp-venture-simulator
```

容器默认监听 `0.0.0.0:8080`，可部署到 Cloud Run、Cloudflare Containers 或其他支持 Docker 的平台。

## CI 配置要点

- 启动入口：`python scripts/demo_backend.py`
- 健康检查：`GET /api/status`
- 必需依赖：`requirements.txt`
- 可选 Secret：`GEMINI_API_KEY`
- 可选环境变量：`GEMINI_MODEL`
- 平台端口：由 `PORT` 环境变量自动读取

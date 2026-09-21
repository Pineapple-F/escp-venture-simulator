# 模型运行包

本目录包含网站事件预测所需的最佳模型权重、推理代码、匿名历史输入和金融语义缓存。

## GitHub 中未包含的文件

FinBERT2-large 权重文件约 1.3GB，超过 GitHub 普通 Git 的单文件限制，因此不提交：

```text
model-runtime/research/enterprise_path_finance_knowledge/
  pretrained/FinBERT2-large/model.safetensors
```

首次运行 `./start.sh` 并调用预测功能时，程序会从以下固定版本自动下载该文件：

- 模型：`valuesimplex-ai-lab/FinBERT2-large`
- revision：`5928de1860ce5eb5f1f2dd23c08d2b9dcc1b0686`

如果部署环境禁止联网，请提前下载权重并放到上述路径。设置
`MODEL_ALLOW_DOWNLOAD=0` 可以禁止程序自动下载。

## 未提交的本机文件

以下内容不是部署资产，不上传 GitHub：

- `market-simulator/.venv/`
- `market-simulator/runtime/saves.sqlite3`
- `market-simulator/runtime/model-worker.log`
- Python 缓存文件

账户数据库包含本机用户操作记录，部署时由网站自动创建。

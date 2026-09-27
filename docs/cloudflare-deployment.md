# ESCP Cloudflare 部署

核对日期：2026-09-27。目标域名：`https://venturesimulator.actscal.org`。

## 本次方案

```text
浏览器 → Cloudflare Static Assets：现有投资人端、企业端页面
       → /api/* → Python Container：业务、知识图谱、事件预测
                       ↓ 私有 outbound handler
                 Durable Object SQLite：账户与操作存档
```

当前业务只有 `saves(id,state)` 账户存档表，没有 MySQL 驱动、连接配置或 MySQL 特有查询，因此暂不部署 MySQL。用户模拟投资、融资方案、关注、企业自建路径都保存在账户 JSON 中。以后真正接入大量浏览/曝光日志或需要跨账户统计，再评估 MySQL。

线上存档现在写入容器配套 Durable Object 的 SQLite `account_saves` 表，使用 revision 条件更新，防止并发覆盖。容器磁盘上的预测缓存可以重算；用户存档不能依赖容器磁盘。不要删除 `VentureSimulatorV2` 命名空间、重命名该类或改变固定实例名 `production`，否则会影响已有存档访问。

本地直接运行仍使用 `market-simulator/runtime/saves.sqlite3`；原有本机存档未修改、未上传，也不会自动成为线上账户。部署前如果旧线上容器已有用户存档，先导出并安排迁移，不要把旧容器文件视为已迁移。浏览器当前账户可从 `/api/legacy-export` 导出 JSON。

## 已有部署问题

检查了提交 `ffa1973` 对应的 [失败 Actions](https://github.com/Pineapple-F/escp-venture-simulator/actions/runs/36314088187)：Wrangler 最后报 `Unauthorized`。账号 ID 和 Token 已存在 GitHub Secrets 中，但存在并不代表拥有 Containers 发布权限。

旧部署还将所有静态文件经容器转发、空闲 24 小时后才休眠，并把用户存档留在临时文件系统。现在前端单独发布，API 才访问容器；空闲 10 分钟休眠，最多 1 个实例；模型按需加载。

## 你需要在账号中完成的事

1. 登录 Cloudflare，选择域名及项目所在账号，在 **Workers & Pages / Workers 订阅** 中开通 **Workers Paid（5 美元/月起）**。这是账号级 Workers 套餐，不是域名的 Pro 套餐，也不需要 Workers AI。付款前以结算页为准；本次代码修改不会替你购买套餐。
2. 创建或调整部署 API Token，限定到项目账号和 `actscal.org` 区域。需要账号级 **Workers Scripts: Edit、Containers: Edit、Account Settings: Read**；自定义域名还需要相应区域的 **Workers Routes: Edit、Zone: Read**。有些 API 界面将 Edit 显示为 Write。不要使用 Global API Key。
3. 打开 [GitHub Actions Secrets](https://github.com/Pineapple-F/escp-venture-simulator/settings/secrets/actions)，确认 `CLOUDFLARE_ACCOUNT_ID` 对应该账号，更新 `CLOUDFLARE_API_TOKEN`。无需把密钥发在对话里。现有 `DEEPSEEK_KEY` 不用于当前这套 Python 网站部署。
4. 保证 `actscal.org` 在相同账号中启用；配置已声明 `venturesimulator.actscal.org` 为 Worker 自定义域名。
5. 在 [Actions](https://github.com/Pineapple-F/escp-venture-simulator/actions) 运行 **Verify and deploy ESCP**，选择需要发布的分支，勾选 `publish`。以后推送 `main` 会自动验证并发布；`deploy/**` 分支默认只验证。

支付方式在 **Manage Account → Billing → Subscriptions** 中设置。官方支持银行卡、PayPal 等方式，具体可用选项以你的结算页为准；账单按美元计价，税费和换汇由结算页及支付机构决定。用量可以在 **Billing → Billable Usage** 查看，预算通知只提醒，不是自动停机或消费硬上限。参见 [账单与支付说明](https://developers.cloudflare.com/billing/) 和 [账单界面更新](https://developers.cloudflare.com/changelog/post/2026-05-21-modernised-billing-profile/)。

工作流依次执行存档/业务测试、当前前端构建、Worker 校验、linux/amd64 镜像构建、6GiB/1CPU 环境的页面与模型加载测试、Worker 与容器存储联调、Cloudflare 权限预检、正式发布和线上验收。GitHub runner 自带 Docker，因此不要求你电脑一直开着。

首次构建需下载约 1.3GB 的固定版本 FinBERT 权重；首次容器部署也需要等待平台分配资源。不要仅根据 Worker URL 能打开就认为模型和数据库已验收。

## 付费标准

下面为核对日的官方美元价格，不含税。Workers、Containers、Durable Objects 的超额费用分别计量，包含额度在账号内共享。

| 项目 | 月包含额度 | 超额价格 |
|---|---|---|
| Workers Paid | 套餐最低 5 美元/月；1000 万请求、3000 万 CPU 毫秒 | 请求 0.30 美元/百万；CPU 0.02 美元/百万毫秒 |
| Containers 内存 | 25 GiB·小时 | 0.0000025 美元/GiB·秒，约 0.009 美元/GiB·小时 |
| Containers CPU | 375 vCPU·分钟 | 0.000020 美元/vCPU·秒，约 0.072 美元/vCPU·小时 |
| Containers 临时磁盘 | 200 GB·小时 | 0.00000007 美元/GB·秒，约 0.000252 美元/GB·小时 |
| Durable Objects SQL 存储 | 5 GB·月、250 亿行读取、5000 万行写入 | 存储 0.20 美元/GB·月；读 0.001 美元/百万行；写 1 美元/百万行 |

容器内存和磁盘按**实例配置 × 运行时间**计费，CPU 按实际活动用量计费；进入休眠后停止该实例计算资源计费。前端静态资源请求免费，不等于所有 API 和容器费用免费。Durable Objects 请求/运行时间、日志及超额出站流量另按官方标准计费。

当前配置 `standard-2` 是 **1 vCPU、6GiB 内存、12GB 临时磁盘**，最多 1 实例。这是兼顾完整文本模型的起点，仍应根据实际延迟与内存曲线调整。

按 30 天、账号额度未被其他项目占用估算：

- 每天总运行 2 小时（含空闲等待），月运行 60 小时：套餐＋内存＋磁盘约 **8.15 美元**；CPU 满负荷跑满这 60 小时，再加约 **3.87 美元**。
- 全天运行，月 720 小时：套餐＋内存＋磁盘约 **45.78 美元**；CPU 满负荷跑满 720 小时，再加约 **51.39 美元**。
- 上述均未计其他超额费用，并非套餐报价或账单上限。10 分钟休眠与单实例上限不能保证固定账单；在 Billing / 使用量界面检查消费并配置可用的账单通知。

官方依据：[Workers 价格](https://developers.cloudflare.com/workers/platform/pricing/)、[Containers 价格](https://developers.cloudflare.com/containers/platform/pricing/)、[Durable Objects 价格](https://developers.cloudflare.com/durable-objects/platform/pricing/)、[实例规格](https://developers.cloudflare.com/containers/platform/limits/)、[Token 权限](https://developers.cloudflare.com/fundamentals/api/reference/permissions/)。

## 本地验证与手动发布

需要 Node.js 22、Python 3.12、已运行的 Docker。

```sh
npm ci
npm run build
npm test
npm run check:worker
docker build --platform linux/amd64 -t escp-local .
npm run dev
```

`check:worker` 仅校验 Worker 与静态资源，跳过容器 rollout；完整镜像和存储联调由 Actions 继续验证。

手动发布可运行 `npx wrangler login` 后执行 `npm run deploy`。如果使用 Actions，通常不必在本机登录。发布后检查：

```sh
npx wrangler containers list
npx wrangler containers images list
python scripts/smoke_test.py https://venturesimulator.actscal.org --storage durable-object
```

验收脚本会创建一个名为 `Deployment smoke test` 的测试账户，检查创建、读取、更新与旧版本写入冲突。仅检查页面可加 `--read-only`。

Cloudflare 页面位置：**Workers & Pages → Containers** 查看实例与日志；对应 Worker 的 **Observability** 查看错误。如果提示 Unauthorized，先检查 Token 的账号范围和 Containers 权限；如果提示套餐未开通，再去 Workers 订阅页处理，反复重建镜像不能解决账号权限。

容器和持久存储通信采用 [官方 outbound bindings 方式](https://developers.cloudflare.com/containers/configuration/workers-connections/)。当前配置保留新版 `exports` 声明；这是 [官方支持的 Durable Object 配置](https://developers.cloudflare.com/durable-objects/reference/durable-objects-migrations/)，无需套用旧示例重复创建命名空间。

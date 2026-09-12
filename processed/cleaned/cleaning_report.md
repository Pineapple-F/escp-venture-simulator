# 清洗报告

- 数据截止日：`2026-09-02`
- 异常日期仅标记，不删除、不覆盖原日期。
- 经营截止日和处罚公示期限允许晚于数据截止日，不标记为异常。
- 清洗结果写入本目录，`processed/` 根目录和 `data/` 原始文件不变。

## 表级统计

| 表 | 输入行数 | 输出行数 | 删除完全重复 | 输出列数 |
|---|---:|---:|---:|---:|
| `investment_merged` | 124,709 | 124,709 | 0 | 35 |
| `company` | 42,223 | 42,223 | 0 | 32 |
| `events_sample_cn` | 817,560 | 628,084 | 189,476 | 13 |
| `employee` | 108,777 | 99,486 | 9,291 | 13 |
| `partner` | 250,105 | 170,096 | 80,009 | 26 |
| `change` | 83,068 | 65,139 | 17,929 | 6 |
| `legal_person` | 22,549 | 20,386 | 2,163 | 13 |
| `abnormal` | 14,038 | 12,492 | 1,546 | 10 |
| `punish` | 1,080 | 930 | 150 | 19 |

## 融资表拆分

- `investment_events.parquet`：123,998 个唯一事件ID。
- `investment_relations.parquet`：124,709 条融资—投资人关系。
- 多记录事件ID：710 个。
- 关键字段存在来源冲突的事件ID：697 个。
- 事件层优先选择金额为正、来源为 `ie+tb`、非空字段较多的记录。关系层保留全部记录。

## 日期异常

| 表.字段 | 1970年 | 晚于截止日 | 解析前非空 | 解析后非空 | 未解析原文 |
|---|---:|---:|---:|---:|---:|
| `investment_merged.event_date` | 1 | 0 | 124,670 | 124,670 | 0 |
| `investment_merged.pub_date` | 0 | 0 | 41,076 | 41,076 | 0 |
| `company.establish_date` | 20 | 0 | 42,202 | 42,202 | 0 |
| `company.issue_date` | 1 | 0 | 41,831 | 41,831 | 0 |
| `company.operation_startdate` | 20 | 0 | 41,546 | 41,546 | 0 |
| `company.operation_enddate` | 0 | 6,798 | 41,579 | 8,388 | 33,191 |
| `company.cancel_date` | 0 | 0 | 5,923 | 5,923 | 0 |
| `company.revoke_date` | 0 | 0 | 4,740 | 4,740 | 0 |
| `events_sample_cn.event_date` | 118 | 1 | 628,084 | 628,084 | 0 |
| `employee.include_date` | 26 | 0 | 73,033 | 73,033 | 0 |
| `employee.remove_date` | 0 | 0 | 12,946 | 12,946 | 0 |
| `partner.include_date` | 54 | 0 | 161,754 | 161,754 | 0 |
| `partner.remove_date` | 0 | 0 | 27,942 | 27,942 | 0 |
| `change.change_date` | 0 | 1 | 65,133 | 65,133 | 0 |
| `legal_person.include_date` | 0 | 0 | 8,272 | 8,272 | 0 |
| `legal_person.remove_date` | 0 | 0 | 2,522 | 2,522 | 0 |
| `abnormal.included_date` | 0 | 0 | 12,491 | 12,491 | 0 |
| `abnormal.removed_date` | 0 | 0 | 6,573 | 6,573 | 0 |
| `punish.punish_date` | 0 | 0 | 930 | 930 | 0 |
| `punish.public_date` | 0 | 0 | 834 | 834 | 0 |
| `punish.public_deadline` | 0 | 764 | 888 | 888 | 0 |

## 常规业务字段标准化

| 指标 | 数量 |
|---|---:|
| 融资数值金额大于0 | 17,788 |
| 融资原始金额字符串可精确解析 | 74,465 |
| 融资原始金额字符串为模糊表述 | 5,894 |
| 估算金额字符串可精确解析 | 22,831 |
| 企业注册资本可精确解析 | 29,638 |
| 企业实缴资本可精确解析 | 13,291 |
| 股权比例超出0到1 | 0 |
| 处罚金额可精确解析 | 709 |
| 没收金额可精确解析 | 523 |

## 公司ID关联质量

| 表.字段 | 非空唯一ID | 可连接工商主表 | 匹配率 |
|---|---:|---:|---:|
| `events_sample_cn.company_id_anon` | 67,516 | 42,202 | 62.5% |
| `employee.company_id_anon` | 14,693 | 12,421 | 84.5% |
| `partner.company_id_anon` | 19,891 | 12,945 | 65.1% |
| `change.company_id_anon` | 14,113 | 12,280 | 87.0% |
| `legal_person.company_id_anon` | 9,941 | 9,821 | 98.8% |
| `abnormal.company_id_anon` | 6,603 | 4,991 | 75.6% |
| `punish.company_id_anon` | 716 | 484 | 67.6% |
| `investment_merged.invested_company_id_anon` | 28,046 | 9,124 | 32.5% |
| `investment_merged.company_id_anon` | 9,496 | 845 | 8.9% |

## 字段变更

- `company.companyid_anon` → `company_id_anon`。
- `events_sample_cn.entity_id` → `company_id_anon`。
- 每个日期字段增加 `<字段>_is_suspect`；1970年或不应出现的未来日期为 `true`。
- 日期字段无法解析的非空原文保存在 `<字段>_unparsed`，不丢弃期限类文本。
- 任职/存续区间表增加 `invalid_date_interval`。
- 融资关系表增加 `amount_num_is_positive`。
- 原始金额、注册资本和处罚金额增加解析后的数值、币种及模糊标记字段。
- 企业状态、企业类型、省份和股东国家/地区增加规范化派生字段。

# 数据来源与授权登记表

| 数据名称 | 来源 | 许可证/协议 | 预定用途 | 是否进入生产训练 | 责任人复核 |
|---|---|---|---|---|---|
| PPG-DaLiA | UCI ML Repository | CC BY 4.0 | PPG去噪、心率辅助任务 | 待法务复核 | 待填写 |
| Wrist PPG During Exercise v1.0.0 | PhysioNet | ODC Attribution 1.0 | 跨场景验证；已接入`s1_walk` | 否，仅验证 | 已校验官方SHA-256 |
| BIDMC PPG and Respiration | PhysioNet | ODC Attribution 1.0 | 呼吸率辅助验证 | 待法务复核 | 待填写 |
| 公司自采数据 | 待确定 | 用户授权与公司数据制度 | 校准、阈值及外部验证 | 是 | 待填写 |

正式训练前必须补充：数据版本、下载日期、文件哈希、原始许可全文、署名方式、是否包含
敏感个人信息、是否允许商业训练、删除机制及保存期限。未经复核的数据不得进入训练集。

## 已接入记录

- 数据集：Wrist PPG During Exercise v1.0.0；
- 来源：`https://physionet.org/content/wrist/1.0.0/`；
- 对象：`s1_walk.dat/.hea/.atr`；
- 活动：Walking_2 km/h；
- 采样率：256 Hz；
- 样本数：150,529；
- 时长：588.00390625秒；
- 通道数：15；
- `s1_walk.dat` SHA-256：
  `8613a4dcee27e3ad0f489b78c3a60fdb8743907ff31d3c7c644799ba776fc2e5`；
- 校验状态：与数据集官方`SHA256SUMS.txt`一致；
- 当前用途：解析器和信号质量流程验证，不进入风险模型效果宣称。


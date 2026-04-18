# IO_CONTRACT (V2)

## 目标
- 本模块优先服务一线 CA 的日常录入与跟进。
- 输出必须兼容旧字段，同时新增 V2 分层结构，供 Streamlit 展示与 Module 5 消费。

## 时间与状态规则
- 时区统一 `Asia/Shanghai`。
- 相对时间必须换算为绝对日期（`YYYY-MM-DD`）写入 timeline 相关字段。
- `purchase_decision_status` 仅允许：
  - `已成交`
  - `意向待定`
  - `仅浏览`
  - `放弃购买`

## 纠正规则
- 默认：`in addition to`（累加）。
- 仅当出现强反转语义时覆盖（如：不要了/改成了/上次说错了/千万别）。
- 覆盖值需在 `_value` 中标注 `<已纠正>`。
- 品类偏好隔离：某品类禁忌不自动外推到全部品类。

## 输出 JSON（兼容 + 分层）

### 1) 旧字段（必须保留）
- `summary`（string）
- 下列字段均为对象：`{"_value": ..., "_evidence": ..., "_confidence": ...}`
  - `target_recipients`
  - `life_event`
  - `timeline`
  - `aesthetic_preference`
  - `size_height`
  - `budget`
  - `mood`
  - `trend_signals`
  - `next_step_intent`
  - `interested_items`
  - `client_constraints`
  - `purchase_frequency`

### 2) V2 扩展字段（平铺）
- `visit_purpose`
- `purchase_decision_status`
- `positive_signals`
- `negative_reasons`
- `client_timeline`
- `ca_action_item`

> V2 扩展字段与旧字段使用同一对象结构：`_value / _evidence / _confidence`。

### 3) V2 分层字段（必须输出）
- `L1_Client_Profile`
  - `target_recipients`
  - `size_height`
  - `budget`
  - `aesthetic_preference`
- `L2_Constraints`
  - `client_constraints`
- `L3_Visit_Funnel`
  - `visit_purpose`
  - `purchase_decision_status`
  - `positive_signals`
  - `negative_reasons`
  - `interested_items`
  - `trend_signals`
  - `mood`
- `L4_Next_Steps`
  - `client_timeline`
  - `ca_action_item`

## 字段一致性要求
- `L1~L4` 中出现的字段应与平铺字段语义一致。
- 当模型漏掉 V2 字段时，允许回退：
  - `visit_purpose <- life_event`
  - `client_timeline <- timeline`
  - `ca_action_item <- next_step_intent`

## 本地文件输出（当前版本）
- Streamlit `Confirm & Save` 后写入：`module_4/database_mock/profile_*.json`
- 推荐 payload 结构：
  - `saved_at`
  - `meta`
  - `ai_profile_edited`（即上述兼容 + 分层 JSON）
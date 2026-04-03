# Data Source Priority Integration Design

## Goal

把当前“文档宣称支持多行情源，但运行时只真正使用 `akshare`”的状态收敛成真实可运行的多源接入方案，兑现以下能力：

- 日线导入按 `akshare -> tushare -> mootdx` 顺序自动降级
- 股票元数据按独立优先级链路获取，不再绑定到日线源
- `TUSHARE_TOKEN`、`DATA_SOURCE_PRIORITY_DAILY_PRICE`、`DATA_SOURCE_PRIORITY_METADATA` 真正影响运行行为
- 文档、示例配置、测试与代码口径一致

## Approved Scope

### In Scope

- 实现 `TushareDailyPriceFeed`
- 实现 `TushareMetadataFeed`
- 实现 `MootdxDailyPriceFeed`
- 为日线和元数据分别建立 provider 优先级选择与自动降级逻辑
- 把 `import-daily-prices`、研究页实时拉取、`ensure_stock_basic()` 接到新链路
- 补齐 adapter、provider 选择、CLI 和回退路径测试
- 对齐 `README.md`、`.env.example`、runbook 与实际行为

### Out Of Scope

- 本期不做多源并行抓取后的字段级仲裁
- 本期不把 `mootdx` 扩展成 metadata provider
- 本期不重构新闻源选择逻辑
- 本期不引入新的异步任务编排或缓存层

## Requirements Confirmed

- 日线默认优先级：`akshare -> tushare -> mootdx`
- metadata 默认优先级：`akshare -> tushare -> mootdx`
- 可以新增 `tushare` 和 `mootdx` 官方 Python 依赖
- 当首选源失败时必须自动降级，而不是直接报错
- `mootdx` 只承担日线兜底，不承诺 metadata

## Recommended Approach

采用“能力拆分 + 顺序降级”的 provider 设计。

当前仓库已经有统一的 `DailyPriceFeed` / `MetadataFeed` port，也已经通过 `parse_priority()` 暴露了环境变量优先级输入，因此最稳妥的方案不是重做一层新的 provider registry，也不是并行抓多源再仲裁，而是在现有结构上补齐三件事：

1. 让每个 adapter 真实实现自己的能力边界
2. 让日线和 metadata 各自独立读取优先级并逐个尝试
3. 让错误语义从“单源失败直接中断”改成“记录失败并继续降级”

这样既能兑现当前文档承诺，也不会把范围膨胀成一个新的数据质量系统。

## System Architecture

### Layer 1: Provider Capability Boundary

provider 按能力拆分，不再默认“能拉日线就一定能拉 metadata”。

- `AkshareDailyPriceFeed`
  - 支持 `daily_price`
  - 支持 `metadata`
- `TushareDailyPriceFeed`
  - 支持 `daily_price`
- `TushareMetadataFeed`
  - 支持 `metadata`
- `MootdxDailyPriceFeed`
  - 支持 `daily_price`
  - 不支持 `metadata`

这能避免现有 `ensure_stock_basic()` 把 metadata 获取逻辑错误地绑定到日线 feed 上。

### Layer 2: Daily Price Provider Chain

`import_daily_prices()` 和研究页实时刷新路径统一走日线 provider 链。

执行顺序：

1. 解析 `DATA_SOURCE_PRIORITY_DAILY_PRICE`
2. 根据优先级构造候选 provider 列表
3. 依次调用 `fetch_daily_prices()`
4. 首个成功返回非异常结果的 provider 作为本次真实来源
5. 所有 provider 都失败时抛出聚合错误

默认顺序为：

- `akshare`
- `tushare`
- `mootdx`

### Layer 3: Metadata Provider Chain

`ensure_stock_basic()` 不再从日线 feed 上猜测 metadata 能力，而是显式走 metadata provider 链。

执行顺序：

1. 解析 `DATA_SOURCE_PRIORITY_METADATA`
2. 根据优先级构造 metadata provider 列表
3. 依次调用 `fetch_stock_metadata()`
4. 首个成功结果用于创建或更新 `StockBasic`
5. 若全部失败，则退回最小占位 metadata，并把失败原因写入日志

默认顺序同样为：

- `akshare`
- `tushare`
- `mootdx`

但 `mootdx` 在 metadata 链中会被识别为“不支持此能力”并跳过。

### Layer 4: Unified Error And Fallback Semantics

本期的关键不是“完全不失败”，而是“失败有边界且可诊断”。

要求：

- 单个 provider 失败不立即中断
- 聚合错误必须包含每个 provider 的失败摘要
- metadata 全失败时不阻塞日线导入
- 成功源必须反映在 `data_source` 和任务日志里

这样可以把“当前代码和文档口径不一致”的问题，转成“真实可运行且可解释的降级行为”。

## Component Design

### `apps/api/src/swinginsight/ingest/adapters/akshare_daily_price_feed.py`

保留现有实现，继续作为第一优先级 provider。

要求：

- 不改变现有统一字段输出
- 保持 `fetch_stock_metadata()` 能力
- 在新 provider 选择测试中作为默认首选源

### `apps/api/src/swinginsight/ingest/adapters/tushare_daily_price_feed.py`

新增真实 `tushare` 日线拉取。

统一输出至少包含：

- `stock_code`
- `trade_date`
- `open_price`
- `high_price`
- `low_price`
- `close_price`
- `volume`
- `amount`
- `change_pct`
- `pre_close_price`
- `adj_type`
- `is_trading_day`
- `data_source = "tushare"`

字段缺失策略：

- 上游未提供时允许 `None`
- 不为了“看起来完整”而伪造 turnover 或行业信息

### `apps/api/src/swinginsight/ingest/adapters/tushare_metadata_feed.py`

新增真实 metadata 拉取。

最小保证字段：

- `stock_code`
- `stock_name`
- `market`
- `industry`
- `concept_tags`

如果 `tushare` 无法稳定提供 `concept_tags`，可以先返回空列表，但不能再抛 `NotImplementedError`。

### `apps/api/src/swinginsight/ingest/adapters/mootdx_daily_price_feed.py`

新增真实 `mootdx` 日线兜底实现。

要求：

- 输出与其他日线 provider 相同的标准字段
- 允许部分字段为 `None`
- 明确 `data_source = "mootdx"`
- 不提供 metadata 方法

### `apps/api/src/swinginsight/jobs/import_market_data.py`

这是本次改造的主入口。

需要拆成两个概念清晰的选择器：

- 日线 provider 选择器
- metadata provider 选择器

建议新增：

- 根据优先级字符串构造 provider 列表的 helper
- 逐个尝试 provider 的 helper
- 聚合错误对象或错误格式化 helper

保留现有 `import_daily_prices()` 对外接口，避免上层调用方大面积变化。

### `apps/api/src/swinginsight/settings.py`

补齐配置读取，让这些 env 不只存在于文档里：

- `TUSHARE_TOKEN`
- `DATA_SOURCE_PRIORITY_DAILY_PRICE`
- `DATA_SOURCE_PRIORITY_METADATA`

这里不需要做复杂配置系统，只要让运行时代码有一处清晰的配置入口即可。

## Data Flow

### Daily Price Import Flow

1. 调用 `import_daily_prices(stock_code, start, end, demo=False)`
2. 读取 `DATA_SOURCE_PRIORITY_DAILY_PRICE`
3. 构造 `akshare -> tushare -> mootdx` provider 列表
4. 逐个调用 `fetch_daily_prices()`
5. 首个成功 provider 返回统一 rows
6. `DailyPriceImporter` 执行 upsert
7. `TaskRunLog` 和 `daily_price.data_source` 反映实际成功源

### Stock Metadata Flow

1. 调用 `ensure_stock_basic(session, stock_code, ...)`
2. 读取 `DATA_SOURCE_PRIORITY_METADATA`
3. 构造 metadata provider 列表
4. 逐个调用 `fetch_stock_metadata()`
5. 成功则更新 `StockBasic`
6. 全失败则写最小占位 metadata，并记录失败信息

## Failure Handling

### Provider Failure Rules

- 网络错误：继续降级到下一个 provider
- 鉴权错误，例如缺少 `TUSHARE_TOKEN`：继续降级
- 上游返回空数据：
  - 若属于“合法空区间”，按成功处理
  - 若属于 provider 明显异常，由 adapter 转成明确异常
- 所有 provider 失败：抛聚合错误，包含 provider 名和失败摘要

### Metadata Fallback Rules

metadata 是增强能力，不是日线导入的硬前置。

因此：

- metadata 全失败时，`StockBasic` 允许回退为最小占位记录
- 但必须显式体现这是 fallback，而不是默默伪装成真实 metadata

## Testing Strategy

### Adapter Tests

需要新增或更新以下测试：

- `TushareDailyPriceFeed` 能把上游 payload 映射成统一字段
- `TushareMetadataFeed` 能返回标准 metadata 结构
- `MootdxDailyPriceFeed` 能返回标准日线结构
- `AkshareDailyPriceFeed` 现有测试继续保留

### Provider Selection Tests

需要覆盖：

- 默认顺序为 `akshare,tushare,mootdx`
- env 覆盖后按新顺序执行
- 第一个 provider 失败时自动降级到第二个
- 前两个 provider 失败时自动降级到第三个
- metadata provider 顺序独立于日线 provider 顺序

### Importer And CLI Tests

需要覆盖：

- `import-daily-prices` 在首选源失败时仍能成功导入
- `task_run_log` 反映实际成功源
- `ensure_stock_basic()` 在 metadata 全失败时仍能创建最小 `StockBasic`

### Documentation Consistency Check

至少需要让这些文件的口径完全一致：

- `.env.example`
- `README.md`
- `docs/runbooks/dev-setup.md`
- 如有必要，补充到 `docs/2026-04-03-delivery-milestones.md`

## Acceptance Criteria

- 默认配置下，日线真实按 `akshare -> tushare -> mootdx` 降级
- 默认配置下，metadata 真实按 `akshare -> tushare -> mootdx` 降级
- `TUSHARE_TOKEN` 缺失时，不会让整个导入流程直接失败
- `akshare` 不可用时，`tushare` 可接管
- `akshare` 和 `tushare` 都不可用时，`mootdx` 可兜底日线
- 代码中不再存在 `TushareDailyPriceFeed`、`TushareMetadataFeed`、`MootdxDailyPriceFeed` 的 `NotImplementedError`
- 文档不再宣称一套优先级，而代码实际执行另一套优先级

## Risks And Tradeoffs

- `tushare` 和 `mootdx` 的字段覆盖度与 `akshare` 不完全一致，因此统一 schema 必须容忍部分空字段
- metadata 全失败时允许 fallback，会保留系统可用性，但也意味着元数据质量与行情质量解耦
- 本期不做多源仲裁，因此“首个成功源”不一定是“字段最完整源”，但这比当前的假支持状态更真实、更可维护

## Next Step

这份 design 通过后，下一步应进入 implementation plan，按 TDD 拆成：

1. adapter tests and implementations
2. provider selection and fallback logic
3. importer and CLI integration
4. config and docs alignment

# Pattern Similarity Engine V1 Design

## Goal

把当前“波段对波段”的相似度实现升级为“固定 7 日滑窗检索 + 波段展示”的混合引擎，使相似样本同时满足三件事：

- 检索单元长度稳定，分数更可比较
- 页面仍然围绕历史波段展示，不打断现有研究页心智
- 相似样本可以直接产出后续 `1/3/5/10` 日统计，进入预测与研究链路

## Approved Scope

### In Scope

- 新增固定 `7` 个交易日滑窗样本体系
- 新增滑窗特征、后续收益、查询缓存表
- 新增滑窗预计算作业与 CLI
- 查询时从当前最终波段内自动选择“核心走势代表窗”
- 两阶段检索：粗召回 + 精排
- 命中滑窗映射回历史波段展示
- 研究页与预测接口输出更细的相似度分项与未来统计
- K 线对比弹窗改成以“相似 7 日窗”为高亮中心

### Out Of Scope

- 本期不引入 FAISS、HNSW 或外部向量库
- 本期不引入深度学习表征学习
- 本期不做多周期联合检索
- 本期不把新闻、行业、概念上下文纳入相似度总分
- 本期不重做整套前端视觉，只改信息结构和文案

## Recommended Approach

采用“保留 `SwingSegment` 展示层，新增 `PatternWindow` 检索层”的双层架构。

当前系统已经围绕 `SwingSegment` 建立了研究页、相似样本卡片、局部 K 线对比和预测接口。如果直接把所有页面展示切成“固定 7 日窗口”，用户会失去波段级语义；但如果继续只以波段为检索单元，样本长度和结构差异太大，排序稳定性不足。

因此本期设计如下：

- 底层检索单元：固定 `7` 个交易日滑窗
- 当前查询入口：当前最新最终波段
- 当前查询窗：从当前波段内自动挑一个“代表性 7 日窗”
- 结果展示单元：历史波段
- 同一历史波段允许多个高分滑窗同时出现

这样既解决“长度不可比”的算法问题，也保留“波段复盘”的用户心智。

## System Architecture

### Layer 1: Current Segment Selector

预测入口仍然先找到当前股票最新一条 `is_final=true` 的 `SwingSegment`。

如果当前波段长度大于等于 `7`，系统在该波段内部枚举所有连续 `7` 日子窗，并为每个子窗计算一个 `representative_score`。评分最高的子窗作为查询窗。

如果当前波段长度小于 `7`，系统以波段中点为核心，向前后补齐相邻交易日，构造一个固定 `7` 根的查询窗。展示时仍只高亮真实波段边界。

### Layer 2: Pattern Retrieval

查询窗进入新的 `pattern_window` 检索层。检索流程分两步：

1. 粗召回
2. 精排

粗召回不追求最终精度，只负责从全市场滑窗中筛出足够可信的候选；精排再对候选做完整的多维相似度重算。

### Layer 3: Segment Presentation

精排后的每个命中样本都保留两层身份：

- `pattern_window`: 真正命中的 7 日窗
- `swing_segment`: 该窗口所属的历史最终波段

研究页继续展示历史波段信息，但会明确标注：

- 相似窗口时间段
- 所属波段时间段

### Layer 4: Future Outcome Statistics

每个历史滑窗预计算后续 `1/3/5/10` 日收益、最大上冲和最大回撤。查询结果可以直接输出：

- 单样本未来表现
- 相似样本组统计

这一步是把“相似度展示”升级成“可研究、可预测、可回测”的关键。

## Data Model

## `pattern_window`

一条记录代表一个固定长度滑窗。

建议字段：

- `id`
- `window_uid`
- `stock_code`
- `segment_id`
- `start_date`
- `end_date`
- `window_size`
- `start_close`
- `end_close`
- `period_pct_change`
- `highest_day_pos`
- `lowest_day_pos`
- `trend_label`
- `feature_version`

说明：

- `segment_id` 可空。窗口中心点能映射到最终波段时写入该字段。
- `trend_label` 是轻量上下文标签，用于粗召回剪枝。

## `pattern_feature`

存检索和精排所需的结构化特征。

建议字段：

- `id`
- `window_id`
- `price_seq_json`
- `return_seq_json`
- `candle_feat_json`
- `volume_seq_json`
- `turnover_seq_json`
- `trend_context_json`
- `vola_context_json`
- `coarse_vector_json`
- `feature_version`

说明：

- `price_seq_json` 存归一化价格轨迹与累计收益轨迹
- `candle_feat_json` 存 `[body_ratio, upper_ratio, lower_ratio, close_pos, is_bull] * 7`
- `coarse_vector_json` 用于第一阶段粗召回

## `pattern_future_stat`

存滑窗未来表现。

建议字段：

- `id`
- `window_id`
- `ret_1d`
- `ret_3d`
- `ret_5d`
- `ret_10d`
- `max_up_3d`
- `max_dd_3d`
- `max_up_5d`
- `max_dd_5d`
- `max_up_10d`
- `max_dd_10d`

## `pattern_match_result`

存查询缓存。

建议字段：

- `id`
- `query_signature`
- `query_window_id`
- `target_window_id`
- `rank_no`
- `total_similarity`
- `sim_price`
- `sim_candle`
- `sim_volume`
- `sim_turnover`
- `sim_trend`
- `sim_vola`
- `feature_version`

本期缓存不是强依赖，但表结构要先落下来，为后续重复查询缓存预留位置。

## Window Construction

所有样本统一为 `7` 个交易日。

生成规则：

- 仅使用 `daily_price` 中真实存在的交易日
- 连续取 `7` 条同股票的交易记录
- 若特征计算需要的背景数据不足，例如无法计算 `ma60` 或 `atr10`，则该窗口不入库

窗口和波段的关系：

- 取窗口中心交易日
- 找该日期覆盖到的 `SwingSegment`
- 命中则写入 `segment_id`

这样窗口始终是检索单位，波段只是展示映射。

## Representative Window Selection

当前查询窗不是当前波段最后 `7` 根，也不是人工指定，而是从当前波段内部自动选择“最能代表该波段核心走势”的 `7` 日窗。

评分由以下部分组成：

- `0.45 *` 子窗价格轨迹与整段轨迹的相似度
- `0.25 *` 子窗 K 线结构与整段核心结构的相似度
- `0.20 *` 子窗中心点接近波段中点的得分
- `0.10 *` 子窗振幅覆盖度

这个规则的目的不是预测末端，而是找到“最典型的一段走势”，对应用户已确认的“核心走势优先”。

## Feature Engineering

### Price Path Features

- `norm_close[t] = close[t] / close[0]`
- `ret[t] = close[t] / close[t-1] - 1`
- `cum_ret[t] = close[t] / close[0] - 1`
- `highest_day_pos`
- `lowest_day_pos`

### Candle Geometry Features

每根 K 线拆成：

- `body_ratio`
- `upper_ratio`
- `lower_ratio`
- `close_pos`
- `is_bull`

窗口级特征直接按日顺序拼接。

### Volume Features

- `vol_ratio = volume / window_mean_volume`
- `vol_change = volume / prev_volume - 1`

### Turnover Features

- `turnover_ratio = turnover / window_mean_turnover`
- `turnover_change = turnover / prev_turnover - 1`

### Trend Context Features

在窗口末端计算：

- `close/ma5`
- `close/ma10`
- `close/ma20`
- `close/ma60`
- `slope_ma5`
- `slope_ma10`
- `slope_ma20`
- `trend_label_onehot`

### Volatility Context Features

- `atr5`
- `atr10`
- `amp`
- `avg_intraday_amp`
- `max_intraday_amp`

## Similarity Engine

### Stage 1: Coarse Retrieval

粗召回先做轻量剪枝，再做向量相似。

剪枝维度：

- `window_size == 7`
- `trend_label` 相同优先
- `period_pct_change` 同方向优先
- `amplitude_bucket` 接近优先
- `bull_ratio_bucket` 接近优先

然后对剪枝后的候选计算 `coarse_vector` 余弦相似，取 Top `300` 到 `500`。

### Stage 2: Fine Ranking

对召回结果重算六个分项：

- `sim_price`
- `sim_candle`
- `sim_volume`
- `sim_turnover`
- `sim_trend`
- `sim_vola`

### Scoring Formula

第一版固定权重：

- `0.35 * sim_price`
- `0.25 * sim_candle`
- `0.15 * sim_volume`
- `0.08 * sim_turnover`
- `0.12 * sim_trend`
- `0.05 * sim_vola`

### Component Definitions

`sim_price`

- 价格路径距离使用自实现 DTW 接口
- 第一版先实现普通 DTW
- 接口保持可替换，后续可无缝升级到 Soft-DTW

`sim_candle`

- `flatten(candle_feat)` 做余弦相似
- 再加：
  - 阳线/阴线排列一致率
  - 最高点/最低点位置差惩罚

`sim_volume`

- `0.6 * cosine(vol_ratio)`
- `0.4 * pearson(vol_ratio)`

`sim_turnover`

- `0.7 * cosine(turnover_ratio)`
- `0.3 * pearson(turnover_ratio)`

`sim_trend`

- `cosine(trend_context)`

`sim_vola`

- `exp(-beta * euclidean_distance(vola_context))`

## API Design

现有 `SimilarCase` 结构需要升级，明确区分“命中的相似窗口”和“所属历史波段”。

每个相似结果建议返回：

- `window_id`
- `window_stock_code`
- `window_start_date`
- `window_end_date`
- `window_size`
- `segment_id`
- `segment_stock_code`
- `segment_start_date`
- `segment_end_date`
- `segment_pct_change`
- `score`
- `price_score`
- `candle_score`
- `volume_score`
- `turnover_score`
- `trend_score`
- `vola_score`
- `return_1d`
- `return_3d`
- `return_5d`
- `return_10d`
- `max_up_5d`
- `max_dd_5d`
- `max_up_10d`
- `max_dd_10d`

预测与研究页摘要还要新增一组相似样本统计：

- `sample_count`
- `future_1d_mean`
- `future_1d_median`
- `future_1d_win_rate`
- `future_3d_mean`
- `future_5d_mean`
- `future_10d_mean`
- `future_5d_max_dd_median`
- `future_10d_max_dd_median`

## Frontend Design

### Similar Case Card

卡片继续按“历史样本”展示，但文案必须显式区分：

- `相似窗口`
- `所属波段`

分项相似度改为：

- 价格
- K线形态
- 成交量
- 换手率
- 趋势背景
- 波动率

### Compare Modal

弹窗展示两张只读图：

- 当前代表性 `7` 日窗及其前后各 `10` 个交易日
- 历史命中 `7` 日窗及其前后各 `10` 个交易日

橙色高亮代表真正参与相似度计算的 `7` 日窗。若能映射到波段，可用更浅层标识波段范围，但视觉焦点仍然是滑窗。

## CLI And Backfill

新增三类作业：

- `build-pattern-windows`
- `materialize-pattern-features`
- `materialize-pattern-future-stats`

要求：

- 先支持单股增量
- 再支持全量回填
- 支持价格更新后按股票局部重算

## Compatibility And Model Versioning

旧模型版本继续保留为 `prediction:v1`。

新引擎使用独立版本，例如：

- `pattern:v1`
- `prediction:v2-pattern`

不要把新旧口径混写到同一个 `model_version` 下，否则历史结果不可解释。

## Testing Strategy

必须覆盖：

- schema/迁移测试
- 固定 7 日窗切片测试
- 代表窗选择测试
- 相似度分项排序测试
- 滑窗到波段映射测试
- API 结构测试
- 前端卡片/弹窗渲染测试
- 真实数据单股 smoke test

## Rollout Plan

建议按以下顺序上线：

1. 新表与 CLI 落地
2. 单股回填验证
3. API 接口切换到新结果
4. 前端文案与对比弹窗切换
5. 小范围股票集回测
6. 全量回填

## Success Criteria

这版上线后应满足：

- 相似样本的 K 线数量稳定为同一口径
- 页面不再把“短窗口相似”误解为“整段波段完全相似”
- `Top K` 相似样本能直接输出可解释的未来收益统计
- 同一历史波段允许多个不同窗口命中
- 预测链路能以 `pattern:v1` 独立验证，不污染旧版本结果

# Pattern Similarity Precision Pass Design

## Goal

在不改动数据库 schema 的前提下，修正当前滑窗相似度链路里最直接影响精准度的缺陷，使 `/predictions` 返回的 Top-K 相似样本更可信、更稳定、更符合人工研究判断。

本轮范围只覆盖三件事：

- 消除候选检索中的未来信息泄漏
- 改进代表窗选择，优先选出波段核心走势
- 对最终结果做去重和多样性约束，避免单一波段或单一股票占满 Top-K

## Current Problems

### Future Leakage

`PatternSimilarityService.find_similar_windows()` 当前从全量 `pattern_window` 中选候选，只排除查询窗本身，没有限制候选结束时间必须早于查询时间点。这样会让预测接口在历史回测时看到未来样本，结果不可信。

### Weak Representative Window Selection

`select_representative_window()` 当前只按窗口中心接近波段中点、以及窗口涨跌幅接近整段涨跌幅排序，和设计文档中定义的“核心走势代表窗”偏差较大。查询窗质量不足会直接拖低后续精排效果。

### Duplicate-Dominated Results

最终结果当前只按分数排序，同一历史波段的多个相邻高分窗口都可以进入 Top-K，同一股票也会被明显偏置。这降低了研究页的样本多样性和解释价值。

### Candle Turning Point Mismatch

`sim_candle` 依赖最高点/最低点位置，但服务层目前从 `price_seq` 反推这些位置，而不是读取 `PatternWindow` 中真实的高低点位置，导致 K 线形态惩罚项偏离真实极值结构。

## Design

### Candidate Time Filter

候选窗口必须满足：

- `candidate.id != query_window.id`
- `candidate.end_date < query_window.start_date`

第二个条件是本轮时序约束的核心。它保证候选窗口在时间上完整发生于查询窗之前，避免未来泄漏，也避免同一时段重叠窗口带来的伪高分。

### Representative Window Scoring

对当前 `SwingSegment` 下所有候选 7 日窗计算 `representative_score`，取分数最高者作为查询窗。

评分公式：

- `0.45 * price_similarity`
- `0.25 * candle_similarity`
- `0.20 * midpoint_score`
- `0.10 * amplitude_coverage_score`

各分项定义如下：

`price_similarity`

- 取当前子窗的 `price_seq`
- 取当前整段价格轨迹，重采样到 7 个点
- 使用现有 `trajectory_similarity` 计算相似度

`candle_similarity`

- 取当前子窗的 `candle_feat`
- 对整段 K 线做等距采样，构造整段 candle 原型
- 复用现有 `sim_candle` 的打分逻辑，但输入为子窗特征 vs 原型特征

`midpoint_score`

- 计算子窗中心点与波段中点的天数差
- 用线性衰减映射到 `0..1`
- 最靠近中点得分最高

`amplitude_coverage_score`

- 计算子窗振幅与整段振幅的比值
- 当子窗振幅接近整段核心振幅时得分更高
- 采用 `min(window_amp / segment_amp, 1.0)` 的饱和形式

### Result Deduplication

精排完成后，按总分从高到低遍历候选，并应用两层约束：

- 同一 `segment_id` 只保留最高分窗口
- 同一 `stock_code` 最多保留 2 个窗口

若 `segment_id` 为空，则退化为按 `window_id` 作为唯一实体处理，不额外合并。

这样可以保留“同一股票可出现多个历史阶段”的研究价值，同时防止结果被同一波段切片淹没。

### Turning Point Source of Truth

`highest_day_pos` / `lowest_day_pos` 在精排时改为优先读取 `PatternWindow` 上的真实字段，不再从 `price_seq` 推导。`_feature_payload()` 改成同时接收 `PatternWindow` 和 `PatternFeature`，由 `PatternWindow` 提供 turning-point 位置。

## Files Affected

- `apps/api/src/swinginsight/services/pattern_similarity_service.py`
- `apps/api/tests/services/test_pattern_similarity_service.py`
- `apps/api/tests/integration/test_pattern_similarity_flow.py`

如果需要把代表窗打分拆分为更小的纯函数，可新增：

- `apps/api/src/swinginsight/domain/prediction/pattern_query_window.py`
- `apps/api/tests/domain/test_pattern_query_window.py`

本轮优先在现有 service 中完成，只有当测试驱动下 service 变得明显臃肿时，才拆出独立 domain 模块。

## Testing Strategy

新增或强化以下测试：

- 未来窗口不会被召回
- 代表窗优先选出波段核心走势，而非简单靠近中点
- 同一 `segment_id` 的多个高分窗口只保留一个
- 同一 `stock_code` 在结果集中最多出现两个窗口
- `sim_candle` 的 turning-point 惩罚读取真实窗口高低点位置

现有端到端测试继续保留，用于确认 `/predictions` 仍返回完整结构。

## Non-Goals

- 本轮不引入学习排序、权重学习或向量库
- 本轮不改动 `pattern_feature` / `pattern_window` schema
- 本轮不做离线回测和评估报表
- 本轮不调整前端展示文案

## Success Criteria

上线后应满足：

- 查询结果不再包含查询时点之后的窗口
- 代表窗更稳定地落在当前波段核心走势区域
- Top-K 结果的波段和股票分布更均衡
- 不改变现有 API 结构

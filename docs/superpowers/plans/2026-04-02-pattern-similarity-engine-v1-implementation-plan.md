# Pattern Similarity Engine V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有“波段对波段”相似度升级成“固定 7 日滑窗检索 + 波段展示”的完整第一版，实现新表结构、预计算作业、相似度引擎、API 输出和前端展示改造。

**Architecture:** 保留现有 `SwingSegment` 作为研究页与预测页的展示骨架，引入独立的 `pattern_window` 检索层。查询时先从当前最终波段中自动选择代表性 `7` 日窗，再通过粗召回与精排找到历史命中滑窗，并映射回历史波段输出。预测概率与样本统计改由 `pattern:v1` 驱动。

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, pytest, TypeScript, React, Vitest

---

## Task 1: Add Pattern Similarity Schema

**Files:**
- Create: `apps/api/src/swinginsight/db/models/pattern.py`
- Modify: `apps/api/src/swinginsight/db/models/__init__.py`
- Create: `apps/api/alembic/versions/0004_pattern_similarity_v1.py`
- Create: `apps/api/tests/db/test_pattern_schema.py`

- [ ] **Step 1: Write the failing schema test**

```python
def test_pattern_tables_exist(session):
    inspector = sa.inspect(session.bind)
    assert "pattern_window" in inspector.get_table_names()
    assert "pattern_feature" in inspector.get_table_names()
    assert "pattern_future_stat" in inspector.get_table_names()
    assert "pattern_match_result" in inspector.get_table_names()


def test_pattern_window_allows_multiple_windows_per_segment(session):
    segment_id = seed_segment(session)
    create_pattern_window(session, segment_id=segment_id, start_date=date(2024, 1, 1), end_date=date(2024, 1, 9))
    create_pattern_window(session, segment_id=segment_id, start_date=date(2024, 1, 2), end_date=date(2024, 1, 10))
    assert session.scalar(select(func.count()).select_from(PatternWindow).where(PatternWindow.segment_id == segment_id)) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest apps/api/tests/db/test_pattern_schema.py -v`

Expected: FAIL，提示缺少新模型或新表。

- [ ] **Step 3: Write minimal implementation**

在 `apps/api/src/swinginsight/db/models/pattern.py` 新增：

- `PatternWindow`
- `PatternFeature`
- `PatternFutureStat`
- `PatternMatchResult`

关键要求：

- `PatternWindow.window_uid` 唯一
- `PatternFeature.window_id` 唯一
- `PatternFutureStat.window_id` 唯一
- `PatternMatchResult` 对 `(query_signature, target_window_id)` 建唯一约束
- 索引覆盖：
  - `stock_code, start_date, end_date`
  - `segment_id`
  - `window_size`
  - `feature_version`

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd apps/api
../../.venv/bin/alembic -c alembic.ini upgrade head
cd ../..
.venv/bin/pytest apps/api/tests/db/test_pattern_schema.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/swinginsight/db/models/pattern.py apps/api/src/swinginsight/db/models/__init__.py apps/api/alembic/versions/0004_pattern_similarity_v1.py apps/api/tests/db/test_pattern_schema.py
git commit -m "feat: add pattern similarity schema"
```

## Task 2: Build Pattern Window Generation And Future Stats

**Files:**
- Create: `apps/api/src/swinginsight/services/pattern_window_service.py`
- Create: `apps/api/src/swinginsight/jobs/build_pattern_windows.py`
- Create: `apps/api/src/swinginsight/jobs/materialize_pattern_future_stats.py`
- Modify: `apps/api/src/swinginsight/jobs/cli.py`
- Create: `apps/api/tests/services/test_pattern_window_service.py`
- Create: `apps/api/tests/jobs/test_pattern_jobs.py`

- [ ] **Step 1: Write the failing window generation test**

```python
def test_build_pattern_windows_creates_fixed_7_bar_windows_with_segment_mapping(session):
    seed_prices(session, stock_code="000001", count=80)
    segment_id = seed_segment(session, stock_code="000001", start_date=date(2024, 1, 15), end_date=date(2024, 2, 20))

    result = PatternWindowService(session).build_windows(stock_code="000001", window_size=7)

    assert result.created > 0
    sample = session.scalar(select(PatternWindow).where(PatternWindow.segment_id == segment_id))
    assert sample is not None
    assert sample.window_size == 7
```

- [ ] **Step 2: Write the failing future stat test**

```python
def test_materialize_pattern_future_stats_persists_forward_returns(session):
    window_id = seed_pattern_window(session, stock_code="000001", end_date=date(2024, 1, 10))
    seed_future_prices(session, stock_code="000001", start_date=date(2024, 1, 10), closes=[10.0, 10.5, 10.2, 11.0, 11.3, 10.9, 11.4, 11.8, 11.7, 12.0, 12.1])

    result = PatternWindowService(session).materialize_future_stats(stock_code="000001")

    stats = session.scalar(select(PatternFutureStat).where(PatternFutureStat.window_id == window_id))
    assert result.updated >= 1
    assert stats.ret_1d is not None
    assert stats.ret_10d is not None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/pytest apps/api/tests/services/test_pattern_window_service.py apps/api/tests/jobs/test_pattern_jobs.py -v`

Expected: FAIL

- [ ] **Step 4: Write minimal implementation**

新增 `PatternWindowService`，至少实现：

```python
class PatternWindowService:
    def build_windows(self, *, stock_code: str, window_size: int = 7) -> PatternBuildResult: ...
    def materialize_future_stats(self, *, stock_code: str) -> PatternFutureStatResult: ...
```

实现要求：

- 窗口固定 `7` 根
- 中心日期映射到 `SwingSegment.segment_id`
- 未来统计覆盖 `1/3/5/10` 日收益和 `3/5/10` 日最大上冲/回撤
- CLI 新增：
  - `build-pattern-windows --stock-code`
  - `materialize-pattern-future-stats --stock-code`

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest apps/api/tests/services/test_pattern_window_service.py apps/api/tests/jobs/test_pattern_jobs.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/swinginsight/services/pattern_window_service.py apps/api/src/swinginsight/jobs/build_pattern_windows.py apps/api/src/swinginsight/jobs/materialize_pattern_future_stats.py apps/api/src/swinginsight/jobs/cli.py apps/api/tests/services/test_pattern_window_service.py apps/api/tests/jobs/test_pattern_jobs.py
git commit -m "feat: add pattern window generation jobs"
```

## Task 3: Materialize Pattern Features And Similarity Functions

**Files:**
- Create: `apps/api/src/swinginsight/domain/prediction/pattern_features.py`
- Create: `apps/api/src/swinginsight/domain/prediction/pattern_similarity.py`
- Create: `apps/api/src/swinginsight/services/pattern_feature_service.py`
- Create: `apps/api/src/swinginsight/jobs/materialize_pattern_features.py`
- Modify: `apps/api/src/swinginsight/jobs/cli.py`
- Create: `apps/api/tests/domain/test_pattern_features.py`
- Create: `apps/api/tests/domain/test_pattern_similarity.py`
- Create: `apps/api/tests/services/test_pattern_feature_service.py`

- [ ] **Step 1: Write the failing feature extraction tests**

```python
def test_build_pattern_features_outputs_expected_component_shapes():
    features = build_pattern_features(window_rows)
    assert len(features["price_seq"]) == 7
    assert len(features["return_seq"]) == 7
    assert len(features["candle_feat"]) == 35
    assert len(features["trend_context"]) >= 8
    assert len(features["vola_context"]) >= 5


def test_build_pattern_features_skips_windows_without_context():
    assert build_pattern_features(short_history_rows) is None
```

- [ ] **Step 2: Write the failing similarity tests**

```python
def test_price_similarity_prefers_closer_path():
    assert sim_price(current, close_match) > sim_price(current, noisy_match)


def test_candle_similarity_penalizes_reversed_bull_bear_order():
    assert sim_candle(current, aligned) > sim_candle(current, reversed_order)


def test_total_similarity_uses_all_components():
    result = calc_pattern_similarity(query_features, sample_features)
    assert set(result) >= {"total_similarity", "sim_price", "sim_candle", "sim_volume", "sim_turnover", "sim_trend", "sim_vola"}
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/pytest apps/api/tests/domain/test_pattern_features.py apps/api/tests/domain/test_pattern_similarity.py apps/api/tests/services/test_pattern_feature_service.py -v`

Expected: FAIL

- [ ] **Step 4: Write minimal implementation**

`build_pattern_features()` 至少产出：

- `price_seq`
- `return_seq`
- `candle_feat`
- `volume_seq`
- `turnover_seq`
- `trend_context`
- `vola_context`
- `coarse_vector`

`calc_pattern_similarity()` 至少产出：

```python
{
    "total_similarity": ...,
    "sim_price": ...,
    "sim_candle": ...,
    "sim_volume": ...,
    "sim_turnover": ...,
    "sim_trend": ...,
    "sim_vola": ...,
}
```

权重固定为：

- `0.35 price`
- `0.25 candle`
- `0.15 volume`
- `0.08 turnover`
- `0.12 trend`
- `0.05 vola`

CLI 新增：

- `materialize-pattern-features --stock-code`

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest apps/api/tests/domain/test_pattern_features.py apps/api/tests/domain/test_pattern_similarity.py apps/api/tests/services/test_pattern_feature_service.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/swinginsight/domain/prediction/pattern_features.py apps/api/src/swinginsight/domain/prediction/pattern_similarity.py apps/api/src/swinginsight/services/pattern_feature_service.py apps/api/src/swinginsight/jobs/materialize_pattern_features.py apps/api/src/swinginsight/jobs/cli.py apps/api/tests/domain/test_pattern_features.py apps/api/tests/domain/test_pattern_similarity.py apps/api/tests/services/test_pattern_feature_service.py
git commit -m "feat: add pattern feature materialization and similarity core"
```

## Task 4: Integrate Pattern Search Into Prediction Pipeline

**Files:**
- Create: `apps/api/src/swinginsight/services/pattern_similarity_service.py`
- Modify: `apps/api/src/swinginsight/services/prediction_service.py`
- Modify: `apps/api/src/swinginsight/api/routes/predictions.py`
- Modify: `apps/api/src/swinginsight/api/routes/stocks.py`
- Create: `apps/api/tests/services/test_pattern_similarity_service.py`
- Modify: `apps/api/tests/domain/test_prediction_service.py`
- Modify: `apps/api/tests/api/test_turning_points_api.py`

- [ ] **Step 1: Write the failing representative window selection test**

```python
def test_select_representative_window_prefers_core_shape_not_last_7_bars(session):
    current_segment = seed_segment_with_distinct_middle_pattern(session)
    selected = PatternSimilarityService(session).select_representative_window(current_segment)
    assert selected.start_date == date(2024, 2, 5)
    assert selected.end_date == date(2024, 2, 13)
```

- [ ] **Step 2: Write the failing prediction integration test**

```python
def test_prediction_service_returns_pattern_similarity_cases(session):
    result = PredictionService(session).predict("000001", date(2024, 6, 28))
    sample = result.similar_cases[0]
    assert sample.window_id is not None
    assert sample.window_start_date is not None
    assert sample.segment_id is not None
    assert sample.candle_score is not None
    assert sample.trend_score is not None
    assert result.group_stat["sample_count"] >= 1
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/pytest apps/api/tests/services/test_pattern_similarity_service.py apps/api/tests/domain/test_prediction_service.py apps/api/tests/api/test_turning_points_api.py -v`

Expected: FAIL

- [ ] **Step 4: Write minimal implementation**

`PatternSimilarityService` 至少实现：

- `select_representative_window(current_segment)`
- `find_similar_windows(stock_code, predict_date, top_n=300, top_k=20)`
- `summarize_future_returns(similar_windows)`

`PredictionService` 改为：

- 用 `PatternSimilarityService` 替代原 `SimilarityStore.find_top_k`
- `PREDICTION_VERSION` 升级为 `prediction:v2-pattern`
- `SimilarCase` 扩展为同时携带滑窗字段和波段字段

API 至少返回：

- `window_start_date`
- `window_end_date`
- `segment_start_date`
- `segment_end_date`
- `price_score`
- `candle_score`
- `volume_score`
- `turnover_score`
- `trend_score`
- `vola_score`
- `group_stat`

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest apps/api/tests/services/test_pattern_similarity_service.py apps/api/tests/domain/test_prediction_service.py apps/api/tests/api/test_turning_points_api.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/swinginsight/services/pattern_similarity_service.py apps/api/src/swinginsight/services/prediction_service.py apps/api/src/swinginsight/api/routes/predictions.py apps/api/src/swinginsight/api/routes/stocks.py apps/api/tests/services/test_pattern_similarity_service.py apps/api/tests/domain/test_prediction_service.py apps/api/tests/api/test_turning_points_api.py
git commit -m "feat: switch prediction search to pattern similarity engine"
```

## Task 5: Update Research Page And Compare Modal

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/components/similar-case-list.tsx`
- Modify: `apps/web/src/components/prediction-panel.tsx`
- Modify: `apps/web/src/components/kline-chart.tsx`
- Modify: `apps/web/src/app/stocks/[stockCode]/page.tsx`
- Modify: `apps/web/tests/similar-case-list.test.tsx`
- Modify: `apps/web/tests/prediction-panel.test.tsx`
- Modify: `apps/web/tests/stock-research-page-fetch.test.tsx`
- Modify: `apps/web/tests/kline-chart.test.tsx`

- [ ] **Step 1: Write the failing UI tests**

```tsx
it("renders both matched window and owning segment dates", async () => {
  render(<SimilarCaseList items={[sample]} />)
  expect(screen.getByText("相似窗口：2024-12-19 至 2024-12-27")).toBeInTheDocument()
  expect(screen.getByText("所属波段：2024-12-19 至 2025-01-13")).toBeInTheDocument()
})

it("highlights matched 7-bar window in compare modal", async () => {
  render(<PredictionPanel data={payload} />)
  await user.click(screen.getByRole("button", { name: "查看K线对比" }))
  expect(screen.getByText("当前相似窗口")).toBeInTheDocument()
  expect(screen.getByText("历史相似窗口")).toBeInTheDocument()
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm --dir apps/web exec vitest run tests/similar-case-list.test.tsx tests/prediction-panel.test.tsx tests/stock-research-page-fetch.test.tsx tests/kline-chart.test.tsx`

Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

前端改动要求：

- `api.ts` 新增滑窗字段和 `group_stat`
- 相似样本卡片明确区分：
  - `相似窗口`
  - `所属波段`
- 分项相似度显示：
  - 价格
  - K线形态
  - 成交量
  - 换手率
  - 趋势背景
  - 波动率
- 对比弹窗高亮中心改成 `7` 日相似窗口
- 保留前后各 `10` 个交易日上下文

- [ ] **Step 4: Run tests to verify they pass**

Run: `pnpm --dir apps/web exec vitest run tests/similar-case-list.test.tsx tests/prediction-panel.test.tsx tests/stock-research-page-fetch.test.tsx tests/kline-chart.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/lib/api.ts apps/web/src/components/similar-case-list.tsx apps/web/src/components/prediction-panel.tsx apps/web/src/components/kline-chart.tsx apps/web/src/app/stocks/[stockCode]/page.tsx apps/web/tests/similar-case-list.test.tsx apps/web/tests/prediction-panel.test.tsx apps/web/tests/stock-research-page-fetch.test.tsx apps/web/tests/kline-chart.test.tsx
git commit -m "feat: update research page for pattern similarity results"
```

## Task 6: Backfill, Real-Data Verification, And Documentation

**Files:**
- Modify: `README.md`
- Create: `apps/api/tests/integration/test_pattern_similarity_flow.py`
- Modify: `apps/api/tests/ingest/test_job_cli.py`

- [ ] **Step 1: Write the failing integration test**

```python
def test_pattern_similarity_flow_runs_end_to_end(session):
    seed_realistic_prices(session, stock_code="600010")
    seed_segments(session, stock_code="600010")

    build_pattern_windows(stock_code="600010")
    materialize_pattern_features(stock_code="600010")
    materialize_pattern_future_stats(stock_code="600010")
    payload = get_prediction_payload(session, "600010", date(2026, 4, 1))

    assert payload["similar_cases"]
    assert payload["group_stat"]["sample_count"] >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest apps/api/tests/integration/test_pattern_similarity_flow.py apps/api/tests/ingest/test_job_cli.py -v`

Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

补齐：

- README 中新增三段命令：
  - `build-pattern-windows`
  - `materialize-pattern-features`
  - `materialize-pattern-future-stats`
- CLI 帮助文案说明单股回填顺序
- integration test 覆盖单股完整链路

- [ ] **Step 4: Run verification**

Run:

```bash
.venv/bin/pytest apps/api/tests/db/test_pattern_schema.py apps/api/tests/services/test_pattern_window_service.py apps/api/tests/jobs/test_pattern_jobs.py apps/api/tests/domain/test_pattern_features.py apps/api/tests/domain/test_pattern_similarity.py apps/api/tests/services/test_pattern_feature_service.py apps/api/tests/services/test_pattern_similarity_service.py apps/api/tests/domain/test_prediction_service.py apps/api/tests/api/test_turning_points_api.py apps/api/tests/integration/test_pattern_similarity_flow.py -v
pnpm --dir apps/web exec vitest run tests/similar-case-list.test.tsx tests/prediction-panel.test.tsx tests/stock-research-page-fetch.test.tsx tests/kline-chart.test.tsx
```

Expected: PASS

- [ ] **Step 5: Real-data smoke test**

Run:

```bash
python -m swinginsight.jobs.cli import-daily-prices --stock-code 600010 --start 2026-01-01 --end 2026-04-02
python -m swinginsight.jobs.cli rebuild-segments --stock-code 600010
python -m swinginsight.jobs.cli build-pattern-windows --stock-code 600010
python -m swinginsight.jobs.cli materialize-pattern-features --stock-code 600010
python -m swinginsight.jobs.cli materialize-pattern-future-stats --stock-code 600010
```

验证：

- `pattern_window` 有数据
- `pattern_feature` 有数据
- `pattern_future_stat` 有数据
- `/stocks/600010` 返回 `similar_cases`
- `similar_cases[0]` 包含窗口字段和波段字段

- [ ] **Step 6: Commit**

```bash
git add README.md apps/api/tests/integration/test_pattern_similarity_flow.py apps/api/tests/ingest/test_job_cli.py
git commit -m "docs: add pattern similarity rollout guide"
```

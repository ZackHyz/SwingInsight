# News Module V2 Sentiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有新闻模块 V1 基础上新增“高级情绪分析 V1”，把原始新闻与粗粒度分类升级为可量化的事件级消息因子，并接入研究页、特征生成和回测输入链路。

**Architecture:** 保持现有 `news_raw -> news_processed -> point/segment mapping -> research/prediction` 主链不变，在 `process-news` 阶段插入新的“事件抽取 + 情绪打分 + 热度/位置修正”子流水线。V2 只落地规则 + 可插拔模型网关，不直接引入 Neo4j；图谱相关只保留结构化结果落 PostgreSQL 的准备位，等事件抽取稳定后再做独立 V3 计划。

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Alembic, pytest, argparse CLI, optional Transformers/Hugging Face pipeline hook, PostgreSQL/SQLite tests

---

## Why This Is The Next Step

- 现有 `news_processed` 已有 `category / sub_category / sentiment / heat_level / keyword_list / tag_list`，但情绪仍停留在标题关键词粗打分，见 `apps/api/src/swinginsight/domain/news/tagging.py`
- 现有新闻特征只覆盖计数与简单比率，缺少事件强度、冲突信号、修正后情绪分，见 `apps/api/src/swinginsight/domain/features/news.py`
- 现有研究页已能展示新闻标签和股价关联关系，下一步最应该补的是“情绪和事件因子是否值得进研究与预测”，而不是立刻上图数据库
- 复杂关键词图谱依赖更稳定的事件抽取结果；现在先做高级情绪分析 V1，后面图谱可以直接复用 `news_event_result`

## Scope Boundaries

- 本期只做 `高级情绪分析 V1`
- 不做 Neo4j、Graph Data Science、社区发现、传播路径分析
- 不做大模型微调，不做离线标注平台
- 允许预留 Hugging Face 文本分类接口，但默认实现必须可以在“纯规则模式”下工作并通过测试
- 研究页只消费“新闻情绪标签 + 聚合摘要”，不在本期增加单独新闻详情页

## Existing Files To Extend

- `apps/api/src/swinginsight/db/models/news.py`
  - 现有 `NewsRaw`、`NewsProcessed`、`SegmentNewsMap`、`PointNewsMap`
- `apps/api/src/swinginsight/services/news_processing_service.py`
  - 现有新闻清洗、去重、粗分类处理入口
- `apps/api/src/swinginsight/domain/news/classifier.py`
  - 现有业务分类规则
- `apps/api/src/swinginsight/domain/news/tagging.py`
  - 现有标题关键词情绪与热度规则
- `apps/api/src/swinginsight/domain/features/news.py`
  - 现有消息面特征聚合
- `apps/api/src/swinginsight/services/current_news_window_service.py`
  - 现有当前窗口新闻摘要
- `apps/api/src/swinginsight/api/routes/stocks.py`
  - 现有研究页新闻输出

## New Data Model Direction

V2 不继续把所有结果都塞进 `news_processed`。新增两张结果表：

- `news_sentiment_result`
  - 一条新闻一条汇总情绪记录
  - 存整体极性、基础分、修正分、置信度、热度分、事件冲突标记
- `news_event_result`
  - 一条新闻零到多条事件记录
  - 存事件类型、事件极性、事件强度、主要实体、次要实体、句级文本

这样后续图谱阶段直接复用 `news_event_result`，不需要再从原文二次反抽。

## Delivery Milestones

- Milestone 1: 新情绪/事件结果表和迁移完成
- Milestone 2: 规则版事件抽取与情绪打分完成
- Milestone 3: `process-news` 能稳定写出 `news_sentiment_result` 与 `news_event_result`
- Milestone 4: 研究页、当前窗口摘要、消息面特征开始消费新结果
- Milestone 5: 补齐批处理与回补命令，完成真实股票验证

## Task 1: Add Persistent Sentiment And Event Result Tables

**Files:**
- Modify: `apps/api/src/swinginsight/db/models/news.py`
- Create: `apps/api/alembic/versions/0003_news_sentiment_v1.py`
- Create: `apps/api/tests/db/test_news_sentiment_schema.py`

- [ ] **Step 1: 写失败的 schema 测试**

```python
def test_news_sentiment_tables_exist(session):
    inspector = sa.inspect(session.bind)
    assert "news_sentiment_result" in inspector.get_table_names()
    assert "news_event_result" in inspector.get_table_names()


def test_news_event_result_allows_multiple_events_per_news(session):
    seed_news(session, news_id=1)
    insert_event(session, news_id=1, event_type="earnings")
    insert_event(session, news_id=1, event_type="capital_action")
    assert session.scalar(select(func.count()).select_from(NewsEventResult).where(NewsEventResult.news_id == 1)) == 2
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/pytest apps/api/tests/db/test_news_sentiment_schema.py -v`

Expected: FAIL，提示缺少新表或约束。

- [ ] **Step 3: 做最小 schema 实现**

在 `apps/api/src/swinginsight/db/models/news.py` 新增：

- `NewsSentimentResult`
  - `news_id`
  - `stock_code`
  - `sentiment_label`
  - `sentiment_score_base`
  - `sentiment_score_adjusted`
  - `confidence_score`
  - `heat_score`
  - `market_context_score`
  - `position_context_score`
  - `event_conflict_flag`
  - `model_version`
  - `calculated_at`
- `NewsEventResult`
  - `news_id`
  - `stock_code`
  - `sentence_index`
  - `sentence_text`
  - `event_type`
  - `event_polarity`
  - `event_strength`
  - `entity_main`
  - `entity_secondary`
  - `trigger_keywords`
  - `model_version`

迁移要求：
- `news_id` 建唯一约束到 `news_sentiment_result`
- `news_event_result` 对 `(news_id, sentence_index, event_type)` 建唯一约束
- 索引至少覆盖 `stock_code`、`event_type`、`sentiment_label`

- [ ] **Step 4: 跑迁移和 schema 测试**

Run: `cd apps/api && DATABASE_URL=sqlite+pysqlite:////tmp/swinginsight-news-v2.db ../../.venv/bin/alembic -c alembic.ini upgrade head`

Run: `.venv/bin/pytest apps/api/tests/db/test_news_sentiment_schema.py -v`

Expected: PASS

- [ ] **Step 5: 提交 schema 变更**

```bash
git add apps/api/src/swinginsight/db/models/news.py apps/api/alembic/versions/0003_news_sentiment_v1.py apps/api/tests/db/test_news_sentiment_schema.py
git commit -m "feat: add news sentiment and event result schema"
```

## Task 2: Build Rule-Based Event Extraction And Sentiment Scoring Core

**Files:**
- Create: `apps/api/src/swinginsight/domain/news/events.py`
- Create: `apps/api/src/swinginsight/domain/news/sentiment.py`
- Modify: `apps/api/src/swinginsight/domain/news/classifier.py`
- Modify: `apps/api/src/swinginsight/domain/news/tagging.py`
- Create: `apps/api/tests/domain/test_news_sentiment_rules.py`

- [ ] **Step 1: 写失败的规则测试**

```python
def test_extract_events_splits_multiple_financial_events():
    events = extract_events("公司发布业绩预增公告，同时控股股东拟减持。")
    assert [event.event_type for event in events] == ["earnings", "capital_action"]
    assert [event.event_polarity for event in events] == ["positive", "negative"]


def test_score_news_sentiment_aggregates_conflicting_events():
    result = score_news_sentiment(
        title="公司发布业绩预增公告，同时控股股东拟减持",
        summary=None,
        source_type="announcement",
        duplicate_count=1,
        events=[
            EventSignal(event_type="earnings", event_polarity="positive", event_strength=4),
            EventSignal(event_type="capital_action", event_polarity="negative", event_strength=3),
        ],
    )
    assert result.sentiment_label == "neutral"
    assert result.event_conflict_flag is True
    assert result.sentiment_score_base != 0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/pytest apps/api/tests/domain/test_news_sentiment_rules.py -v`

Expected: FAIL

- [ ] **Step 3: 最小实现规则引擎**

必须覆盖的事件类型：
- `earnings`
- `capital_action`
- `mna`
- `risk_alert`
- `order_contract`
- `policy_catalyst`
- `governance`

规则要求：
- 支持一条新闻抽多个事件
- 每个事件产出 `event_type / event_polarity / event_strength / trigger_keywords`
- 先做标题 + 摘要级切句，不要求正文全文解析
- `score_news_sentiment` 输出：
  - `sentiment_label`
  - `sentiment_score_base`
  - `confidence_score`
  - `heat_score`
  - `event_conflict_flag`

建议规则：
- 业绩预增/扭亏/回购/增持/中标：正向
- 减持/终止/问询/处罚/风险提示/异常波动：负向或风险
- 董事会决议/股东大会通知：默认中性，除非触发更具体事件

- [ ] **Step 4: 跑规则测试**

Run: `.venv/bin/pytest apps/api/tests/domain/test_news_sentiment_rules.py apps/api/tests/domain/test_news_processing.py -v`

Expected: PASS

- [ ] **Step 5: 提交规则层**

```bash
git add apps/api/src/swinginsight/domain/news apps/api/tests/domain/test_news_sentiment_rules.py apps/api/tests/domain/test_news_processing.py
git commit -m "feat: add rule-based news sentiment scoring"
```

## Task 3: Extend Process-News Pipeline To Persist Sentiment And Event Results

**Files:**
- Modify: `apps/api/src/swinginsight/services/news_processing_service.py`
- Create: `apps/api/src/swinginsight/services/news_sentiment_service.py`
- Create: `apps/api/tests/services/test_news_sentiment_service.py`
- Modify: `apps/api/tests/domain/test_news_processing.py`

- [ ] **Step 1: 写失败的处理集成测试**

```python
def test_process_news_writes_sentiment_and_event_results(session):
    news_id = seed_news(
        session,
        title="公司发布业绩预增公告，同时控股股东拟减持",
        source_type="announcement",
    )
    result = NewsProcessingService(session).process_batch([news_id])
    sentiment = session.scalar(select(NewsSentimentResult).where(NewsSentimentResult.news_id == news_id))
    events = session.scalars(select(NewsEventResult).where(NewsEventResult.news_id == news_id).order_by(NewsEventResult.sentence_index.asc())).all()
    assert result.processed_count == 1
    assert sentiment is not None
    assert len(events) == 2
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/pytest apps/api/tests/services/test_news_sentiment_service.py apps/api/tests/domain/test_news_processing.py -v`

Expected: FAIL

- [ ] **Step 3: 最小实现处理链路**

要求：
- 在 `process_batch` 中，保留现有 `NewsProcessed` 写入逻辑
- 新增 `NewsSentimentService` 负责：
  - 事件抽取
  - 基础分聚合
  - 热度分计算
  - 位置修正预留
  - 写入 `NewsSentimentResult`
  - 写入 `NewsEventResult`
- `process-news` 的幂等性要保持：
  - 二次运行同一 `news_id` 时更新现有记录，不重复插入

- [ ] **Step 4: 跑集成测试**

Run: `.venv/bin/pytest apps/api/tests/services/test_news_sentiment_service.py apps/api/tests/domain/test_news_processing.py apps/api/tests/ingest/test_job_cli.py -v`

Expected: PASS

- [ ] **Step 5: 提交处理链整合**

```bash
git add apps/api/src/swinginsight/services/news_processing_service.py apps/api/src/swinginsight/services/news_sentiment_service.py apps/api/tests/services/test_news_sentiment_service.py apps/api/tests/domain/test_news_processing.py
git commit -m "feat: persist event-level news sentiment results"
```

## Task 4: Add Position-Aware Adjustment And Research Consumption

**Files:**
- Modify: `apps/api/src/swinginsight/services/news_sentiment_service.py`
- Modify: `apps/api/src/swinginsight/domain/features/news.py`
- Modify: `apps/api/src/swinginsight/services/feature_materialization_service.py`
- Modify: `apps/api/src/swinginsight/services/current_news_window_service.py`
- Modify: `apps/api/src/swinginsight/api/routes/stocks.py`
- Modify: `apps/api/tests/api/test_turning_points_api.py`
- Create: `apps/api/tests/domain/test_news_feature_v2.py`

- [ ] **Step 1: 写失败的位置修正与特征测试**

```python
def test_adjusted_sentiment_rewards_positive_news_before_trough(session):
    mapping = seed_point_mapping(session, relation_type="before_trough", point_type="trough")
    sentiment = adjust_sentiment_with_position(
        base_score=0.6,
        category="announcement",
        relation_type=mapping.relation_type,
        point_type=mapping.point_type,
    )
    assert sentiment > 0.6
```

```python
def test_compute_news_features_v2_emits_adjusted_sentiment_metrics():
    features = compute_news_features_v2([...])
    assert "avg_adjusted_sentiment_before_trough_5d" in features
    assert "conflicting_event_ratio" in features
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/pytest apps/api/tests/domain/test_news_feature_v2.py apps/api/tests/api/test_turning_points_api.py -v`

Expected: FAIL

- [ ] **Step 3: 最小实现位置修正与消费层**

修正规则 V1：
- `before_trough` 且新闻为正向 `announcement / policy_catalyst / earnings`，上调 `position_context_score`
- `before_peak` 且正向高热度新闻，下调 `sentiment_score_adjusted`
- 风险提示/减持/问询类在 `after_peak` 下调更重

研究页与摘要接入：
- `/stocks/{code}` 的 `news_items` 继续保留 `display_tags`
- 新增字段：
  - `sentiment_score_adjusted`
  - `event_types`
  - `event_conflict_flag`
- 当前窗口摘要增加：
  - `avg_adjusted_sentiment`
  - `positive_event_count`
  - `negative_event_count`

特征入模：
- 在 `domain/features/news.py` 新增：
  - `avg_adjusted_sentiment_before_trough_5d`
  - `avg_adjusted_sentiment_after_peak_5d`
  - `conflicting_event_ratio`
  - `capital_action_risk_flag`

- [ ] **Step 4: 跑研究页和特征测试**

Run: `.venv/bin/pytest apps/api/tests/domain/test_news_feature_v2.py apps/api/tests/api/test_turning_points_api.py apps/api/tests/services/test_stock_research_service.py -v`

Expected: PASS

- [ ] **Step 5: 提交消费层**

```bash
git add apps/api/src/swinginsight/domain/features/news.py apps/api/src/swinginsight/services/current_news_window_service.py apps/api/src/swinginsight/api/routes/stocks.py apps/api/tests/domain/test_news_feature_v2.py apps/api/tests/api/test_turning_points_api.py
git commit -m "feat: expose position-aware news sentiment factors"
```

## Task 5: Add Backfill And Real-Data Verification Path

**Files:**
- Modify: `apps/api/src/swinginsight/jobs/process_news.py`
- Modify: `apps/api/src/swinginsight/jobs/cli.py`
- Create: `apps/api/tests/jobs/test_process_news_v2.py`
- Modify: `README.md`

- [ ] **Step 1: 写失败的作业测试**

```python
def test_process_news_job_reports_sentiment_and_event_counts(session):
    seed_pending_news(session, stock_code="600010")
    result = process_news(stock_code="600010", start=date(2026, 3, 19), end=date(2026, 4, 2), session=session)
    assert result.processed_count > 0
    assert result.sentiment_results > 0
    assert result.event_results > 0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/pytest apps/api/tests/jobs/test_process_news_v2.py -v`

Expected: FAIL

- [ ] **Step 3: 最小实现作业与文档**

要求：
- `process-news` CLI 输出新增：
  - `sentiment_results`
  - `event_results`
  - `conflict_news`
- README 新增“情绪分析 V1”章节，说明：
  - 如何回补
  - 如何查看 `news_sentiment_result`
  - 如何验证研究页输出

- [ ] **Step 4: 跑真实链路验证**

Run:

```bash
cd /Users/kfz/code/SwingInsight/apps/api
/Users/kfz/code/SwingInsight/.venv/bin/python -m swinginsight.jobs.cli import-news --stock-code 600010 --start 2026-03-19 --end 2026-04-02
/Users/kfz/code/SwingInsight/.venv/bin/python -m swinginsight.jobs.cli process-news --stock-code 600010 --start 2026-03-19 --end 2026-04-02
/Users/kfz/code/SwingInsight/.venv/bin/python -m swinginsight.jobs.cli align-news --stock-code 600010 --start 2026-03-19 --end 2026-04-02
```

验证：
- `news_sentiment_result` 行数与 `news_processed` 对齐
- `news_event_result` 至少能看到 `earnings / capital_action / risk_alert` 等业务事件
- `GET /stocks/600010` 返回 `display_tags + sentiment_score_adjusted + event_types`

- [ ] **Step 5: 提交作业与文档**

```bash
git add apps/api/src/swinginsight/jobs/process_news.py apps/api/src/swinginsight/jobs/cli.py apps/api/tests/jobs/test_process_news_v2.py README.md
git commit -m "feat: add operational flow for news sentiment v1"
```

## Explicitly Deferred To V3

这些不在本计划内：

- Neo4j / Graph Data Science 接入
- `news_entity_map` / `entity_relation_map` / `concept_synonym_dict`
- BERTopic/KeyBERT/主题聚类
- Hugging Face 金融情绪模型上线作为默认主路径
- 复杂传播链、社区发现、图中心性分析

## Recommended Execution Order

1. Task 1: schema
2. Task 2: 规则引擎
3. Task 3: 处理链持久化
4. Task 4: 特征与研究页消费
5. Task 5: 作业与真实验证

## Definition Of Done

- 真实股票 `600010` 能完成导入、处理、对齐与研究页展示
- `news_sentiment_result` 与 `news_event_result` 都有真实数据
- 研究页新闻可见：
  - 股价关联标签
  - 情绪标签
  - 修正后情绪分或等价摘要字段
- 消息面特征已进入段特征生成链路
- 相关 API、domain、jobs、web 测试全部通过

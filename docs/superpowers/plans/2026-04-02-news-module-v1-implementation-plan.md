# News Module V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 SwingInsight 后端上补齐新闻模块 V1，形成“抓取 -> 原始入库 -> 去重清洗 -> 分类打标 -> 拐点/波段映射 -> 特征生成 -> 研究/预测接入”的可验证闭环。

**Architecture:** 直接扩展现有 `apps/api` 新闻骨架，不新建平行系统。保留 `news_raw` 与 `segment_news_map`，新增 `news_processed` 和 `point_news_map` 承载处理结果与拐点映射；抓取层沿用 `ingest/adapters` 和 `NewsFeed` port，处理与对齐逻辑落在 `services`/`domain/news`，研究页和预测继续走现有 `stocks`、`predictions` 路由。

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Alembic, pytest, AkShare/HTTP adapters, argparse CLI

---

## Current Baseline

- 已有原始新闻表与波段映射表：`apps/api/src/swinginsight/db/models/news.py`
- 已有波段新闻对齐服务：`apps/api/src/swinginsight/services/segment_news_alignment_service.py`
- 已有新闻特征入口，但只支持少量聚合：`apps/api/src/swinginsight/domain/features/news.py`
- 已有新闻导入器与作业入口，但新闻源适配器仍是占位实现：`apps/api/src/swinginsight/ingest/news_importer.py`、`apps/api/src/swinginsight/ingest/adapters/akshare_news_feed.py`、`apps/api/src/swinginsight/jobs/import_news.py`
- 已有段新闻 API，但没有拐点新闻 API、新闻处理表、当前窗口新闻特征、增量新闻调度

## Scope Boundaries

- V1 只做后端闭环，不在本计划中强制包含完整前端资讯页改造。
- NLP 先走规则分类和轻量标签，不引入大模型分类器或复杂向量检索。
- 数据源先落两类：公告源 + 财经资讯源。优先巨潮资讯与东方财富；若现阶段库里只有 AkShare 封装，则以适配器包装实际可用源，接口设计保持可替换。
- 预测接入以“结构化新闻特征进入 `segment_feature` 和当前状态摘要”为止，不在本期引入新的机器学习模型。

## Repository Fit

- 继续使用 `apps/api/src/swinginsight/ingest/adapters/` 存放新闻源适配器，不额外创建 `source_adapters/`
- 继续使用 `apps/api/src/swinginsight/jobs/cli.py` 作为命令入口
- 继续复用 `feature_materialization_service.py` 生成新闻特征，避免再造第二套特征流水线
- Alembic 新增迁移应为 `apps/api/alembic/versions/0002_news_module_v1.py`

## Delivery Milestones

- Milestone 1: 完成新闻表结构升级与迁移，数据可以稳定落库
- Milestone 2: 完成两类新闻源适配与导入任务，支持按股票/日期回补
- Milestone 3: 完成去重、规则分类、情绪/热度/事件标签，生成 `news_processed`
- Milestone 4: 完成拐点/波段映射与新闻查询接口
- Milestone 5: 完成消息面特征入模和研究页/预测链路接入

## Task 1: Harden News Schema And Migration Boundary

**Files:**
- Modify: `apps/api/src/swinginsight/db/models/news.py`
- Create: `apps/api/alembic/versions/0002_news_module_v1.py`
- Create: `apps/api/tests/db/test_news_schema.py`

- [ ] **Step 1: 先写失败的 schema 测试**

```python
def test_news_processed_and_point_news_map_tables_exist(session):
    inspector = sa.inspect(session.bind)
    assert "news_processed" in inspector.get_table_names()
    assert "point_news_map" in inspector.get_table_names()


def test_point_news_map_enforces_unique_point_news_relation(session):
    insert_point_news_map(session, point_id=1, news_id=2, relation_type="before_trough")
    with pytest.raises(IntegrityError):
        insert_point_news_map(session, point_id=1, news_id=2, relation_type="before_trough")
```

- [ ] **Step 2: 跑测试确认当前失败**

Run: `.venv/bin/pytest apps/api/tests/db/test_news_schema.py -v`

Expected: FAIL，提示缺少新表或唯一约束。

- [ ] **Step 3: 最小实现数据库升级**

必须在 `apps/api/src/swinginsight/db/models/news.py` 中完成：
- 为 `NewsRaw` 增加 `raw_json`、`fetch_time`、`is_parsed`、`parse_status`、`main_news_id`
- 新增 `NewsProcessed`
- 新增 `PointNewsMap`
- 为 `news_uid`、`stock_code + publish_time`、`duplicate_group_id`、`point_id/news_id/relation_type` 加清晰索引/唯一约束

迁移 `0002_news_module_v1.py` 必须保证：
- 从现有 `0001` 无损升级
- 生产数据可回填默认值
- `downgrade()` 可执行

- [ ] **Step 4: 跑迁移与数据库测试**

Run: `cd apps/api && DATABASE_URL=sqlite+pysqlite:////tmp/swinginsight-news-plan.db ../../.venv/bin/alembic -c alembic.ini upgrade head`

Expected: PASS

Run: `.venv/bin/pytest apps/api/tests/db/test_news_schema.py apps/api/tests/db/test_schema_smoke.py -v`

Expected: PASS

- [ ] **Step 5: 提交 schema 变更**

```bash
git add apps/api/src/swinginsight/db/models/news.py apps/api/alembic/versions/0002_news_module_v1.py apps/api/tests/db/test_news_schema.py
git commit -m "feat: extend news schema for processed news and point mapping"
```

## Task 2: Implement Source Adapters And Raw Import Orchestration

**Files:**
- Modify: `apps/api/src/swinginsight/ingest/ports.py`
- Modify: `apps/api/src/swinginsight/ingest/news_importer.py`
- Modify: `apps/api/src/swinginsight/jobs/import_news.py`
- Modify: `apps/api/src/swinginsight/jobs/cli.py`
- Modify: `apps/api/src/swinginsight/ingest/adapters/akshare_news_feed.py`
- Create: `apps/api/src/swinginsight/ingest/adapters/cninfo_news_feed.py`
- Create: `apps/api/src/swinginsight/ingest/adapters/eastmoney_news_feed.py`
- Create: `apps/api/src/swinginsight/services/news_source_service.py`
- Create: `apps/api/tests/ingest/test_news_importer.py`
- Modify: `apps/api/tests/ingest/test_job_cli.py`

- [ ] **Step 1: 先写失败的导入与 CLI 测试**

```python
def test_news_importer_upserts_rows_and_sets_fetch_metadata(session, fake_news_feed):
    importer = NewsImporter(session=session, feed=fake_news_feed, source_name="fake")
    inserted = importer.run(stock_code="000001", start=date(2024, 1, 1), end=date(2024, 1, 31))
    assert inserted == 2
    rows = session.scalars(select(NewsRaw).order_by(NewsRaw.id.asc())).all()
    assert rows[0].fetch_time is not None
    assert rows[0].parse_status == "pending"
```

```python
def test_cli_exposes_import_news_command(runner):
    result = runner.invoke(main, ["import-news", "--stock-code", "000001", "--start", "2024-01-01", "--end", "2024-01-31"])
    assert result.exit_code == 0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/pytest apps/api/tests/ingest/test_news_importer.py apps/api/tests/ingest/test_job_cli.py -v`

Expected: FAIL，提示导入字段、命令或适配器未实现。

- [ ] **Step 3: 实现最小抓取与导入闭环**

要求：
- `NewsFeed` 继续返回统一字段，但新增 `raw_json` 和标准化 `source_type`
- `NewsImporter` 支持基于 `news_uid`/URL/标题时间的幂等 upsert，而不是无脑插入
- `jobs/import_news.py` 支持 `stock_code/start/end/source_list`
- `jobs/cli.py` 新增 `import-news`
- `news_source_service.py` 负责按 source 名称构建 feed 列表，业务层不能直接 new 某个 adapter
- `akshare_news_feed.py` 不再保留 `NotImplementedError`

- [ ] **Step 4: 跑导入与 CLI 验证**

Run: `.venv/bin/pytest apps/api/tests/ingest/test_news_importer.py apps/api/tests/ingest/test_job_cli.py -v`

Expected: PASS

- [ ] **Step 5: 提交抓取层**

```bash
git add apps/api/src/swinginsight/ingest apps/api/src/swinginsight/jobs/import_news.py apps/api/src/swinginsight/jobs/cli.py apps/api/src/swinginsight/services/news_source_service.py apps/api/tests/ingest
git commit -m "feat: add news adapters and raw import pipeline"
```

## Task 3: Build News Processing Pipeline For Dedupe, Classification, And Tagging

**Files:**
- Modify: `apps/api/src/swinginsight/domain/news/dedupe.py`
- Create: `apps/api/src/swinginsight/domain/news/normalize.py`
- Create: `apps/api/src/swinginsight/domain/news/classifier.py`
- Create: `apps/api/src/swinginsight/domain/news/tagging.py`
- Create: `apps/api/src/swinginsight/services/news_processing_service.py`
- Create: `apps/api/tests/domain/test_news_processing.py`

- [ ] **Step 1: 写失败的处理测试**

```python
def test_process_news_marks_duplicate_group_and_main_news(session):
    seed_duplicate_news(session)
    result = NewsProcessingService(session).process_batch([1, 2])
    assert result.processed_count == 2
    assert result.duplicates >= 1
    processed = session.scalar(select(NewsProcessed).where(NewsProcessed.news_id == 1))
    assert processed.category == "announcement"
```

```python
def test_rule_classifier_maps_business_categories():
    assert classify_title("2025年业绩预告同比扭亏").category == "announcement"
    assert classify_title("签署重大订单协议").sub_category == "order_contract"
    assert classify_title("异常波动及风险提示公告").sub_category == "risk_alert"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/pytest apps/api/tests/domain/test_news_processing.py -v`

Expected: FAIL

- [ ] **Step 3: 实现处理流水线**

V1 处理规则必须覆盖：
- URL 去重
- 标题精确去重
- 标题相似去重的最小版本（标题规范化 + 关键词骨架）
- 一级分类：`announcement` / `media_news` / `industry_news` / `concept_news` / `market_flash`
- 二级分类：`earnings` / `capital_action` / `mna` / `risk_alert` / `order_contract`
- 标签：`positive` / `neutral` / `negative`、`low` / `medium` / `high`、`official` / `rumor` / `follow_up` / `first_release` / `repeated_spread`

处理输出要求：
- `NewsRaw.is_parsed = True`
- `NewsRaw.parse_status = "processed"` 或 `"failed"`
- `NewsProcessed` 写入 clean 字段、分类、标签、关键词
- 重复新闻不删除，只维护 `duplicate_group_id`、`main_news_id`

- [ ] **Step 4: 跑处理测试**

Run: `.venv/bin/pytest apps/api/tests/domain/test_news_processing.py apps/api/tests/domain/test_news_alignment.py -v`

Expected: PASS

- [ ] **Step 5: 提交新闻处理层**

```bash
git add apps/api/src/swinginsight/domain/news apps/api/src/swinginsight/services/news_processing_service.py apps/api/tests/domain/test_news_processing.py
git commit -m "feat: add news processing pipeline"
```

## Task 4: Add Point And Segment Alignment Services Plus Query APIs

**Files:**
- Modify: `apps/api/src/swinginsight/services/segment_news_alignment_service.py`
- Create: `apps/api/src/swinginsight/services/point_news_alignment_service.py`
- Modify: `apps/api/src/swinginsight/api/routes/news.py`
- Modify: `apps/api/src/swinginsight/api/routes/turning_points.py`
- Modify: `apps/api/src/swinginsight/api/main.py`
- Create: `apps/api/tests/domain/test_point_news_alignment.py`
- Create: `apps/api/tests/api/test_news_api.py`

- [ ] **Step 1: 写失败的映射与 API 测试**

```python
def test_align_point_news_maps_news_into_t_minus_5_to_t_plus_5(session):
    point = seed_turning_point(session, point_type="trough", point_date=date(2024, 1, 8))
    seed_news_window(session)
    rows = align_point_news(session, point_id=point.id, before_days=5, after_days=5)
    assert {row.relation_type for row in rows} == {"before_trough", "after_trough"}
```

```python
def test_get_turning_point_news_returns_processed_fields(client):
    response = client.get("/turning-points/1/news")
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["category"] == "announcement"
    assert "keyword_list" in payload[0]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/pytest apps/api/tests/domain/test_point_news_alignment.py apps/api/tests/api/test_news_api.py -v`

Expected: FAIL

- [ ] **Step 3: 实现拐点/波段对齐与查询**

要求：
- `segment_news_alignment_service.py` 改为优先消费 `NewsProcessed`
- `point_news_alignment_service.py` 负责 `T-5 ~ T+5` 拐点窗口映射
- 新增 API：
  - `GET /segments/{segment_id}/news`
  - `GET /turning-points/{point_id}/news`
  - `GET /stocks/{stock_code}/news?start_date=&end_date=`
- `api/routes/news.py` 统一返回 processed 字段：`category`、`sub_category`、`sentiment`、`heat_level`、`keyword_list`

- [ ] **Step 4: 跑 API 与对齐测试**

Run: `.venv/bin/pytest apps/api/tests/domain/test_news_alignment.py apps/api/tests/domain/test_point_news_alignment.py apps/api/tests/api/test_news_api.py -v`

Expected: PASS

- [ ] **Step 5: 提交对齐与查询层**

```bash
git add apps/api/src/swinginsight/services/segment_news_alignment_service.py apps/api/src/swinginsight/services/point_news_alignment_service.py apps/api/src/swinginsight/api/routes/news.py apps/api/src/swinginsight/api/routes/turning_points.py apps/api/src/swinginsight/api/main.py apps/api/tests/domain/test_point_news_alignment.py apps/api/tests/api/test_news_api.py
git commit -m "feat: align processed news to points and segments"
```

## Task 5: Materialize News Features For Research And Prediction

**Files:**
- Modify: `apps/api/src/swinginsight/domain/features/news.py`
- Modify: `apps/api/src/swinginsight/services/feature_materialization_service.py`
- Modify: `apps/api/src/swinginsight/services/stock_research_service.py`
- Modify: `apps/api/src/swinginsight/api/routes/stocks.py`
- Modify: `apps/api/src/swinginsight/api/routes/predictions.py`
- Create: `apps/api/src/swinginsight/services/current_news_window_service.py`
- Create: `apps/api/tests/domain/test_news_features.py`
- Modify: `apps/api/tests/integration/test_end_to_end_research_flow.py`

- [ ] **Step 1: 写失败的特征测试**

```python
def test_compute_news_features_includes_sentiment_heat_and_event_flags():
    items = [
        build_news_feature_item(relation_type="before_trough", sentiment="positive", heat_level="high", category="announcement"),
        build_news_feature_item(relation_type="after_peak", sentiment="negative", heat_level="medium", category="media_news"),
    ]
    features = compute_news_features(items)
    assert features["positive_news_ratio"] == 0.5
    assert features["high_heat_news_ratio"] == 0.5
    assert features["announcement_count_before_trough_5d"] == 1.0
```

```python
def test_stock_research_payload_includes_windowed_news_summary(client):
    response = client.get("/stocks/000001")
    payload = response.json()
    assert "news_items" in payload
    assert "news_summary" in payload["current_state"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/pytest apps/api/tests/domain/test_news_features.py apps/api/tests/integration/test_end_to_end_research_flow.py -v`

Expected: FAIL

- [ ] **Step 3: 实现特征与研究链路接入**

V1 必须产出的新闻特征至少包含：
- `news_count_before_trough_5d`
- `news_count_after_peak_5d`
- `announcement_count_before_trough_5d`
- `negative_news_count_after_peak_5d`
- `positive_news_ratio`
- `duplicate_news_ratio`
- `high_heat_news_ratio`
- `has_earnings_event`
- `has_risk_alert`

接入点要求：
- `feature_materialization_service.py` 在 materialize 时读取 processed + point/segment map
- `stock_research_service.py` 在补数据或重建研究页时同步处理新闻
- `stocks.py` 返回最近新闻和窗口摘要
- `predictions.py` 将当前窗口新闻摘要并入 `current_state`

- [ ] **Step 4: 跑特征与集成测试**

Run: `.venv/bin/pytest apps/api/tests/domain/test_news_features.py apps/api/tests/integration/test_end_to_end_research_flow.py -v`

Expected: PASS

- [ ] **Step 5: 提交特征接入层**

```bash
git add apps/api/src/swinginsight/domain/features/news.py apps/api/src/swinginsight/services/feature_materialization_service.py apps/api/src/swinginsight/services/stock_research_service.py apps/api/src/swinginsight/api/routes/stocks.py apps/api/src/swinginsight/api/routes/predictions.py apps/api/src/swinginsight/services/current_news_window_service.py apps/api/tests/domain/test_news_features.py apps/api/tests/integration/test_end_to_end_research_flow.py
git commit -m "feat: integrate news features into research and prediction"
```

## Task 6: Add Operational Commands, Incremental Refresh, And Final Verification

**Files:**
- Modify: `apps/api/src/swinginsight/jobs/cli.py`
- Modify: `apps/api/src/swinginsight/jobs/import_news.py`
- Create: `apps/api/src/swinginsight/jobs/process_news.py`
- Create: `apps/api/src/swinginsight/jobs/align_news.py`
- Create: `apps/api/tests/integration/test_news_pipeline_flow.py`
- Modify: `README.md`

- [ ] **Step 1: 写失败的流水线集成测试**

```python
def test_news_pipeline_flow_backfills_processes_and_aligns(session):
    run_import_news(stock_code="000001", start=date(2024, 1, 1), end=date(2024, 1, 31))
    run_process_news(stock_code="000001", start=date(2024, 1, 1), end=date(2024, 1, 31))
    run_align_news(stock_code="000001", start=date(2024, 1, 1), end=date(2024, 1, 31))
    assert session.scalar(select(func.count(NewsProcessed.id))) > 0
    assert session.scalar(select(func.count(PointNewsMap.id))) > 0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/pytest apps/api/tests/integration/test_news_pipeline_flow.py -v`

Expected: FAIL

- [ ] **Step 3: 实现命令与增量策略**

CLI 至少要支持：
- `import-news`
- `process-news`
- `align-news`

增量策略要求：
- 默认按最近 7 日刷新新闻
- `StockResearchService.ensure_stock_ready()` 在页面按需触发时，只补缺失窗口，不全量重跑全部历史
- 所有 job 写入 `task_run_log`

- [ ] **Step 4: 跑最终回归**

Run: `.venv/bin/pytest apps/api/tests/db/test_news_schema.py apps/api/tests/ingest/test_news_importer.py apps/api/tests/domain/test_news_processing.py apps/api/tests/domain/test_news_alignment.py apps/api/tests/domain/test_point_news_alignment.py apps/api/tests/domain/test_news_features.py apps/api/tests/api/test_news_api.py apps/api/tests/integration/test_news_pipeline_flow.py apps/api/tests/integration/test_end_to_end_research_flow.py -v`

Expected: PASS

- [ ] **Step 5: 更新文档并提交**

`README.md` 必须补充：
- 新闻源配置
- CLI 示例
- 增量更新说明
- 失败排查入口

```bash
git add apps/api/src/swinginsight/jobs apps/api/tests/integration/test_news_pipeline_flow.py README.md
git commit -m "feat: add operational pipeline for news module v1"
```

## Recommended Execution Order

1. 先完成 Task 1 和 Task 2，确保抓取与表结构稳定。
2. 再完成 Task 3 和 Task 4，形成“可研究”的新闻处理与映射闭环。
3. 最后完成 Task 5 和 Task 6，把新闻特征接到研究页和预测，并加上日常运维入口。

## Risks To Watch

- 公告源和媒体源字段差异大，适配层必须统一 `source_type` 和时间字段，否则后续处理层会持续补洞。
- `news_raw` 现有字段和 `news_processed` 的职责必须分清，不能既在 raw 表写清洗结果又单独维护 processed 表。
- 去重规则过激会吞掉真正不同的跟进报道；V1 先保守，保留原始记录，只做分组。
- 当前 `feature_materialization_service.py` 会在 materialize 时自动对齐新闻，新增 point map 后必须避免重复写映射。
- `StockResearchService.ensure_stock_ready()` 里如果把新闻全量重跑塞进页面请求，会拖慢搜索体验；按需触发只允许补最近窗口。

## Acceptance Checklist

- 可以按股票和日期窗口导入至少两类新闻源
- `news_raw`、`news_processed`、`segment_news_map`、`point_news_map` 四张表都有可验证数据
- `GET /segments/{segment_id}/news` 和 `GET /turning-points/{point_id}/news` 可返回处理后的新闻字段
- `segment_feature` 中可以看到新闻特征项
- `/stocks/{stock_code}` 和 `/predictions/{stock_code}` 能返回当前窗口新闻摘要
- 相关 pytest 回归全绿

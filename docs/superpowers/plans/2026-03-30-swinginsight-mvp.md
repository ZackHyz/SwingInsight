# SwingInsight MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从 0 搭建 SwingInsight 的首个可用 MVP，完成 A 股日线/成交/新闻数据接入、波峰波谷识别与人工校正、波段样本沉淀、特征提取，以及面向当前状态的相似样本匹配和概率预测。

**Architecture:** 采用单仓双应用结构：`apps/api` 负责数据模型、算法、任务入口与 HTTP API；`apps/web` 负责研究页面、K 线交互、校正界面和结果展示。优先使用可解释的规则、阈值和相似度检索完成第一版闭环，先把数据质量与交互正确性做稳，再补异步任务和更复杂模型。

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL, pandas, numpy, scikit-learn, AkShare, Tushare, mootdx, Next.js, React, TypeScript, ECharts, Playwright, pytest, Vitest, Docker Compose

---

## Assumptions

- 共享链接里的 PRD 已视为确认版产品输入，本计划直接落到工程实施层。
- 日线与历史成交下载逻辑已有原型实现；MVP 只为这些能力设计标准接入层，不重写抓取内核。
- 本期只做 A 股、日线级别、单用户研究台，不做自动交易、多账户权限、分钟级回放。
- 先用 PostgreSQL 承载核心数据；异步任务先用 CLI/API 触发，Redis/队列等基础设施在吞吐瓶颈出现后再引入。
- 用户已确认数据源使用 `AkShare`、`Tushare`、`mootdx`；`Tushare` token 只通过环境变量 `TUSHARE_TOKEN` 注入，不能写入代码仓库或示例配置中的明文值。

## Data Source Strategy

- `Tushare`: 作为结构化基础数据主源，优先承担 `stock_basic`、交易日历、复权因子、行业概念映射、日线补齐等字段完整性要求高的数据。
- `AkShare`: 作为通用抓取层和补充源，优先承担新闻、热点题材、部分基础行情补录，以及 `Tushare` 覆盖不足时的回填。
- `mootdx`: 作为行情侧高可用补充源，优先承担本地化行情拉取、历史 K 线兜底和数据交叉校验。
- 所有接入必须走统一 port，业务层不能直接依赖某个 SDK；同一批数据落库前先做字段归一、来源标记和优先级仲裁。
- 同一实体的推荐优先级默认设为：`Tushare > AkShare > mootdx`，但新闻类数据单独走 `AkShare` 优先。
- 每次导入记录 `source_name`、`source_record_id`、`fetched_at` 和哈希指纹，便于后续去重、审计和问题回放。

## Repository Layout

```text
.
├── .gitignore
├── .editorconfig
├── .env.example
├── Makefile
├── README.md
├── infra/
│   └── docker-compose.yml
├── apps/
│   ├── api/
│   │   ├── pyproject.toml
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   ├── src/swinginsight/
│   │   │   ├── api/
│   │   │   ├── db/
│   │   │   ├── domain/
│   │   │   ├── ingest/
│   │   │   ├── jobs/
│   │   │   └── settings.py
│   │   └── tests/
│   └── web/
│       ├── package.json
│       ├── src/
│       │   ├── app/
│       │   ├── components/
│       │   └── lib/
│       └── tests/
└── docs/
    ├── adr/
    ├── runbooks/
    └── superpowers/plans/
```

## Delivery Milestones

- Week 1: 仓库骨架、数据库、基础运行环境
- Week 2: 数据接入层、拐点识别、波段生成
- Week 3: 股票研究页与人工校正闭环
- Week 4: 新闻对齐、波段详情、特征沉淀
- Week 5: 当前状态识别、相似样本匹配、预测面板
- Week 6: 联调、测试、演示数据、MVP 验收

## Task 1: Bootstrap The Monorepo And Local Environment

**Files:**
- Create: `.gitignore`
- Create: `.editorconfig`
- Create: `.env.example`
- Create: `Makefile`
- Create: `README.md`
- Create: `infra/docker-compose.yml`
- Create: `docs/adr/0001-stack-and-mvp-boundary.md`
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/src/swinginsight/__init__.py`
- Create: `apps/api/src/swinginsight/settings.py`
- Create: `apps/api/tests/test_smoke.py`
- Create: `apps/web/package.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/src/app/page.tsx`
- Create: `apps/web/tests/smoke.test.ts`

- [ ] **Step 1: 初始化仓库与根目录规范文件**

Run: `git init`

Expected: 目录成为可追踪仓库，后续提交步骤可执行。

- [ ] **Step 2: 写后端与前端 smoke test**

```python
def test_backend_smoke() -> None:
    from swinginsight.settings import Settings

    settings = Settings.model_validate({})
    assert settings.app_name == "SwingInsight API"
```

```ts
import { describe, expect, it } from "vitest";

describe("smoke", () => {
  it("keeps the web workspace alive", () => {
    expect(true).toBe(true);
  });
});
```

- [ ] **Step 3: 补齐最小骨架实现，让 smoke test 通过**

最小实现必须包含：
- 可启动的 PostgreSQL `docker-compose`
- API 配置类
- `TUSHARE_TOKEN`、数据源优先级等环境变量说明
- Web 首页占位页
- 根 README 中的启动命令

- [ ] **Step 4: 运行基础验证**

Run: `docker compose -f infra/docker-compose.yml config`

Expected: compose 文件校验通过。

Run: `cd apps/api && uv run pytest tests/test_smoke.py -v`

Expected: PASS

Run: `cd apps/web && pnpm test -- --run`

Expected: PASS

- [ ] **Step 5: 提交基础骨架**

```bash
git add .
git commit -m "chore: bootstrap swinginsight monorepo"
```

## Task 2: Define Schema, Migrations, And Persistence Boundaries

**Files:**
- Create: `apps/api/alembic.ini`
- Create: `apps/api/alembic/env.py`
- Create: `apps/api/alembic/versions/0001_initial_schema.py`
- Create: `apps/api/src/swinginsight/db/base.py`
- Create: `apps/api/src/swinginsight/db/session.py`
- Create: `apps/api/src/swinginsight/db/models/stock.py`
- Create: `apps/api/src/swinginsight/db/models/market_data.py`
- Create: `apps/api/src/swinginsight/db/models/news.py`
- Create: `apps/api/src/swinginsight/db/models/turning_point.py`
- Create: `apps/api/src/swinginsight/db/models/segment.py`
- Create: `apps/api/src/swinginsight/db/models/prediction.py`
- Create: `apps/api/tests/db/test_schema_smoke.py`
- Create: `apps/api/tests/db/test_segment_constraints.py`

- [ ] **Step 1: 先写数据库约束测试**

```python
def test_daily_price_unique_constraint(session):
    insert_daily_price(session, stock_code="000001", trade_date=date(2024, 1, 2), adj_type="qfq")
    with pytest.raises(IntegrityError):
        insert_daily_price(session, stock_code="000001", trade_date=date(2024, 1, 2), adj_type="qfq")
```

```python
def test_segment_uid_is_unique(session):
    insert_segment(session, segment_uid="seg-0001")
    with pytest.raises(IntegrityError):
        insert_segment(session, segment_uid="seg-0001")
```

- [ ] **Step 2: 落地第一版核心表**

第一批必须包含：
- `stock_basic`
- `daily_price`
- `trade_record`
- `news_raw`
- `algo_version`
- `turning_point`
- `point_revision_log`
- `swing_segment`
- `segment_news_map`
- `segment_feature`
- `segment_label`
- `prediction_result`
- `task_run_log`

- [ ] **Step 3: 建立 Alembic 迁移和 session 管理**

要求：
- 开发环境可一键 `upgrade head`
- 测试环境可创建独立库或 schema
- 所有表使用清晰索引名，避免默认匿名索引

- [ ] **Step 4: 运行迁移与约束测试**

Run: `cd apps/api && uv run alembic upgrade head`

Expected: 数据库迁移成功，无缺失依赖。

Run: `cd apps/api && uv run pytest tests/db -v`

Expected: PASS

- [ ] **Step 5: 提交数据库基础设施**

```bash
git add apps/api/alembic.ini apps/api/alembic apps/api/src/swinginsight/db apps/api/tests/db
git commit -m "feat: add initial schema and persistence layer"
```

## Task 3: Wrap Existing Data Download Logic Behind Ingestion Ports

**Files:**
- Create: `apps/api/src/swinginsight/ingest/ports.py`
- Create: `apps/api/src/swinginsight/ingest/source_priority.py`
- Create: `apps/api/src/swinginsight/ingest/daily_price_importer.py`
- Create: `apps/api/src/swinginsight/ingest/trade_record_importer.py`
- Create: `apps/api/src/swinginsight/ingest/news_importer.py`
- Create: `apps/api/src/swinginsight/ingest/adapters/akshare_daily_price_feed.py`
- Create: `apps/api/src/swinginsight/ingest/adapters/akshare_news_feed.py`
- Create: `apps/api/src/swinginsight/ingest/adapters/tushare_daily_price_feed.py`
- Create: `apps/api/src/swinginsight/ingest/adapters/tushare_metadata_feed.py`
- Create: `apps/api/src/swinginsight/ingest/adapters/mootdx_daily_price_feed.py`
- Create: `apps/api/src/swinginsight/jobs/import_market_data.py`
- Create: `apps/api/src/swinginsight/jobs/import_news.py`
- Create: `apps/api/src/swinginsight/jobs/cli.py`
- Create: `apps/api/tests/ingest/test_importers.py`
- Create: `apps/api/tests/ingest/test_job_cli.py`

- [ ] **Step 1: 写 fake adapter 驱动的导入测试**

```python
def test_daily_price_importer_upserts_rows(session, fake_daily_price_feed):
    importer = DailyPriceImporter(session=session, feed=fake_daily_price_feed)
    result = importer.run(stock_code="000001", start=date(2024, 1, 1), end=date(2024, 1, 31))
    assert result.inserted > 0
    assert result.updated >= 0
```

```python
def test_cli_exposes_import_daily_prices(runner):
    result = runner.invoke(cli, ["import-daily-prices", "--stock-code", "000001"])
    assert result.exit_code == 0
```

- [ ] **Step 2: 定义接入协议，不把已有抓取代码耦合进业务层**

至少抽象出三个 port：
- `DailyPriceFeed`
- `TradeRecordFeed`
- `NewsFeed`
- `MetadataFeed`

要求：
- import job 只依赖 port，不依赖某个具体供应商
- 所有导入结果写入 `task_run_log`
- 支持重复执行而不产生重复数据
- 支持多源优先级仲裁和字段级回退

- [ ] **Step 3: 提供本地 demo 适配器与真实适配器挂载点**

建议：
- `ingest/adapters/demo_*` 提供测试和演示数据
- `ingest/adapters/tushare_*` 负责股票基础资料、交易日历、复权和高完整性日线
- `ingest/adapters/akshare_*` 负责新闻与补充抓取
- `ingest/adapters/mootdx_*` 负责行情兜底与交叉校验
- 真实 token 和账号配置统一放进 `.env`，示例文件只保留占位符

- [ ] **Step 4: 运行导入测试**

Run: `cd apps/api && uv run pytest tests/ingest -v`

Expected: PASS

Run: `cd apps/api && uv run python -m swinginsight.jobs.cli import-daily-prices --stock-code 000001 --demo`

Expected: 输出导入统计，并在数据库里可见示例数据。

- [ ] **Step 5: 提交数据接入层**

```bash
git add apps/api/src/swinginsight/ingest apps/api/src/swinginsight/jobs apps/api/tests/ingest
git commit -m "feat: add data ingestion ports and import jobs"
```

## Task 4: Implement Turning Point Detection And Swing Segment Generation

**Files:**
- Create: `apps/api/src/swinginsight/domain/turning_points/local_extrema.py`
- Create: `apps/api/src/swinginsight/domain/turning_points/zigzag.py`
- Create: `apps/api/src/swinginsight/domain/turning_points/filters.py`
- Create: `apps/api/src/swinginsight/domain/segments/builder.py`
- Create: `apps/api/src/swinginsight/domain/segments/metrics.py`
- Create: `apps/api/src/swinginsight/services/turning_point_service.py`
- Create: `apps/api/src/swinginsight/services/segment_generation_service.py`
- Create: `apps/api/src/swinginsight/jobs/rebuild_segments.py`
- Create: `apps/api/tests/domain/test_turning_points.py`
- Create: `apps/api/tests/domain/test_segment_builder.py`

- [ ] **Step 1: 先用可控样本写失败测试**

```python
def test_zigzag_detector_marks_major_turning_points(sample_price_series):
    detector = ZigZagDetector(reversal_pct=0.08)
    points = detector.detect(sample_price_series)
    assert [p.point_type for p in points] == ["trough", "peak", "trough", "peak"]
```

```python
def test_segment_builder_creates_up_and_down_swings(turning_points):
    segments = build_segments(turning_points)
    assert segments[0].trend_direction == "up"
    assert segments[1].trend_direction == "down"
```

- [ ] **Step 2: 落地三层算法结构**

必须分层：
- 原始候选点识别
- 噪音过滤与参数版本化
- 波段构建与指标计算

MVP 先支持：
- 局部极值法
- ZigZag 阈值法
- 简单波动率过滤

- [ ] **Step 3: 将结果持久化，并保留人工修正空间**

要求：
- 自动点写入 `turning_point`
- 参数写入 `algo_version`
- 只从 `is_final = true` 的拐点构建最终波段
- 重新生成波段时保证幂等

- [ ] **Step 4: 运行算法测试和重建任务**

Run: `cd apps/api && uv run pytest tests/domain/test_turning_points.py tests/domain/test_segment_builder.py -v`

Expected: PASS

Run: `cd apps/api && uv run python -m swinginsight.jobs.cli rebuild-segments --stock-code 000001 --algo zigzag`

Expected: 生成拐点和波段，并输出统计信息。

- [ ] **Step 5: 提交识别与波段生成**

```bash
git add apps/api/src/swinginsight/domain apps/api/src/swinginsight/services apps/api/src/swinginsight/jobs apps/api/tests/domain
git commit -m "feat: add turning point detection and swing segment generation"
```

## Task 5: Build The Research Page And Manual Turning Point Correction Flow

**Files:**
- Create: `apps/api/src/swinginsight/api/main.py`
- Create: `apps/api/src/swinginsight/api/routes/stocks.py`
- Create: `apps/api/src/swinginsight/api/routes/turning_points.py`
- Create: `apps/api/src/swinginsight/api/schemas/turning_points.py`
- Create: `apps/web/src/app/stocks/[stockCode]/page.tsx`
- Create: `apps/web/src/components/kline-chart.tsx`
- Create: `apps/web/src/components/turning-point-editor.tsx`
- Create: `apps/web/src/components/trade-marker-layer.tsx`
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/tests/e2e/turning-point-editor.spec.ts`

- [ ] **Step 1: 先写端到端场景测试**

```ts
test("user can add and persist a trough point", async ({ page }) => {
  await page.goto("/stocks/000001");
  await page.getByRole("button", { name: "标记波谷" }).click();
  await page.getByTestId("kline-canvas").click({ position: { x: 420, y: 280 } });
  await page.getByRole("button", { name: "保存修正" }).click();
  await expect(page.getByText("保存成功")).toBeVisible();
});
```

- [ ] **Step 2: 实现研究主页面最小闭环**

页面必须同时展示：
- 股票基础信息
- 日 K 线
- 自动/最终拐点
- 历史买卖点
- 当前状态卡片占位

- [ ] **Step 3: 实现人工校正接口与日志**

要求：
- 新增、删除、移动波峰波谷
- 支持撤销本次编辑
- 写入 `point_revision_log`
- 保存后触发对应股票的波段重建

- [ ] **Step 4: 跑通前后端联调测试**

Run: `cd apps/web && pnpm playwright test tests/e2e/turning-point-editor.spec.ts`

Expected: PASS

Run: `cd apps/api && uv run pytest tests/api -v`

Expected: 至少新增 turning point route 的基础测试并通过。

- [ ] **Step 5: 提交研究页和校正闭环**

```bash
git add apps/api/src/swinginsight/api apps/web/src apps/web/tests/e2e
git commit -m "feat: add research page and manual turning point correction"
```

## Task 6: Align News To Turning Points And Build Segment Detail View

**Files:**
- Create: `apps/api/src/swinginsight/domain/news/dedupe.py`
- Create: `apps/api/src/swinginsight/services/segment_news_alignment_service.py`
- Create: `apps/api/src/swinginsight/api/routes/news.py`
- Create: `apps/api/src/swinginsight/api/routes/segments.py`
- Create: `apps/api/tests/domain/test_news_alignment.py`
- Create: `apps/web/src/app/segments/[segmentId]/page.tsx`
- Create: `apps/web/src/components/news-timeline.tsx`
- Create: `apps/web/src/components/segment-summary-card.tsx`

- [ ] **Step 1: 写窗口关联和去重测试**

```python
def test_alignment_maps_news_within_point_window(session, seeded_segment, seeded_news):
    rows = align_segment_news(session, segment_id=seeded_segment.id, before_days=5, after_days=5)
    assert any(row.relation_type == "before_trough" for row in rows)
```

```python
def test_dedupe_groups_same_title_and_source():
    grouped = dedupe_news_items([news_a, news_b])
    assert len(grouped) == 1
```

- [ ] **Step 2: 实现新闻与波段对齐逻辑**

要求：
- 支持 `T-5 ~ T+5` 拐点窗口
- 支持波段内部新闻集合
- 记录 `distance_days`
- 初版去重规则必须确定且可测试

- [ ] **Step 3: 实现波段详情页**

页面至少展示：
- 波段起止时间、涨跌幅、持续天数
- 技术指标摘要
- 新闻时间线
- 波段标签占位

- [ ] **Step 4: 运行相关新闻与页面测试**

Run: `cd apps/api && uv run pytest tests/domain/test_news_alignment.py -v`

Expected: PASS

Run: `cd apps/web && pnpm test -- --run`

Expected: 页面组件测试通过。

- [ ] **Step 5: 提交新闻对齐闭环**

```bash
git add apps/api/src/swinginsight/domain/news apps/api/src/swinginsight/services apps/api/src/swinginsight/api/routes apps/web/src/app/segments apps/web/src/components
git commit -m "feat: align news with turning points and add segment detail view"
```

## Task 7: Materialize Technical And News Features Into A Queryable Sample Library

**Files:**
- Create: `apps/api/src/swinginsight/domain/features/technical.py`
- Create: `apps/api/src/swinginsight/domain/features/news.py`
- Create: `apps/api/src/swinginsight/domain/labels/rules.py`
- Create: `apps/api/src/swinginsight/services/feature_materialization_service.py`
- Create: `apps/api/src/swinginsight/jobs/materialize_features.py`
- Create: `apps/api/tests/domain/test_feature_materialization.py`
- Create: `apps/web/src/app/library/page.tsx`
- Create: `apps/web/src/components/segment-filter-bar.tsx`
- Create: `apps/web/src/components/segment-table.tsx`

- [ ] **Step 1: 先写核心特征测试**

```python
def test_materializer_persists_technical_and_news_features(session, seeded_segment):
    rows = materialize_segment_features(session, segment_id=seeded_segment.id)
    names = {row.feature_name for row in rows}
    assert "pct_change" in names
    assert "news_count_before_trough_5d" in names
```

- [ ] **Step 2: 只实现第一批高解释性特征**

技术面首批：
- `pct_change`
- `duration_days`
- `max_drawdown_pct`
- `volume_ratio_5d`
- `ma5_above_ma20`
- `macd_cross_flag`

消息面首批：
- `news_count_before_trough_5d`
- `news_count_after_peak_5d`
- `positive_news_ratio`
- `duplicate_news_ratio`

- [ ] **Step 3: 加入基础标签体系和样本库页面**

首批标签：
- `缩量筑底型`
- `放量突破型`
- `消息刺激型`
- `高位见顶型`

样本库页面至少支持：
- 股票代码过滤
- 波段类型过滤
- 标签过滤
- 查看单段详情跳转

- [ ] **Step 4: 运行特征与样本库测试**

Run: `cd apps/api && uv run pytest tests/domain/test_feature_materialization.py -v`

Expected: PASS

Run: `cd apps/api && uv run python -m swinginsight.jobs.cli materialize-features --stock-code 000001`

Expected: 生成 `segment_feature` 和 `segment_label` 数据。

- [ ] **Step 5: 提交特征工程与样本库**

```bash
git add apps/api/src/swinginsight/domain/features apps/api/src/swinginsight/domain/labels apps/api/src/swinginsight/services apps/api/src/swinginsight/jobs apps/api/tests/domain apps/web/src/app/library apps/web/src/components
git commit -m "feat: add segment feature materialization and sample library"
```

## Task 8: Ship Current-State Assessment, Similarity Search, And Prediction Panel

**Files:**
- Create: `apps/api/src/swinginsight/domain/prediction/state_rules.py`
- Create: `apps/api/src/swinginsight/domain/prediction/similarity.py`
- Create: `apps/api/src/swinginsight/services/prediction_service.py`
- Create: `apps/api/src/swinginsight/api/routes/predictions.py`
- Create: `apps/api/tests/domain/test_prediction_service.py`
- Create: `apps/web/src/components/prediction-panel.tsx`
- Create: `apps/web/src/components/similar-case-list.tsx`

- [ ] **Step 1: 先写状态判断和相似检索测试**

```python
def test_prediction_service_returns_state_probabilities(session, seeded_current_state):
    result = PredictionService(session).predict("000001", date(2024, 6, 28))
    assert result.current_state in {"底部构建中", "启动前夕", "主升初期", "高位震荡", "疑似见顶"}
    assert round(result.up_prob_10d + result.flat_prob_10d + result.down_prob_10d, 4) == 1.0
```

```python
def test_similarity_search_returns_ranked_segments(similarity_store):
    matches = similarity_store.find_top_k(current_vector, k=5)
    assert len(matches) == 5
    assert matches[0].score >= matches[-1].score
```

- [ ] **Step 2: 用规则 + 相似样本检索完成第一版预测**

MVP 明确不做：
- 直接预测具体价格
- 黑盒深度学习
- 自动交易信号下发

MVP 必须做：
- 当前状态分类
- 5/10/20 日方向概率
- Top-N 相似历史波段
- 风险提示摘要

- [ ] **Step 3: 实现研究页右侧预测面板**

面板至少展示：
- 当前状态标签
- 方向概率条
- 关键触发特征
- 相似样本列表
- 风险提示

- [ ] **Step 4: 运行预测测试**

Run: `cd apps/api && uv run pytest tests/domain/test_prediction_service.py -v`

Expected: PASS

Run: `cd apps/api && uv run python -m swinginsight.jobs.cli predict-state --stock-code 000001 --predict-date 2024-06-28`

Expected: 输出预测摘要并写入 `prediction_result`。

- [ ] **Step 5: 提交预测闭环**

```bash
git add apps/api/src/swinginsight/domain/prediction apps/api/src/swinginsight/services apps/api/src/swinginsight/api/routes/predictions.py apps/api/tests/domain apps/web/src/components
git commit -m "feat: add current-state prediction and similarity search"
```

## Task 9: Harden The MVP, Add Demo Data, And Prepare Delivery

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `docs/runbooks/dev-setup.md`
- Create: `docs/runbooks/demo-flow.md`
- Create: `apps/api/tests/integration/test_end_to_end_research_flow.py`
- Create: `apps/web/tests/e2e/research-flow.spec.ts`
- Create: `apps/api/scripts/seed_demo_data.py`
- Modify: `README.md`

- [ ] **Step 1: 写 MVP 端到端集成测试**

```python
def test_end_to_end_research_flow(api_client, seeded_demo_project):
    response = api_client.get("/predictions/000001", params={"predict_date": "2024-06-28"})
    assert response.status_code == 200
    assert "current_state" in response.json()
```

```ts
test("research workflow loads chart, saves correction, and shows prediction", async ({ page }) => {
  await page.goto("/stocks/000001");
  await expect(page.getByText("当前状态")).toBeVisible();
  await expect(page.getByText("相似历史样本")).toBeVisible();
});
```

- [ ] **Step 2: 准备演示数据与脚本**

要求：
- 一条可重复执行的 demo seed 脚本
- 至少一只股票拥有完整的价格、新闻、拐点、波段、特征、预测数据
- README 里写明如何一键跑出演示

- [ ] **Step 3: 配置持续集成**

CI 至少执行：
- backend pytest
- frontend unit test
- frontend Playwright smoke
- lint/format 检查

- [ ] **Step 4: 做最终验收验证**

Run: `cd apps/api && uv run pytest -v`

Expected: PASS

Run: `cd apps/web && pnpm test -- --run && pnpm playwright test`

Expected: PASS

Run: `python apps/api/scripts/seed_demo_data.py && make demo`

Expected: 本地可启动完整演示流。

- [ ] **Step 5: 提交 MVP 交付版本**

```bash
git add .github docs README.md apps/api/tests/integration apps/web/tests/e2e apps/api/scripts
git commit -m "chore: harden swinginsight mvp and prepare demo delivery"
```

## MVP Exit Criteria

- 可以导入至少 1 只股票的日线、成交记录和新闻
- 可以自动生成拐点和波段，并允许人工修正
- 修正后可以重算波段、特征和预测结果
- 研究页能展示 K 线、拐点、买卖点、新闻和当前状态
- 系统能输出 Top-N 相似样本和 5/10/20 日方向概率
- 后端、前端、端到端测试全部通过

## Explicit Deferrals

- 分钟级别与 Tick 数据
- 多用户和权限体系
- 自动交易与风控执行
- 大规模异步任务编排
- LLM 驱动的新闻深度理解
- 黑盒深度学习价格预测

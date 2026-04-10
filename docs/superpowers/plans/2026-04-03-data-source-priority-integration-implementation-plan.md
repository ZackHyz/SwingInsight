# Data Source Priority Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现真实可运行的 `akshare -> tushare -> mootdx` 日线优先级链路、独立 metadata 优先级链路，以及与之匹配的日志、研究页刷新路径和文档口径。

**Architecture:** 保持现有 `DailyPriceFeed` / `MetadataFeed` port，不引入新的并行仲裁系统。通过真实 adapter、顺序降级的 provider chain、以及 `DailyPriceImporter` 的实际 source 记录，把 CLI 和研究页实时刷新都切到同一套可诊断的多源选择逻辑上。

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, pytest, tushare, mootdx

---

## Repository Fit

- `apps/api/pyproject.toml`
  - 后端运行依赖，新增 `tushare` 和 `mootdx`。
- `apps/api/src/swinginsight/settings.py`
  - 统一暴露 `TUSHARE_TOKEN`、`DATA_SOURCE_PRIORITY_DAILY_PRICE`、`DATA_SOURCE_PRIORITY_METADATA`。
- `apps/api/src/swinginsight/ingest/adapters/tushare_daily_price_feed.py`
  - `tushare` 日线适配器，输出统一 `daily_price` payload。
- `apps/api/src/swinginsight/ingest/adapters/tushare_metadata_feed.py`
  - `tushare` 股票元数据适配器。
- `apps/api/src/swinginsight/ingest/adapters/mootdx_daily_price_feed.py`
  - `mootdx` 日线兜底适配器。
- `apps/api/src/swinginsight/jobs/import_market_data.py`
  - provider list 构造、顺序降级、metadata fallback 的主入口。
- `apps/api/src/swinginsight/ingest/daily_price_importer.py`
  - 导入落库时记录真实成功 provider，而不是初始化时的占位 source。
- `apps/api/src/swinginsight/services/stock_research_service.py`
  - 研究页实时拉取路径复用新的 provider chain。
- `apps/api/tests/ingest/test_real_data_feeds.py`
  - adapter 映射契约测试，含 `akshare`、`tushare`、`mootdx`。
- `apps/api/tests/jobs/test_import_market_data.py`
  - provider 顺序、降级、metadata 独立优先级的任务级测试。
- `apps/api/tests/ingest/test_importers.py`
  - `DailyPriceImporter` 的 source 记录回归测试。
- `apps/api/tests/services/test_stock_research_service.py`
  - 研究服务实时刷新路径的 provider fallback 回归测试。
- `.env.example`
  - 默认优先级和 env 示例。
- `README.md`
  - 运行说明和能力说明。
- `docs/runbooks/dev-setup.md`
  - 环境和测试文档口径。

### Task 1: Add Dependency Surface And Tushare Adapter Contract Tests

**Files:**
- Modify: `apps/api/pyproject.toml`
- Modify: `apps/api/src/swinginsight/ingest/adapters/tushare_daily_price_feed.py`
- Modify: `apps/api/src/swinginsight/ingest/adapters/tushare_metadata_feed.py`
- Modify: `apps/api/tests/ingest/test_real_data_feeds.py`

- [ ] **Step 1: Write the failing Tushare adapter tests**

```python
def test_tushare_daily_price_feed_maps_pro_bar_rows(monkeypatch):
    rows = TushareDailyPriceFeed(client=fake_client, token="token").fetch_daily_prices(
        stock_code="600157",
        start=date(2026, 3, 30),
        end=date(2026, 3, 31),
    )
    assert rows[0]["stock_code"] == "600157"
    assert rows[0]["trade_date"] == date(2026, 3, 30)
    assert rows[0]["close_price"] == 1.28
    assert rows[0]["data_source"] == "tushare"


def test_tushare_metadata_feed_maps_stock_basic_row(monkeypatch):
    metadata = TushareMetadataFeed(client=fake_client, token="token").fetch_stock_metadata("600157")
    assert metadata["stock_code"] == "600157"
    assert metadata["stock_name"] == "永泰能源"
    assert metadata["market"] == "A"
```

- [ ] **Step 2: Run the Tushare adapter tests to verify they fail**

Run: `cd apps/api && ../../.venv/bin/pytest tests/ingest/test_real_data_feeds.py -k tushare -v`

Expected: FAIL with `NotImplementedError`, missing constructor support, or incorrect field mapping.

- [ ] **Step 3: Add the runtime dependencies**

Update `apps/api/pyproject.toml` to include:

```toml
"tushare>=1.4,<2.0",
"mootdx>=0.11,<1.0",
```

Keep all existing dependencies unchanged.

- [ ] **Step 4: Implement the minimal Tushare adapters**

In `tushare_daily_price_feed.py`, implement:

```python
class TushareDailyPriceFeed:
    def __init__(self, client=None, token: str | None = None) -> None: ...
    def fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None) -> list[dict[str, Any]]: ...
```

In `tushare_metadata_feed.py`, implement:

```python
class TushareMetadataFeed:
    def __init__(self, client=None, token: str | None = None) -> None: ...
    def fetch_stock_metadata(self, stock_code: str) -> dict[str, Any]: ...
```

Implementation requirements:

- Normalize `600157` style codes to the `ts_code` format expected by Tushare.
- Return unified fields already accepted by `DailyPriceImporter`.
- Set `data_source="tushare"` on every daily-price payload.
- Do not fabricate unsupported metadata fields; `industry` can be `None`, `concept_tags` can be `[]`.
- Raise a clear error when `token` is missing, rather than a generic SDK exception.

- [ ] **Step 5: Run the Tushare adapter tests to verify they pass**

Run: `cd apps/api && ../../.venv/bin/pytest tests/ingest/test_real_data_feeds.py -k tushare -v`

Expected: PASS

- [ ] **Step 6: Commit the Tushare adapter work**

```bash
git add apps/api/pyproject.toml \
  apps/api/src/swinginsight/ingest/adapters/tushare_daily_price_feed.py \
  apps/api/src/swinginsight/ingest/adapters/tushare_metadata_feed.py \
  apps/api/tests/ingest/test_real_data_feeds.py
git commit -m "feat: add tushare market data adapters"
```

### Task 2: Add Mootdx Daily Price Fallback Adapter

**Files:**
- Modify: `apps/api/src/swinginsight/ingest/adapters/mootdx_daily_price_feed.py`
- Modify: `apps/api/tests/ingest/test_real_data_feeds.py`

- [ ] **Step 1: Write the failing Mootdx adapter test**

```python
def test_mootdx_daily_price_feed_maps_bars_to_unified_rows(monkeypatch):
    rows = MootdxDailyPriceFeed(client=fake_client).fetch_daily_prices(
        stock_code="600157",
        start=date(2026, 3, 30),
        end=date(2026, 3, 31),
    )
    assert len(rows) == 2
    assert rows[0]["stock_code"] == "600157"
    assert rows[0]["trade_date"] == date(2026, 3, 30)
    assert rows[0]["data_source"] == "mootdx"
```

- [ ] **Step 2: Run the Mootdx adapter test to verify it fails**

Run: `cd apps/api && ../../.venv/bin/pytest tests/ingest/test_real_data_feeds.py -k mootdx -v`

Expected: FAIL with `NotImplementedError`

- [ ] **Step 3: Implement the minimal Mootdx adapter**

Implement:

```python
class MootdxDailyPriceFeed:
    def __init__(self, client=None) -> None: ...
    def fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None) -> list[dict[str, Any]]: ...
```

Implementation requirements:

- Infer market from stock-code prefix.
- Normalize returned bars into the same payload shape used by the other daily-price feeds.
- Fill unsupported fields with `None` instead of fabricating values.
- Set `data_source="mootdx"` on every payload.

- [ ] **Step 4: Run the Mootdx adapter test to verify it passes**

Run: `cd apps/api && ../../.venv/bin/pytest tests/ingest/test_real_data_feeds.py -k mootdx -v`

Expected: PASS

- [ ] **Step 5: Commit the Mootdx adapter**

```bash
git add apps/api/src/swinginsight/ingest/adapters/mootdx_daily_price_feed.py \
  apps/api/tests/ingest/test_real_data_feeds.py
git commit -m "feat: add mootdx daily price fallback adapter"
```

### Task 3: Wire Daily Price Provider Priority And Actual Source Logging

**Files:**
- Modify: `apps/api/src/swinginsight/jobs/import_market_data.py`
- Modify: `apps/api/src/swinginsight/ingest/daily_price_importer.py`
- Modify: `apps/api/src/swinginsight/settings.py`
- Modify: `apps/api/tests/ingest/test_importers.py`
- Modify: `apps/api/tests/ingest/test_real_data_feeds.py`
- Create: `apps/api/tests/jobs/test_import_market_data.py`

- [ ] **Step 1: Write the failing provider-order and importer-source tests**

```python
def test_build_daily_price_feed_uses_default_priority_order():
    settings = Settings.model_validate({})
    feed, source_name = build_daily_price_feed(demo=False, settings=settings)
    assert source_name == "priority"
    assert feed.provider_names == ["akshare", "tushare", "mootdx"]


def test_import_daily_prices_falls_back_to_tushare_when_akshare_fails(monkeypatch, tmp_path):
    monkeypatch.setattr("swinginsight.jobs.import_market_data.build_daily_price_feed", fake_priority_feed)
    result = import_daily_prices(stock_code="000001", start=date(2024, 1, 2), end=date(2024, 1, 3))
    assert result.inserted == 1


def test_daily_price_importer_logs_actual_success_source(session):
    importer = DailyPriceImporter(session=session, feed=fake_priority_feed, source_name="priority")
    importer.run(stock_code="000001", start=date(2024, 1, 2), end=date(2024, 1, 3))
    log = session.scalars(select(TaskRunLog).order_by(TaskRunLog.id.desc())).one()
    assert log.input_params_json["source"] == "tushare"
```

- [ ] **Step 2: Run the provider and importer tests to verify they fail**

Run: `cd apps/api && ../../.venv/bin/pytest tests/jobs/test_import_market_data.py tests/ingest/test_importers.py -v`

Expected: FAIL with missing priority-feed behavior or incorrect log source.

- [ ] **Step 3: Implement minimal daily-price priority selection**

In `settings.py`, expose:

```python
data_source_priority_daily_price: list[str]
data_source_priority_metadata: list[str]
tushare_token: str | None
```

In `import_market_data.py`, implement:

```python
def build_daily_price_feed(*, demo: bool, settings: Settings | None = None) -> tuple[DailyPriceFeed, str]: ...
```

Recommended shape:

- Keep the public signature compatible for current callers.
- Return a priority/composite feed that tries `akshare`, then `tushare`, then `mootdx`.
- Store the actually successful provider name on the composite feed, for example `resolved_source_name`.
- Raise one aggregated error only after all candidates fail.

In `daily_price_importer.py`, resolve the real source for `TaskRunLog` and normalized payloads from:

1. `feed.resolved_source_name`
2. first payload `data_source`
3. constructor `source_name`

- [ ] **Step 4: Run the provider and importer tests to verify they pass**

Run: `cd apps/api && ../../.venv/bin/pytest tests/jobs/test_import_market_data.py tests/ingest/test_importers.py -v`

Expected: PASS

- [ ] **Step 5: Commit the daily-price priority chain**

```bash
git add apps/api/src/swinginsight/jobs/import_market_data.py \
  apps/api/src/swinginsight/ingest/daily_price_importer.py \
  apps/api/src/swinginsight/settings.py \
  apps/api/tests/jobs/test_import_market_data.py \
  apps/api/tests/ingest/test_importers.py \
  apps/api/tests/ingest/test_real_data_feeds.py
git commit -m "feat: add daily price provider fallback chain"
```

### Task 4: Add Metadata Priority Resolution And Research-Service Integration

**Files:**
- Modify: `apps/api/src/swinginsight/jobs/import_market_data.py`
- Modify: `apps/api/src/swinginsight/services/stock_research_service.py`
- Modify: `apps/api/tests/jobs/test_import_market_data.py`
- Modify: `apps/api/tests/services/test_stock_research_service.py`

- [ ] **Step 1: Write the failing metadata and research-path tests**

```python
def test_ensure_stock_basic_uses_metadata_priority_separately(monkeypatch, session):
    monkeypatch.setenv("DATA_SOURCE_PRIORITY_DAILY_PRICE", "mootdx")
    monkeypatch.setenv("DATA_SOURCE_PRIORITY_METADATA", "akshare,tushare,mootdx")
    ensure_stock_basic(session, stock_code="600157")
    stock = session.scalar(select(StockBasic).where(StockBasic.stock_code == "600157"))
    assert stock.stock_name == "永泰能源"


def test_ensure_stock_basic_falls_back_to_minimal_record_when_all_metadata_providers_fail(session, monkeypatch):
    monkeypatch.setattr("swinginsight.jobs.import_market_data.build_metadata_feeds", lambda **_: [])
    ensure_stock_basic(session, stock_code="000001")
    stock = session.scalar(select(StockBasic).where(StockBasic.stock_code == "000001"))
    assert stock.stock_name == "000001"


def test_stock_research_service_refresh_live_prices_uses_priority_feed(monkeypatch, session):
    monkeypatch.setattr("swinginsight.jobs.import_market_data.build_daily_price_feed", fake_priority_feed)
    result = StockResearchService(session).ensure_stock_ready("600157")
    assert result is True
```

- [ ] **Step 2: Run the metadata and research-service tests to verify they fail**

Run: `cd apps/api && ../../.venv/bin/pytest tests/jobs/test_import_market_data.py tests/services/test_stock_research_service.py -v`

Expected: FAIL with missing metadata provider chain or stale `ensure_stock_basic()` signature assumptions.

- [ ] **Step 3: Implement the minimal metadata priority chain**

In `import_market_data.py`, implement:

```python
def build_metadata_feeds(*, settings: Settings | None = None) -> list[tuple[MetadataFeed, str]]: ...
def ensure_stock_basic(session, stock_code: str, metadata_feeds: list[tuple[MetadataFeed, str]] | None = None) -> None: ...
```

Implementation requirements:

- Use `DATA_SOURCE_PRIORITY_METADATA` independently from the daily-price chain.
- Support `akshare` and `tushare`.
- Skip unsupported metadata providers, such as `mootdx`, without crashing.
- When all metadata providers fail, create or update a minimal `StockBasic` placeholder instead of aborting the whole refresh path.

In `stock_research_service.py`:

- Remove any direct assumptions that `ensure_stock_basic()` depends on the selected daily-price feed.
- Keep the live-refresh path behavior unchanged from the caller perspective.

- [ ] **Step 4: Run the metadata and research-service tests to verify they pass**

Run: `cd apps/api && ../../.venv/bin/pytest tests/jobs/test_import_market_data.py tests/services/test_stock_research_service.py -v`

Expected: PASS

- [ ] **Step 5: Commit the metadata and service integration**

```bash
git add apps/api/src/swinginsight/jobs/import_market_data.py \
  apps/api/src/swinginsight/services/stock_research_service.py \
  apps/api/tests/jobs/test_import_market_data.py \
  apps/api/tests/services/test_stock_research_service.py
git commit -m "feat: add metadata provider fallback chain"
```

### Task 5: Align Docs, Example Config, And Final Verification

**Files:**
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/runbooks/dev-setup.md`

- [ ] **Step 1: Update the example configuration**

Make `.env.example` match the implemented defaults:

- `DATA_SOURCE_PRIORITY_DAILY_PRICE=akshare,tushare,mootdx`
- `DATA_SOURCE_PRIORITY_METADATA=akshare,tushare,mootdx`
- keep `TUSHARE_TOKEN` documented as optional for fallback but required for direct Tushare success

- [ ] **Step 2: Update README and runbooks**

Document:

- actual default provider order
- automatic fallback behavior
- independent metadata priority chain
- dependency/runtime expectations for `tushare` and `mootdx`

Also fix any stale setup text that contradicts `apps/api/pyproject.toml`, including Python-version wording.

- [ ] **Step 3: Run targeted verification**

Run:

```bash
cd apps/api
../../.venv/bin/pytest tests/ingest/test_real_data_feeds.py tests/ingest/test_importers.py tests/jobs/test_import_market_data.py tests/services/test_stock_research_service.py -v
```

Expected: PASS

- [ ] **Step 4: Run representative regression coverage**

Run:

```bash
cd apps/api
../../.venv/bin/pytest tests/api/test_turning_points_api.py tests/integration/test_end_to_end_research_flow.py -v
```

Expected: PASS, confirming research-page entry paths still work after the provider-chain refactor.

- [ ] **Step 5: Commit the docs and verification batch**

```bash
git add .env.example README.md docs/runbooks/dev-setup.md
git commit -m "docs: align market data source configuration"
```

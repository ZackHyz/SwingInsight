# Task 5 Design: Research Page And Manual Turning Point Correction

## Goal

Build the minimum closed loop for manual turning point correction:

- View one stock research page
- Inspect price series and automatic/final turning points
- Add, delete, and move final turning points
- Save the final point set
- Persist revision logs
- Rebuild swing segments after save

This task optimizes for workflow correctness, not final visual polish.

## Scope

### In Scope

- A minimal FastAPI app for research-page APIs
- A single stock research page at `/stocks/[stockCode]`
- Lightweight chart rendering with SVG
- Manual turning point editing in the browser
- One-request commit flow for final point persistence
- Revision logging to `point_revision_log`
- Segment rebuild after manual save
- Basic API tests and a minimal browser flow test

### Out Of Scope

- Full production charting library integration
- Multi-stock navigation and filter views
- Real draft sessions persisted on the server
- Complex undo/redo history across requests
- Rich trade marker semantics beyond placeholders
- Final visual design polish

## Recommended Approach

Use a single-page, single-request commit workflow.

The browser keeps an in-memory editable copy of the final turning points. When the user saves, the client submits the entire final point set plus a derived operation list. The API validates and persists that final set, writes revision logs, and triggers segment rebuild.

This is preferred over incremental server-side draft mutation because:

- it is simpler to reason about in an MVP
- it keeps save semantics deterministic
- it avoids draft session state on the backend
- it makes rebuilding segments straightforward

## Backend Design

## API Surface

### `GET /stocks/{stockCode}`

Returns a research-page aggregate payload:

- `stock`: stock basic info
- `prices`: daily price series for the selected stock
- `auto_turning_points`: system-generated turning points
- `final_turning_points`: current final points shown in editor
- `trade_markers`: placeholder records for future trade overlays
- `current_state`: placeholder prediction/status card data

This endpoint is optimized for the page boot path so the frontend can hydrate from one request.

### `POST /stocks/{stockCode}/turning-points/commit`

Accepts:

- `final_points`: the full final point set after user edits
- `operations`: client-derived change records such as `add`, `delete`, `move`
- `operator`: optional operator identifier

Performs:

1. Validates and normalizes the submitted point set
2. Deletes the current final set for the stock
3. Recreates the final set as manual final points
4. Writes one `point_revision_log` row per operation
5. Rebuilds swing segments for the stock
6. Returns latest final points and rebuild summary

## Persistence Rules

Automatic turning points remain in `turning_point` with `source_type="system"`.

Manual final points are stored in `turning_point` with:

- `source_type="manual"`
- `is_final=true`
- `version_code` derived from the manual edit flow, for example `manual:latest`

When saving manual edits:

- existing manual final points for the stock are replaced
- system-generated points are preserved
- segment generation rebuilds from the current `is_final=true` point set

## Logging Rules

Each user-visible edit operation writes to `point_revision_log`.

Examples:

- `add`: new manual point inserted
- `delete`: final point removed
- `move`: point date and/or price changed

`old_value_json` and `new_value_json` must contain enough information to reconstruct what changed at the record level.

## Service Layer

Add a dedicated service for manual point commit so route handlers stay thin.

Responsibilities:

- load current final points
- compare with submitted final points
- persist the new final set
- write revision logs
- invoke segment rebuild

This service should reuse the existing segment rebuild path introduced in Task 4.

## Frontend Design

## Route

Create `/stocks/[stockCode]` as the research page.

The page fetches from the backend aggregate endpoint and renders four areas:

1. stock header card
2. price chart with turning points
3. turning point editing panel
4. current-state placeholder card

## Components

### `KlineChart`

Render a lightweight SVG chart based on daily closing prices.

For this MVP:

- plot price as a line, not full candlesticks
- overlay automatic and final turning points
- expose click coordinates or nearest trade date selection back to the editor
- expose a stable `data-testid` for automation

This keeps the interaction surface small while still validating the editing workflow.

### `TurningPointEditor`

Controls the edit mode and local state.

Buttons:

- `标记波峰`
- `标记波谷`
- `删除选中点`
- `撤销本次编辑`
- `保存修正`

Behavior:

- user chooses an edit action
- user clicks a date on the chart
- editor mutates the in-memory final point set
- `撤销本次编辑` resets to the page-load snapshot
- `保存修正` posts the full final point set and operations

### `TradeMarkerLayer`

Render placeholder buy/sell markers if present in API response. This component exists to keep the page structure aligned with the product plan even though real trade annotation is still deferred.

### `api.ts`

Encapsulate fetch calls for:

- loading stock research data
- committing manual turning points

## Client State Model

Keep client state intentionally small:

- `initialFinalPoints`
- `draftFinalPoints`
- `selectedPointId`
- `pendingAction`
- `operations`
- `saveStatus`

No persisted draft session is needed in this task.

## Data Flow

1. Page loads aggregate stock payload
2. Editor initializes local editable state from `final_turning_points`
3. User edits points on the chart
4. User saves
5. API persists manual final points and rebuilds segments
6. Page refreshes final points from response and shows success state

## Error Handling

Backend:

- return `404` if stock is unknown
- return `422` for malformed point payloads
- return `400` if final point order is invalid or point types do not alternate

Frontend:

- show inline save success or failure messages
- disable save while request is in flight
- revert to last committed state only on explicit `撤销本次编辑`

## Testing Strategy

## Backend Tests

Add `tests/api/test_turning_points.py` covering:

- research aggregate endpoint returns expected sections
- commit endpoint persists final points
- commit endpoint writes `point_revision_log`
- commit endpoint triggers segment rebuild

## Frontend Tests

Add component or page tests for:

- action button state transitions
- local draft mutation
- success message after save

## Browser Flow

Add a minimal e2e flow for:

- opening `/stocks/000001`
- selecting `标记波谷`
- clicking the chart
- saving edits
- seeing `保存成功`

## Delivery Notes

This task intentionally uses a minimal chart and in-memory edit model. If the workflow proves stable, a later task can swap in a richer charting implementation without changing the save contract.

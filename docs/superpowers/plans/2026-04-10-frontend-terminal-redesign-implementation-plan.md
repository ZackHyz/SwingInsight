# Frontend Terminal Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the frontend into a unified dark terminal-style research product while preserving current API behavior and core user flows.

**Architecture:** Add a shared app shell and terminal design system layer first, then migrate each page into that structure one by one. Use TDD to lock in new shell/layout semantics while preserving search, filtering, detail navigation, and modal interactions, and fold the existing `typecheck` failures into the same migration.

**Tech Stack:** React 19, Vite, TypeScript, Vitest, Testing Library, CSS via app-level stylesheet and semantic class names

---

### Task 1: Add Terminal Design System Foundation

**Files:**
- Create: `apps/web/src/styles/app-shell.css`
- Modify: `apps/web/index.html`
- Modify: `apps/web/src/main.tsx`
- Test: `apps/web/tests/smoke.test.ts`

- [ ] **Step 1: Write the failing home shell test**

Add assertions in `apps/web/tests/smoke.test.ts` for the new terminal landing structure:

```ts
render(<HomePage />);
expect(screen.getByText("SwingInsight Terminal")).toBeTruthy();
expect(screen.getByRole("link", { name: "Overview" })).toBeTruthy();
expect(screen.getByRole("link", { name: "Research" })).toBeTruthy();
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm test -- --run tests/smoke.test.ts`

Expected: FAIL because the current home page does not render the terminal shell or nav links.

- [ ] **Step 3: Implement the global shell entry styling**

Create `apps/web/src/styles/app-shell.css` with:

- terminal color tokens
- typography variables
- panel, nav, metric, table, badge, button, dialog, and state classes
- responsive shell layout classes

Update `apps/web/index.html` to:

- preload terminal fonts via web-safe fallback or external `@import`-free stack
- remove the current prototype inline `<style>`
- keep the page root clean for app-level styles

Update `apps/web/src/main.tsx` to import the stylesheet before rendering the app.

- [ ] **Step 4: Run the test to verify it passes**

Run: `pnpm test -- --run tests/smoke.test.ts`

Expected: PASS with the new shell semantics available to the page.

- [ ] **Step 5: Commit**

```bash
git add apps/web/index.html apps/web/src/main.tsx apps/web/src/styles/app-shell.css apps/web/tests/smoke.test.ts
git commit -m "feat: add terminal design system foundation"
```

### Task 2: Introduce Shared App Shell And Terminal Primitives

**Files:**
- Create: `apps/web/src/components/app-shell.tsx`
- Create: `apps/web/src/components/terminal-panel.tsx`
- Create: `apps/web/src/components/status-pill.tsx`
- Modify: `apps/web/src/app/page.tsx`
- Test: `apps/web/tests/smoke.test.ts`

- [ ] **Step 1: Extend the failing shell test for product entry content**

Add assertions in `apps/web/tests/smoke.test.ts` for:

- terminal hero title
- code entry CTA or quick-entry area
- shell navigation labels
- a capability section explaining the three core workflows

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm test -- --run tests/smoke.test.ts`

Expected: FAIL because the current page still has only the bootstrap copy.

- [ ] **Step 3: Implement shared shell components and migrate the home page**

Create `AppShell`, `TerminalPanel`, and `StatusPill` with focused responsibilities:

- `AppShell`: layout frame, side nav, top bar, content container
- `TerminalPanel`: reusable titled surface
- `StatusPill`: reusable state chip

Refactor `apps/web/src/app/page.tsx` to render:

- terminal landing hero
- quick links into research and pattern library
- capability panels for turning points, news events, and similar cases
- demo stock entry hint

- [ ] **Step 4: Run the test to verify it passes**

Run: `pnpm test -- --run tests/smoke.test.ts`

Expected: PASS with the new terminal landing page structure.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/app-shell.tsx apps/web/src/components/terminal-panel.tsx apps/web/src/components/status-pill.tsx apps/web/src/app/page.tsx apps/web/tests/smoke.test.ts
git commit -m "feat: add terminal app shell and landing page"
```

### Task 3: Rebuild The Stock Research Page As The Main Workspace

**Files:**
- Modify: `apps/web/src/app/stocks/[stockCode]/page.tsx`
- Modify: `apps/web/src/components/prediction-panel.tsx`
- Modify: `apps/web/src/components/turning-point-editor.tsx`
- Modify: `apps/web/src/components/kline-chart.tsx`
- Modify: `apps/web/src/components/similar-case-list.tsx`
- Test: `apps/web/tests/stock-research-page-fetch.test.tsx`
- Test: `apps/web/tests/prediction-panel.test.tsx`
- Test: `apps/web/tests/turning-point-editor.test.tsx`
- Test: `apps/web/tests/similar-case-list.test.tsx`

- [ ] **Step 1: Write the failing research workspace tests**

Update `apps/web/tests/stock-research-page-fetch.test.tsx` and `apps/web/tests/prediction-panel.test.tsx` to assert the new workspace semantics:

- shell chrome is visible on the research page
- a left context rail exists
- the chart workspace is the main content area
- the intelligence rail exists
- the news section is an event flow area rather than a plain list

In `apps/web/tests/similar-case-list.test.tsx`, keep the modal behavior but assert the new terminal dialog structure.

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `pnpm test -- --run tests/stock-research-page-fetch.test.tsx tests/prediction-panel.test.tsx tests/similar-case-list.test.tsx tests/turning-point-editor.test.tsx`

Expected: FAIL because the current research page does not expose the new shell/workspace structure.

- [ ] **Step 3: Implement the research workspace layout**

Refactor `apps/web/src/app/stocks/[stockCode]/page.tsx` to render inside `AppShell` and organize content into:

- `Instrument Context Rail`
- `Chart Workspace`
- `Intelligence Rail`
- `Event Flow`

Refactor the child components so they use shared panel classes instead of loose inline styles.

While modifying `apps/web/src/components/similar-case-list.tsx`, fix the existing type narrowing issue by normalizing nullable numeric fields before passing them to formatter helpers.

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `pnpm test -- --run tests/stock-research-page-fetch.test.tsx tests/prediction-panel.test.tsx tests/similar-case-list.test.tsx tests/turning-point-editor.test.tsx`

Expected: PASS with the research workspace and modal behavior preserved.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/app/stocks/[stockCode]/page.tsx apps/web/src/components/prediction-panel.tsx apps/web/src/components/turning-point-editor.tsx apps/web/src/components/kline-chart.tsx apps/web/src/components/similar-case-list.tsx apps/web/tests/stock-research-page-fetch.test.tsx apps/web/tests/prediction-panel.test.tsx apps/web/tests/turning-point-editor.test.tsx apps/web/tests/similar-case-list.test.tsx
git commit -m "feat: rebuild stock research page as terminal workspace"
```

### Task 4: Rebuild The Pattern Library As An Analysis View

**Files:**
- Modify: `apps/web/src/app/library/page.tsx`
- Modify: `apps/web/src/components/segment-filter-bar.tsx`
- Modify: `apps/web/src/components/segment-table.tsx`
- Test: `apps/web/tests/library-page.test.tsx`

- [ ] **Step 1: Write the failing library analysis test**

Expand `apps/web/tests/library-page.test.tsx` to assert:

- shell navigation is present
- the filter bar is presented as an analysis sidebar
- a results summary header is shown
- table rows remain filterable by stock code and label

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm test -- --run tests/library-page.test.tsx`

Expected: FAIL because the current page is only a heading, filters, and bare table.

- [ ] **Step 3: Implement the analysis layout**

Refactor the page into `AppShell` and render:

- summary strip
- fixed-style filter panel
- high-density result table

Update `segment-filter-bar.tsx` and `segment-table.tsx` to consume the shared terminal classes and preserve current filtering/detail link behavior.

- [ ] **Step 4: Run the test to verify it passes**

Run: `pnpm test -- --run tests/library-page.test.tsx`

Expected: PASS with the new analysis layout and preserved filtering behavior.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/app/library/page.tsx apps/web/src/components/segment-filter-bar.tsx apps/web/src/components/segment-table.tsx apps/web/tests/library-page.test.tsx
git commit -m "feat: redesign pattern library as analysis view"
```

### Task 5: Rebuild Segment Detail As Drill-Down Analysis

**Files:**
- Modify: `apps/web/src/app/segments/[segmentId]/page.tsx`
- Modify: `apps/web/src/components/segment-summary-card.tsx`
- Modify: `apps/web/src/components/news-timeline.tsx`
- Test: `apps/web/tests/segment-detail-page.test.tsx`

- [ ] **Step 1: Write the failing detail page test**

Update `apps/web/tests/segment-detail-page.test.tsx` to assert:

- shell chrome is present
- summary metrics render in a top metric band
- timeline section remains visible
- labels render in a dedicated analysis panel

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm test -- --run tests/segment-detail-page.test.tsx`

Expected: FAIL because the current detail page is still a plain stack of sections.

- [ ] **Step 3: Implement the drill-down layout**

Refactor the detail page to use `AppShell` and terminal panels.

Update `segment-summary-card.tsx` to display metrics in a compact band.

Update `news-timeline.tsx` so it renders as an analysis timeline rather than a plain list.

- [ ] **Step 4: Run the test to verify it passes**

Run: `pnpm test -- --run tests/segment-detail-page.test.tsx`

Expected: PASS with the drill-down page structure in place.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/app/segments/[segmentId]/page.tsx apps/web/src/components/segment-summary-card.tsx apps/web/src/components/news-timeline.tsx apps/web/tests/segment-detail-page.test.tsx
git commit -m "feat: redesign segment detail as drill-down analysis"
```

### Task 6: Fix TypeScript Regressions And Run Full Verification

**Files:**
- Modify: `apps/web/tests/similar-case-list.test.tsx`
- Modify: any touched frontend files required for final type safety
- Test: `apps/web/tests/*`

- [ ] **Step 1: Write the failing type-safe test fixture changes**

Normalize the `SegmentChartWindowData` fixtures in `apps/web/tests/similar-case-list.test.tsx` so `point_type` values are typed as `"peak" | "trough"` rather than widened `string`.

- [ ] **Step 2: Run `typecheck` to verify the failure is now isolated to implementation gaps**

Run: `pnpm typecheck`

Expected: FAIL only on the known nullable formatter issue and/or fixture typing until the production code and fixtures are aligned.

- [ ] **Step 3: Implement minimal fixes for full type safety**

Make the smallest necessary changes in the touched files so:

- `similar-case-list.tsx` handles nullable numeric values safely
- the test fixtures satisfy `SegmentChartWindowData`
- no new `tsc` errors are introduced by the redesign

- [ ] **Step 4: Run the full verification suite**

Run:

```bash
pnpm test -- --run
pnpm typecheck
```

Expected:

- all Vitest files pass
- `tsc --noEmit` exits with code 0

- [ ] **Step 5: Commit**

```bash
git add apps/web
git commit -m "fix: align terminal redesign with type safety"
```

### Task 7: Update Docs And Prepare Branch For Review

**Files:**
- Modify: `README.md`
- Modify: `docs/runbooks/dev-setup.md` if frontend launch/verification notes need updating

- [ ] **Step 1: Write the failing documentation delta checklist**

Create a short checklist covering:

- frontend is now a terminal-style workspace
- core verification commands remain `pnpm test -- --run` and `pnpm typecheck`
- no new runtime requirements were added beyond the existing web install

- [ ] **Step 2: Review the current docs and identify stale frontend wording**

Run:

```bash
rg -n "bootstrap|welcome copy|frontend" README.md docs/runbooks/dev-setup.md
```

Expected: locate any outdated description of the old prototype-style frontend.

- [ ] **Step 3: Implement the minimal doc updates**

Update the README and runbook text to describe the terminal-style frontend accurately without overstating new capabilities.

- [ ] **Step 4: Re-run the full verification suite**

Run:

```bash
pnpm test -- --run
pnpm typecheck
```

Expected: still green after docs-only edits.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/runbooks/dev-setup.md
git commit -m "docs: describe terminal frontend workspace"
```

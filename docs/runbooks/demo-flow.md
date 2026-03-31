# Demo Flow

## Seed Demo Data

```bash
.venv/bin/python apps/api/scripts/seed_demo_data.py
```

This seeds `000001` with:

- price history
- auto/manual turning points
- swing segments and labels
- aligned news items
- one saved prediction snapshot

## Start The Demo

```bash
make demo
```

Default endpoints:

- API research payload: `http://127.0.0.1:8000/stocks/000001`
- Browser smoke page: `http://127.0.0.1:4173/stocks/000001`

## Suggested Walkthrough

1. Open the API payload and confirm `current_state.label` is not `placeholder`.
2. Open the browser page and confirm the chart placeholder and prediction panel render.
3. Click `标记波谷`, click the chart, then click `保存修正`.
4. Confirm the page shows `保存成功`.

# Search existing Oracle results

These controls search stored backtest results. They do not launch a new backtest,
change IRR calculations, or recompute an existing run for a different date range.
`num_days` is the recorded daily-observation count for that run, not deployment age
or the elapsed calendar time between its start and end labels.

The methods below belong to this reviewed source revision. An installed package
must contain these parameters, and the serving Oracle/API contract must support
them. A local build or reviewed PR does not establish production availability.

## Choose the history length

Bounds are inclusive. Set both bounds to 90 for exactly 90 recorded days, or to
180 for exactly 180 days. A 90-180 range includes all matching stored run lengths.

```python
# Exactly 90 recorded days, ranked by simple annualized return.
page = client.oracle.list_results(
    min_days=90, max_days=90,
    min_simple_annualized_return=0,
    sort="simple_annualized_return", order="desc",
)

# Any stored length from 90 through 180 recorded days.
page = client.oracle.list_results(
    min_days=90, max_days=180,
    min_simple_annualized_return=0,
    sort="simple_annualized_return", order="desc",
)
if page.effective_filters and page.effective_filters.notice:
    print(page.effective_filters.notice)
```

Oracle applies the 182-day default only when `min_irr` is supplied (including
zero), `min_days` is omitted, and `use_irr_duration_default` is true or omitted.
A search that sets only a minimum IRR therefore returns the applied minimum and
a notice:

```python
page = client.oracle.list_results(min_irr=14, sort="irr_annualized", order="desc")
filters = page.effective_filters
if filters is not None:
    print(filters.min_days)                      # 182
    print(filters.irr_duration_default_applied)  # True
    if filters.notice:
        print(filters.notice)
```

An explicit `min_days=0`, `90`, or `180` overrides that default. To clear the
default entirely, omit `min_days` and pass false. This search returns no notice:

```python
page = client.oracle.list_results(
    min_irr=14, use_irr_duration_default=False,
    sort="irr_annualized", order="desc",
)
```

Searches without `min_irr` have no automatic duration minimum. The response's
`effective_filters` reports `min_days`, `max_days`,
`irr_duration_default_applied`, and a nullable `notice`. A maximum below the
resolved minimum is invalid; override or clear the default before searching
shorter histories. A numeric minimum of zero still excludes unknown durations;
clearing the duration filter can retain them.

## Choose the return measure

- `total_return`: the period total return percentage for the stored run. Use
  `min_return` and `max_return`.
- `irr_annualized`: the existing annualized IRR. Use `min_irr` and `max_irr`.
- `simple_annualized_return`: total return percentage / recorded days * 365,
  without compounding. Use `min_simple_annualized_return` and
  `max_simple_annualized_return`.
- `avg_daily_return`: mean daily return percentage. Use `min_avg_daily_return`
  and `max_avg_daily_return`.
- `avg_closed_trade_return`: the unweighted mean of each closed trade's net
  profit/loss / absolute entry notional * 100. Use
  `min_avg_closed_trade_return` and `max_avg_closed_trade_return`.

Use `min_closed_trades` for a closed-trade sample floor. Sort with any metric name
above, `num_days`, or `closed_trade_count`.
Return bounds use percentage units: `2` means 2%, not 200%. Zero and negative
bounds are valid. Undefined metrics or unavailable historical trade data remain
null; do not display or rank them as zero. Non-finite or reversed bounds are
rejected by the server.

## Preserve notices when paging

`list_results` returns the complete page envelope. `list_results_iter` yields
rows only; use its optional `on_page` callback to inspect each page's actual
server-resolved filters and display a notice when present:

```python
def show_filters(page):
    if page.effective_filters and page.effective_filters.notice:
        print(page.effective_filters.notice)

rows = client.oracle.list_results_iter(
    min_irr=14, min_days=90, max_days=180,
    page_size=50, on_page=show_filters,
)
for row in rows:
    print(row["num_days"], row.get("simple_annualized_return"))
```

The callback runs before each validated page is yielded, including an empty final
page. Filters are forwarded on every request. Older servers may omit
`effective_filters`; its absence is not proof that these controls are supported.
`page.effective_filters` is `None` in that case, and a key the server omits
inside it is `None`.

## TypeScript and the shared workflow

Use the generated public operation, with the same parameter names and explicit
`false` when clearing the default. The response preserves Oracle's envelope.
These legacy result operations have an open response schema, so
`effective_filters` is not typed on the response. The exported
`oracleEffectiveFilters(response)` helper checks its shape at runtime and returns
a typed `OracleEffectiveFilters` object, or `null` when the server did not return
the field. A key the server omits is `null`; an unexpected shape throws
`MalformedResponseError`.

```typescript
import { MangroveAI, oracleEffectiveFilters } from '@mangrove-ai/sdk';

// Only a minimum IRR: Oracle applies its 182-day minimum and returns a notice.
const defaulted = await client.request('GET /api/v1/oracle/results', {
  query: { min_irr: 14, sort: 'irr_annualized', order: 'desc' },
});
const filters = oracleEffectiveFilters(defaulted);
if (filters !== null) {
  console.log(filters.min_days);                      // 182
  console.log(filters.irr_duration_default_applied);  // true
  if (filters.notice) console.log(filters.notice);
}

// The default cleared: shorter histories are included and no notice is returned.
const page = await client.request('GET /api/v1/oracle/results', {
  query: {
    min_irr: 14, use_irr_duration_default: false,
    max_days: 180,
    min_closed_trades: 10, sort: 'avg_closed_trade_return', order: 'desc',
  },
});
```

For one experiment, use
`GET /api/v1/oracle/experiments/{experiment_id}/results` with its path identity.
The Python `client.strategy_workflow.find_sweep_runs` and TypeScript
`client.strategyWorkflow.findSweepRuns` helpers expose the shared workflow;
its sort parameter is `sort_by`, and it returns the same `effective_filters`,
which `oracleEffectiveFilters` also reads.
Workflow metric display strings include `%`; `metrics_raw` retains the numeric
percentage values. Load the server's current `sweep-results` skill before an
agent-led workflow and report the chosen sorting measure and any duration notice.

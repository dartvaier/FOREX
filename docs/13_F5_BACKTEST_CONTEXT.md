# F5.2 — BacktestContext

## Status

```text
IMPLEMENTED
```

`BacktestContext` is the only market-data boundary visible to a future Strategy.
It preserves the F5.1 flow: Strategy → Signal → Risk Engine → OrderIntent → Execution → Fill → Portfolio.

## No look-ahead contract

For every visible bar, `bar.start + timeframe_duration <= context.current_time`.

- `BAR_OPEN` exposes no current OHLC, only past closed bars.
- `BAR_CLOSE` makes the just-finished bar available.
- Gaps remain gaps; no candle is synthesized.
- The source DataFrame and feed are never exposed.

The tests cover the information boundary, gaps, immutability, malformed events,
history limits, and future-OHLC attempts. GitHub Actions runs non-integration
tests on Python 3.12–3.14.

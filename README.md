# EDICT Strategy CLI (Python)

EDICT is an extensible **CLI strategy framework**.

It gives you:
- A clean **strategy interface**
- A **strategy loader** (load strategies by `module:ClassName`)
- A consistent **CLI** to run strategies
- YAML-based config

## Quick start

```bash
# 1) install
poetry install

# 2) generate a new strategy skeleton
poetry run edict new-strategy mean-reversion --out ./my-strategy

# 3) run demo strategy
poetry run edict run --config configs/demo.yaml
# (or explicitly)
poetry run edict run --strategy edict.strategies.demo:DemoStrategy --config configs/demo.yaml

# 4) list built-in strategies
poetry run edict strategies
```

## TradingView webhook → WeCom (企业微信)

Start a webhook server that receives TradingView alerts and forwards them to WeCom.

### Configure env

```bash
export WECOM_WEBHOOK_URL='https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...'
# optional:
export TV_WEBHOOK_SECRET='your-secret'
```

### Run server

```bash
poetry run edict tv-serve --host 0.0.0.0 --port 8787
```

### TradingView Alert message (recommended JSON)

Use **Webhook URL**:

`http(s)://<your-server>:8787/tv/webhook`

Message:

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "exchange": "BINANCE",
  "signal": "breakout_long",
  "side": "long",
  "price": {{close}},
  "ts": "{{timenow}}",
  "note": "optional"
}
```

If you set `TV_WEBHOOK_SECRET`, add a header in TradingView:
- `X-TV-SECRET: <your-secret>`


## Concepts

- **Strategy**: implements `Strategy` interface (`on_start`, `on_bar`, `on_finish`).
- **Engine**: runs a strategy against a stream of bars/events.
- **Loader**: loads a strategy class from `module:ClassName`.

## Layout

- `src/edict/cli/` CLI commands
- `src/edict/core/` core interfaces + engine + loader
- `src/edict/strategies/` built-in example strategies
- `configs/` example configs

## Extending

Create your own strategy class and run it:

```bash
poetry run edict run --strategy your_pkg.your_mod:MyStrategy --config path/to/config.yaml
```

## License

MIT

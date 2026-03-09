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
poetry run edict run --strategy edict.strategies.demo:DemoStrategy --config configs/demo.yaml

# 4) list built-in strategies
poetry run edict strategies
```

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

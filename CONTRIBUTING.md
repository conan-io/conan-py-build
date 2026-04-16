# Contributing

## Dev setup

```bash
git clone https://github.com/conan-io/conan-py-build.git
cd conan-py-build
pip install -e ".[dev]"
```

## Running tests

Unit tests cover individual functions in isolation. They shouldn't invoke Conan:

```bash
pytest tests/test_unit.py -v
```

Integration tests exercise the full PEP 517 hook flow (`build_wheel`,
`build_sdist`) against a real project layout, so they invoke Conan in the
process:

```bash
pytest tests/test_integration.py -v
```

Full suite:

```bash
pytest tests/ -v
```

## Testing against an example

To try a change end-to-end against one of the bundled examples:

```bash
pip install -e .   # from repo root
pip wheel examples/basic --no-build-isolation -w /tmp/dist/ -vv
```

## Submitting a PR

Contributions are welcome — thank you for taking the time!

A few things that help us review quickly:

- **One concern per PR** keeps review focused and makes it easier to
  bisect if something breaks later.
- **Add or update tests** for the changed behaviour.
- **For larger changes or new features**, open an issue first so we can
  discuss the approach before you invest the time. We'd rather help you
  land it cleanly than ask for a big rewrite at review time.

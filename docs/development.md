# Development

## Editable install

```bash
pip install -e .   # from repo root
cd examples/basic
pip wheel . --no-build-isolation -w dist/
```

## Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Documentation

```bash
pip install -e ".[docs]"
mkdocs serve
```

The site is built from `main` on every push. Changes that don't depend on a
specific release can target `main` directly. For documentation tied to an
upcoming release, open the PR against a `docs/<version>` branch, it will be
merged into `main` after the release ships to keep the site in sync with what
users can install.

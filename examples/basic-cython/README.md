# Basic Cython Example - fmt-cython

Example of a Cython extension with a typed computation loop and a C++ dependency
(`fmt`) managed by Conan.

## Build and Install

```bash
pip install -e .  # from repo root
pip install "cython>=3.0"  # required since pip wheel uses --no-build-isolation

cd examples/basic-cython
pip wheel . --no-build-isolation -w dist/ -vvv
pip install dist/myformatter-*.whl
```

### Test

```bash
python -c "import myformatter; print(myformatter.sum_of_squares([1.0, 2.0, 3.0, 4.0, 5.0]))"
# sum_of_squares(5 values) = 55.0000
```

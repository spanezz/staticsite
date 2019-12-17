# Developer documentation

## Running tests

staticsite uses pretty standard unittest-based tests. You can run them normally
with `nose2-3` or `./setup.py test`.

## Test coverage

```
nose2-3 -C --coverage-report=html
sensible-browser htmlcov/index.html
```


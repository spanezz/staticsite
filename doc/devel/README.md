# Developer documentation

## Running tests

staticsite uses pretty standard unittest-based tests. You can run them normally
with `nose2-3` or `./setup.py test`.

## Test coverage

```
nose2-3 -C --coverage-report=html
sensible-browser htmlcov/index.html
```

## Profiling

```
python3 -m cProfile -o profile.out ./ssite build …

ipython3
>>> import pstats
>>> from pstats import SortKey
>>> stats = pstats.Stats("profile.out")
>>> stats.sort_stats(SortKey.CUMULATIVE).print_stats(20)
```

You can use `devel/profile-dump` to get some ready made statistics on profile
data.


Documentation at <https://docs.python.org/3/library/profile.html>

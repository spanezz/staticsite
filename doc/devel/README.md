# Developer documentation

## Architectural documentation

* [Constraints and invariants](constraints.md)

## Playing with the internals

You can run `ssite shell` on an existing site, to get a python shell with the
`site` variable set to the fully built `staticsite.Site` object for the site.

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

You can use `devel/profile-view` to get some ready made statistics on profile
data, and explore the profile results.

You can also use [runsnakerun](http://www.vrplumber.com/programming/runsnakerun/)
(in Debian, you currently need version 2.0.5 (not yet available in buster) to
read python3 profile data).


## Linting

You can run `make check` to run a range of configured lint tools.


## Static type checking

```
make mypy
```


## Codespell

```
codespell --write-changes --skip debian/copyright *.md debian doc example staticsite tests
```


## Release checklist

* Run tests
    * `nose2-3`
    * `make check`
* Build for debian
    * `debian/rules debsrc`
    * `sudo cowbuilder update`
    * `sudo cowbuilder build staticsite_$version.dsc`
    * `debsign staticsite_$version_source.changes`
    * `dput staticsite_$version_source.changes`
* Tag release in git
    * `git tag -s v$version`
    * `git push --tags`


Documentation at <https://docs.python.org/3/library/profile.html>

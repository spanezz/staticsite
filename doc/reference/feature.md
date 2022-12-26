# Site-specific features

Since version 1.0, it is possible to provide site-specific features as python
packages in the theme `features` directory.

At site load time, the `$theme/features` directory gets scanned with
[`pkgutil.iter_modules`](https://docs.python.org/3/library/pkgutil.html#pkgutil.iter_modules),
and all modules found can provide extra features in a `FEATURES` dict at module level.

The `FEATURES` dict maps feature names to subclasses of `staticsite.Feature`.
See `staticsite/feature.py` for details on the base `Feature` class.

You can add anything you want to the modules under `$theme/features`: see for
example [importlib.resources](https://docs.python.org/3/library/importlib.html#module-importlib.resources)
for how to package assets together with a feature.

This mechanism can also add site-specific command line features under the
`ssite site --cmd …` command.

See `example/theme/features/hello.py` for an annotate example feature.

Most of staticsite is now implemented through features, and you can also look
at `staticfile/features/` to take existing features as examples for custom
ones.

You can also replace an existing staticsite feature by providing a new feature
registered with the same name.


## Feature dependencies

Each feature can define a `RUN_BEFORE` or `RUN_AFTER` on other feature names,
to sequence running so that the results of a feature are guaranteed to be
available when another one runs.

For example, the `syndication` analyze pass needs to run after `taxonomy` and
`pages` have built their page lists.

Note that dependencies may not be needed as much as they might seem: they are
useful to sort the execution of feature constructors, `load_dir_meta`,
`load_dir`, and `finalize`, but those are already separate stages. For example,
if `taxonomy` needs to run its `finalize` methods after all pages have been
loaded from disk, a dependency is not needed, since the `load_dir` stage
already happens before the `finalize` stage.

[Back to reference index](README.md)

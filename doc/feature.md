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

See `example/theme/features/hello.py` for an annotate example feature.

Most of staticsite is now implemented through features, and you can also look
at `staticfile/features/` to take existing features as examples for custom
ones.

#!/bin/sh
eatmydata nose2-3 -C --coverage-report html &&
    sensible-browser htmlcov/index.html

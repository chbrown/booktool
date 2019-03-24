# `booktool`

eBook (EPUB and Audiobook) management tool.

[![Latest version on PyPI](https://badge.fury.io/py/booktool.svg)](https://pypi.org/project/booktool/)


#### Install

```sh
pip install -U booktool
```


### Logging

By default, `booktool ...` runs with logging level set to `WARNING`.
`booktool -v ...` sets the level to `INFO`;
`booktool -vv ...` sets it to `DEBUG`.

The following table describes the logging level strategy.

| Level     | Description                                      |
|:----------|:-------------------------------------------------|
| `WARNING` | Anything outside manageable running conditions.  |
| `INFO`    | Mutations (or would be if not in dry-run mode).  |
| `DEBUG`   | Anything else of note.                           |


## License

Copyright 2019 Christopher Brown.
[MIT Licensed](https://chbrown.github.io/licenses/MIT/#2019).

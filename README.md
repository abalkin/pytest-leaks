# pytest-leaks - A pytest plugin to trace resource leaks

[![See Package Info on PyPI](https://badge.fury.io/py/pytest-leaks.svg)](https://badge.fury.io/py/pytest-leaks)
[![See Build Status on Travis CI](https://travis-ci.org/abalkin/pytest-leaks.svg?branch=master)](https://travis-ci.org/abalkin/pytest-leaks)
[![See Build Status on AppVeyor](https://ci.appveyor.com/api/projects/status/github/abalkin/pytest-leaks?branch=master&svg=true)](https://ci.appveyor.com/project/abalkin/pytest-leaks/branch/master)

A pytest plugin to trace resource leaks.

## Usage

    leaks:
      -R LEAKS, --leaks=LEAKS
                            runs each test several times and examines
                            sys.gettotalrefcount() to see if the test appears to
                            be leaking references. The argument should be of the
                            form stab:run where 'stab' is the number of times the
                            test is run to let gettotalrefcount settle down, 'run'
                            is the number of times further it is run. These
                            parameters all have defaults (5 and 4, respectively),
                            and the minimal invocation is '-R :'.

To add a leaks test to your py.test session, add the `-R` option on the
command line:

    $ cd examples; pytest-3 -v -R : test_faucet.py
    ============================= test session starts =============================
    platform darwin -- Python 3.5.2+, pytest-3.0.5.dev0, py-1.4.31, pluggy-0.4.0 --
    cachedir: .cache
    rootdir: .../abalkin/pytest-leaks, inifile:
    plugins: leaks-0.2.0, cov-2.4.0, pyq-1.1
    collected 3 items
    
    test_faucet.py::test_leaky_faucet LEAKED
    test_faucet.py::test_broken_faucet FAILED
    test_faucet.py::test_mended_faucet PASSED
    
    ================================ leaks summary ================================
    test_faucet.py::test_leaky_faucet: Leaks([('refs', [2, 2, 2, 2])])
    ================================== FAILURES ===================================
    _____________________________ test_broken_faucet ______________________________
    
        def test_broken_faucet():
    >       assert 0
    E       assert 0
    
    test_faucet.py:6: AssertionError
    ================ 1 failed, 1 passed, 1 leaked in 0.46 seconds =================

The test file used above contains the following code:

    $ cat test_faucet.py
    drops = []
    def test_leaky_faucet():
        drops.append({})
    
    def test_broken_faucet():
        assert 0
    
    def test_mended_faucet():
        assert 1

Note that pytest-leaks run tests several times: if you see test failures
that are present only when using pytest-leaks, check that the test does
not modify any global state in a way that prevents it from running a
second time.

## Features

- Detects memory leaks by running py.test tests repeatedly and
  comparing total reference counts between the runs.

## Requirements

- py.test version \>= 3;
- A debug build of Python (2.7 or \>=3.5).

On Linux, Python debug builds can be found in packages `pythonX.Y-dbg`
(Debian and derivatives) and `python3-debug` (Fedora and derivatives).

## Installation

You can install "pytest-leaks" via [pip](https://pypi.python.org/pypi/pip/) from
[PyPI](https://pypi.python.org/pypi):

    $ pip install pytest-leaks

## Contributing

Contributions are very welcome. Tests can be run with
[tox](https://tox.readthedocs.io/en/latest/), please ensure the coverage
at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [MIT](http://opensource.org/licenses/MIT) and
[PSF](https://docs.python.org/3/license.html) licenses, "pytest-leaks"
is free and open source software.

## Issues

If you encounter any problems, please [file an issue](https://github.com/abalkin/pytest-leaks/issues)
along with a detailed description.

## Acknowledgements

This [Pytest](https://github.com/pytest-dev/pytest) plugin was initially
generated with [Cookiecutter](https://github.com/audreyr/cookiecutter)
along with [@hackebrot](https://github.com/hackebrot)'s
[Cookiecutter-pytest-plugin](https://github.com/pytest-dev/cookiecutter-pytest-plugin)
template.

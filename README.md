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
    =========================== test session starts ===========================
    platform linux -- Python 3.7.4, pytest-5.0.1, py-1.8.0, pluggy-0.12.0 --
    cachedir: .pytest_cache
    rootdir: ..
    plugins: leaks-0.3.1
    collected 3 items

    test_faucet.py::test_leaky_faucet LEAKED                            [ 25%]
    test_faucet.py::test_broken_faucet FAILED                           [ 50%]
    test_faucet.py::test_mended_faucet PASSED                           [ 75%]
    test_faucet.py::test_skip_marker_example LEAKED                     [100%]

    ================================ FAILURES =================================
    ___________________________ test_broken_faucet ____________________________

        def test_broken_faucet():
    >       assert 0
    E       assert 0

    examples/test_faucet.py:8: AssertionError
    ============================== leaks summary ==============================
    examples/test_faucet.py::test_leaky_faucet: leaked references: [2, 2, 2, 2], memory blocks: [2, 2, 2, 2]
    examples/test_faucet.py::test_skip_marker_example: leaked (not checked): 'not testing'
    ================== 1 failed, 1 passed, 2 leaked in 0.50s ==================

The test file used above contains the following code:

    $ cat test_faucet.py
    drops = []
    def test_leaky_faucet():
        drops.append({})
    
    def test_broken_faucet():
        assert 0
    
    def test_mended_faucet():
        assert 1

    @pytest.mark.no_leak_check(fail=True, reason="not testing")
    def test_skip_marker_example():
        pass

Note that pytest-leaks runs tests several times: if you see test failures
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

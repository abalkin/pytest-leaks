pytest-leaks - A pytest plugin to trace resource leaks
======================================================

.. image:: https://badge.fury.io/py/pytest-leaks.svg
    :target: https://badge.fury.io/py/pytest-leaks
    :alt: See Package Info on PyPI

.. image:: https://travis-ci.org/abalkin/pytest-leaks.svg?branch=master
    :target: https://travis-ci.org/abalkin/pytest-leaks
    :alt: See Build Status on Travis CI

.. image:: https://ci.appveyor.com/api/projects/status/github/abalkin/pytest-leaks?branch=master&svg=true
    :target: https://ci.appveyor.com/project/abalkin/pytest-leaks/branch/master
    :alt: See Build Status on AppVeyor

A pytest plugin to trace resource leaks.

Usage
-----

To add a leaks test to your py.test session, add the ``-R`` option on the command line::

    $ py.test -v -R : test_fauset.py
    ============================= test session starts =============================
    platform darwin -- Python 3.5.2+, pytest-3.0.5.dev0, py-1.4.31, pluggy-0.4.0 --
    cachedir: .cache
    rootdir: .../abalkin/pytest-leaks, inifile:
    plugins: leaks-0.2.0, cov-2.4.0, pyq-1.1
    collected 3 items

    test_fauset.py::test_leaky_fauset LEAKED
    test_fauset.py::test_broken_fauset FAILED
    test_fauset.py::test_mended_fauset PASSED

    ================================ leaks summary ================================
    test_fauset.py::test_leaky_fauset: Leaks([('refs', [2, 2, 2, 2])])
    ================================== FAILURES ===================================
    _____________________________ test_broken_fauset ______________________________

        def test_broken_fauset():
    >       assert 0
    E       assert 0

    test_fauset.py:6: AssertionError
    ================ 1 failed, 1 passed, 1 leaked in 0.46 seconds =================

The test file used above contains the following code::

    $ cat test_fauset.py
    drops = []
    def test_leaky_fauset():
        drops.append({})

    def test_broken_fauset():
        assert 0

    def test_mended_fauset():
        assert 1

Features
--------

* Detects memory leaks by running py.test tests repeatedly and comparing total reference
  counts between the runs.


Requirements
------------

* py.test version >= TBD;
* A debug build of Python 3.5.


Installation
------------

You can install "pytest-leaks" via `pip`_ from `PyPI`_::

    $ pip install pytest-leaks


Contributing
------------
Contributions are very welcome. Tests can be run with `tox`_, please ensure
the coverage at least stays the same before you submit a pull request.

License
-------

Distributed under the terms of the `MIT`_ license, "pytest-leaks" is free and open source software.


Issues
------

If you encounter any problems, please `file an issue`_ along with a detailed description.

Acknowledgements
----------------

This `Pytest`_ plugin was initially generated with `Cookiecutter`_ along with `@hackebrot`_'s
`Cookiecutter-pytest-plugin`_ template.

.. _`Cookiecutter`: https://github.com/audreyr/cookiecutter
.. _`@hackebrot`: https://github.com/hackebrot
.. _`MIT`: http://opensource.org/licenses/MIT
.. _`cookiecutter-pytest-plugin`: https://github.com/pytest-dev/cookiecutter-pytest-plugin
.. _`file an issue`: https://github.com/abalkin/pytest-leaks/issues
.. _`pytest`: https://github.com/pytest-dev/pytest
.. _`tox`: https://tox.readthedocs.io/en/latest/
.. _`pip`: https://pypi.python.org/pypi/pip/
.. _`PyPI`: https://pypi.python.org/pypi

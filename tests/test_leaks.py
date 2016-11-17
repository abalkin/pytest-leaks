# -*- coding: utf-8 -*-
import sys

import pytest

_py3 = sys.version_info > (3, 0)

with_pydebug = pytest.mark.skipif(not hasattr(sys, 'gettotalrefcount'),
                                  reason='--with-pydebug build is required')


@with_pydebug
def test_config_options_fixture(testdir):
    """Make sure that pytest accepts our fixture."""

    # create a temporary pytest test module
    testdir.makepyfile("""
        def test_sth(pytestconfig):
            assert pytestconfig.option.leaks == ":"
    """)

    # run pytest with the following cmd args in a subprocess
    # for some reason an in-process run reports leaks
    result = testdir.runpytest_subprocess(
        '-R', ':',
        '-v'
    )

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_sth PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_help_message(testdir):
    result = testdir.runpytest(
        '--help',
    )
    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        'leaks:',
        '*-R LEAKS, --leaks=LEAKS',
    ])


def test_leaks_ini_setting(testdir):
    testdir.makeini("""
        [pytest]
        leaks_stab = 2
        leaks_run = 1
    """)

    testdir.makepyfile("""
        def test_hello_world(pytestconfig):
            getini = pytestconfig.getini
            assert getini('leaks_stab') == '2'
            assert getini('leaks_run') == '1'
    """)

    result = testdir.runpytest('-v')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_hello_world PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0

@pytest.mark.parametrize('run,stab', [
    (2, 2),
    (3, 1),
])
def test_leaks_option_parsing(testdir, run, stab):
    testdir.makepyfile("""
        def test_leaks(leaks_checker):
            assert leaks_checker.stab == %d
            assert leaks_checker.run == %d
    """ % (run, stab))
    result = testdir.runpytest('-R', '%d:%d' % (run, stab))
    assert result.ret == 0

@with_pydebug
def test_leaks_checker(testdir):
    # create a temporary pytest test module
    testdir.makepyfile(test_leaks_code)

    # run pytest with the following cmd args
    result = testdir.runpytest(
        '-R', ':',
        '-v'
    )

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_refleaks LEAKED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


leaking = None
test_leaks_code = """
garbage = []
def leaking():
    garbage.append(None)
def test_refleaks():
    leaking()
"""

exec(test_leaks_code)


def test_hunt_leaks(leaks_checker):
    # When py.test is invoked without -R, leaks_checker is None.
    if leaks_checker is None:
        return
    leaks = leaks_checker.hunt_leaks(lambda: None)
    assert not leaks
    leaks = leaks_checker.hunt_leaks(leaking)
    assert leaks
    assert leaks['refs'] == [1]

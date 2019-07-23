# -*- coding: utf-8 -*-
import sys
import re
import textwrap
import subprocess

import pytest

if not hasattr(sys, 'gettotalrefcount'):
    pytest.fail('python debug build compiled with --with-pydebug is required')


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
        '*::test_sth PASSED*',
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
        '*::test_hello_world PASSED*',
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
        '*::test_refleaks LEAKED*',
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


def test_doctest(testdir):
    test_code = """
    items = []

    class SomeClass(object):
        '''
        >>> items.append(SomeClass())
        '''
    """

    testdir.makepyfile(test_code)

    # run pytest with the following cmd args
    result = testdir.runpytest(
        '-R', ':',
        '--doctest-modules',
        '-v'
    )

    result.stdout.fnmatch_lines([
        '*::test_doctest.SomeClass LEAKED*',
    ])

    assert result.ret == 0


def test_doctest_failure(testdir):
    test_code = """
    def foo():
        '''
        >>> False
        True
        '''
    """

    testdir.makepyfile(test_code)

    # run pytest with the following cmd args
    result = testdir.runpytest(
        '-R', ':',
        '--doctest-modules',
        '-v'
    )

    result.stdout.fnmatch_lines([
        '*::test_doctest_failure.foo FAILED*',
        "Expected:",
        "    True",
        "Got:",
        "    False"
    ])

    assert result.ret == 1


def test_doctest_pass(tmpdir):
    # XXX: This test fails if run with the `testdir` fixture,
    # XXX: for some currently unknown reason (gh-12)
    with open(str(tmpdir / "test_doctest.py"), "w") as f:
        f.write(textwrap.dedent("""
        class SomeClass(object):
            '''
            >>> SomeClass()
            <...
            '''
        """))

    output = subprocess.check_output(
        [sys.executable, '-mpytest', '-R', ':',
         '--doctest-modules', '-v', 'test_doctest.py'],
        cwd=str(tmpdir))

    assert re.search(b"test_doctest\\.SomeClass\\s*PASSED", output), output


def test_fixture_setup_teardown(tmpdir):
    # XXX: This test fails if run with the `testdir` fixture,
    # XXX: for some currently unknown reason (gh-12)
    with open(str(tmpdir / "test_sth.py"), "w") as f:
        f.write(textwrap.dedent("""
        import pytest

        global_state = False
        global_count = 0
        prev_global_count = -1

        @pytest.fixture
        def myfixture():
            global global_state, global_count
            global_state = True
            try:
                yield
            finally:
                global_state = False
                global_count += 1

        def test_sth(myfixture):
            global prev_global_count
            assert global_state
            assert global_count > prev_global_count
            prev_global_count = global_count
        """))

    output = subprocess.check_output(
        [sys.executable, '-mpytest', '-R', ':',
         '--doctest-modules', '-v', 'test_sth.py'],
        cwd=str(tmpdir))

    assert re.search(b"::test_sth\\s*PASSED", output), output

# -*- coding: utf-8 -*-


def test_config_options_fixture(testdir):
    """Make sure that pytest accepts our fixture."""

    # create a temporary pytest test module
    testdir.makepyfile("""
        def test_sth(config_options):
            assert config_options.leaks == ":"
    """)

    # run pytest with the following cmd args
    result = testdir.runpytest(
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
        def test_hello_world(getini):
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


def test_leaks_checker(testdir):
    # create a temporary pytest test module
    testdir.makepyfile("""
        def test_leaks(leaks_checker):
            leaks_checker.leak()
    """)

    # run pytest with the following cmd args
    result = testdir.runpytest(
        '-R', ':',
        '-v'
    )

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_leaks PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0

# -*- coding: utf-8 -*-
"""
A pytest plugin to trace resource leaks
"""
from __future__ import print_function
import pytest
from array import array


def pytest_addoption(parser):
    group = parser.getgroup('leaks')
    group.addoption(
        '-R', '--leaks',
        action='store',
        dest='leaks',
        help='''\
runs each test several times and examines sys.gettotalrefcount() to
see if the test appears to be leaking references.  The argument should
be of the form stab:run:fname where 'stab' is the number of times the
test is run to let gettotalrefcount settle down, 'run' is the number
of times further it is run and 'fname' is the name of the file the
reports are written to.  These parameters all have defaults (5, 4 and
"reflog.txt" respectively), and the minimal invocation is '-R :'.
'''
    )

    parser.addini('leaks_stab', 'the number of times the test is run to let'
                  ' gettotalrefcount settle down', default=5)
    parser.addini('leaks_run', 'the number of times the test is run', default=4)


def pytest_configure(config):
    leaks = config.getvalue("leaks")
    if leaks:
        checker = LeakChecker(config)
        config.pluginmanager.register(checker, 'leaks_checker')


@pytest.fixture
def config_options(request):
    return request.config.option


@pytest.fixture
def getini(request):
    return request.config.getini

@pytest.fixture
def leaks_checker(request):
    return request.config.pluginmanager.get_plugin('leaks_checker')

N = 2  # number of resource counters


class LeakChecker(object):
    def __init__(self, config):
        self.stab = 1
        self.run = 1
        self.counts_before = array('l', [0] * N)
        self.counts_after = array('l', [0] * N)
        self.test_resource_count = 0

    def leak(self):
        self.test_resource_count += 1

    def get_counts(self):
        return array('l', [self.test_resource_count, 0])

    @pytest.hookimpl(hookwrapper=True, trylast=True)
    def pytest_runtest_call(self, item):
        for _ in range(self.stab):
            item.runtest()
        self.counts_before[:] = self.get_counts()
        for _ in range(self.run - 1):
            item.runtest()
        yield
        self.counts_after[:] = self.get_counts()

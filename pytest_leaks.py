# -*- coding: utf-8 -*-
"""
A pytest plugin to trace resource leaks
"""
from __future__ import print_function

import sys
from array import array
from collections import OrderedDict as odict

import pytest


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

    parser.addini('leaks_stab',
                  'the number of times the test is run to let '
                  'gettotalrefcount settle down', default=5)
    parser.addini('leaks_run',
                  'the number of times the test is run', default=4)


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


class Leaks(odict):
    pass


class LeakChecker(object):
    def __init__(self, config):
        self.stab = 4
        self.run = 1
        # TODO: det defaults from config.
        self.count_blocks = 0 and hasattr(sys, 'getallocatedblocks')
        self.count_refs = 1 and hasattr(sys, 'gettotalrefcount')
        self.test_resource_count = 0
        self.resources = self.find_resources()
        n = len(self.resources)
        self.counts_before = array('l', [0] * n)
        self.counts_after = array('l', [0] * n)

    def find_resources(self):
        resources = odict()
        resources['test'] = lambda: self.test_resource_count
        if self.count_blocks:
            resources['refs'] = sys.gettotalrefcount
        if self.count_refs:
            resources['blocks'] = sys.getallocatedblocks
        return resources

    def leak(self):
        self.test_resource_count += 1

    def get_counts(self):
        counts = [f() for f in self.resources.values()]
        return array('l', counts)

    def get_leaks(self):
        leaks = Leaks()
        for n, (b, a) in zip(self.resources,
                             zip(self.counts_before,
                                 self.counts_after)):
            if b != a:
                leaks[n] = a - b
        return leaks

    @pytest.hookimpl(hookwrapper=True, trylast=True)
    def pytest_runtest_call(self, item):
        for _ in range(self.stab):
            item.runtest()  # warm-up runs
        self.counts_before[:] = self.get_counts()
        for _ in range(self.run - 1):
            item.runtest()  # extra runs
        outcome = yield  # This runs the test for the last time
        self.counts_after[:] = self.get_counts()
        leaks = self.get_leaks()
        if leaks:
            outcome.force_result(leaks)

    @pytest.hookimpl(hookwrapper=True, trylast=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        # Find Leaks object in result
        if call.when == 'call':
            # NB: call may not have the result attribute
            r = getattr(call, 'result', None)
            if isinstance(r, Leaks):
                outcome.result.leaks = r

    @pytest.hookimpl(hookwrapper=True, trylast=True)
    def pytest_report_teststatus(self, report):
        outcome = yield
        if hasattr(report, 'leaks'):
            # cat, letter, word
            outcome.force_result(('leaked', 'L', 'LEAKED'))

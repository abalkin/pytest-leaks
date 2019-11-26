# -*- coding: utf-8 -*-
"""
A pytest plugin to trace resource leaks
"""
from __future__ import print_function

import sys
import re
import json

from collections import OrderedDict

import pytest


try:
    from _pytest.doctest import DoctestItem
except ImportError:
    DoctestItem = type(None)


if sys.version_info < (3,):
    from . import refleak_27 as refleak
    refleak_ver = '27'
elif sys.version_info < (3, 7):
    from . import refleak_35 as refleak
    refleak_ver = '35'
else:
    from . import refleak_38 as refleak
    refleak_ver = '38'


class Leaks(OrderedDict):
    def __str__(self):
        msg = ", ".join("{!s}: {!r}".format(key, value)
                        for key, value in self.items())
        return "leaked {}".format(msg)


def pytest_addoption(parser):
    group = parser.getgroup('leaks')
    group.addoption(
        '-R', '--leaks',
        action='store',
        dest='leaks',
        help='''\
runs each test several times and examines sys.gettotalrefcount() to
see if the test appears to be leaking references.  The argument should
be of the form stab:run where 'stab' is the number of times the
test is run to let gettotalrefcount settle down, 'run' is the number
of times further it is run.  These parameters all have defaults (5 and 4,
respectively), and the minimal invocation is '-R :'.
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
        if not hasattr(sys, 'gettotalrefcount'):
            raise pytest.UsageError(
                "pytest-leaks: tracking reference leaks requires "
                "running on a debug build of Python")

        checker = LeakChecker(config)
        config.pluginmanager.register(checker, 'leaks_checker')

    config.addinivalue_line(
        "markers",
        "no_leak_check(fail=False, reason=""): don't run pytest-leaks on "
        "this test, optionally failing the leak test without checking with "
        "some reason given.")


@pytest.fixture
def leaks_checker(request):
    return request.config.pluginmanager.get_plugin('leaks_checker')


class LeakChecker(object):
    def __init__(self, config):
        try:
            self.stab = int(config.getini('leaks_stab'))
        except ValueError:
            raise pytest.UsageError("pytest-leaks: invalid value for "
                                    "'leaks_stab' in ini file")

        try:
            self.run = int(config.getini('leaks_run'))
        except ValueError:
            raise pytest.UsageError("pytest-leaks: invalid value for "
                                    "'leaks_run' in ini file")

        m = re.match(r'^(\d*):(\d*)$', str(config.getvalue("leaks")))
        if m:
            if m.group(1):
                self.stab = int(m.group(1))
            if m.group(2):
                self.run = int(m.group(2))
        else:
            raise pytest.UsageError("pytest-leaks: invalid value for "
                                    "-R option")

        # Get access to the builtin "runner" plugin.
        self.runner = config.pluginmanager.get_plugin('runner')

        # Temporary storage for leak data
        self._leaks = {}  # item.nodeid -> result

    def hunt_leaks(self, func):
        return hunt_leaks(func, self.stab, self.run)

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_protocol(self, item, nextitem):
        marker = item.get_closest_marker('no_leak_check')
        if marker:
            # Don't run leak check
            if marker.kwargs.get('fail'):
                reason = marker.kwargs.get('reason', "")
                self.leaks[item.nodeid] = {'(not checked)': reason}
            return

        when = ["setup"]
        hook = item.ihook

        if isinstance(item, DoctestItem):
            # pytest runs doctests with clear_globs=True, so we need
            # to copy it in order to be able to run several times
            doctest_original_globs = dict(item.dtest.globs)
        else:
            doctest_original_globs = None

        def run_test():
            hasrequest = hasattr(item, "_request")
            if hasrequest and not item._request:
                item._initrequest()

            when[0] = "setup"
            hook.pytest_runtest_setup(item=item)
            when[0] = "call"
            hook.pytest_runtest_call(item=item)
            when[0] = "teardown"
            hook.pytest_runtest_teardown(item=item, nextitem=nextitem)

            if hasrequest:
                # Ensure fixtures etc are reset properly
                item._request = False
                item.funcargs = None

            if doctest_original_globs is not None:
                # Restore doctest environment
                item.dtest.globs.update(doctest_original_globs)

            # Clear pytest captured output etc., if any
            item._report_sections = []

        if hasattr(self.runner.CallInfo, 'from_call'):
            # pytest >= 4
            from _pytest.outcomes import Exit
            call = self.runner.CallInfo.from_call(
                lambda: self.hunt_leaks(run_test), 'leakshunt',
                reraise=(KeyboardInterrupt, Exit))
        else:
            # pytest < 4
            call = self.runner.CallInfo(
                lambda: self.hunt_leaks(run_test), 'leakshunt')

        if call.excinfo is not None:
            # Raise errors immediately: it's possible there's some bad
            # interaction with the leak checking code, so we should
            # not hide this failure.
            hook.pytest_runtest_logstart(nodeid=item.nodeid,
                                         location=item.location)
            # doctest requires errors are reported with the correct 'when'
            call.when = when[0]
            report = hook.pytest_runtest_makereport(item=item, call=call)
            hook.pytest_runtest_logreport(report=report)
            hook.pytest_runtest_logfinish(nodeid=item.nodeid,
                                          location=item.location)
            return True  # skip pytest implementation
        else:
            self._leaks[item.nodeid] = call.result

        return  # proceed to pytest implementation

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield

        # Append leak report in 'call' phase
        if call.when != 'call':
            return

        report = outcome.get_result()
        leaks = self._leaks.pop(item.nodeid, None)
        if leaks:
            report.sections.append(('pytest-leaks', json.dumps(leaks)))
            outcome.force_result(report)

    def _leaks_from_report(self, report):
        if report.when != "call":
            return None

        leaks = [data for key, data in report.get_sections('pytest-leaks')
                 if key == 'pytest-leaks']
        if leaks:
            return Leaks(json.loads(leaks[0]))

        return None

    @pytest.hookimpl(hookwrapper=True, trylast=True)
    def pytest_report_teststatus(self, report):
        outcome = yield
        if report.when == 'call' and report.outcome == 'passed':
            if self._leaks_from_report(report):
                # cat, letter, word
                outcome.force_result(('leaked', 'L', 'LEAKED'))

    @pytest.hookimpl
    def pytest_terminal_summary(self, terminalreporter, exitstatus):
        tr = terminalreporter

        if 'pytest_sugar' in type(tr).__module__:
            # pytest-sugar doesn't run pytest_report_teststatus: ensure
            # leak summary gets shown
            leaked = list(tr.getreports('passed'))
        else:
            leaked = list(tr.getreports('leaked'))

        if leaked:
            tr.write_sep("=", 'leaks summary', cyan=True)
            for rep in leaked:
                leaks = self._leaks_from_report(rep)
                if leaks:
                    tr.line("%s: %s" % (rep.nodeid, leaks))


class Namespace(object):
    pass


def hunt_leaks(func, nwarmup, ntracked):
    huntrleaks = (nwarmup, ntracked, "")
    if refleak_ver == '27':
        return refleak.dash_R(None, "", func, huntrleaks, True)
    elif refleak_ver == '35':
        return refleak.dash_R(None, "", func, huntrleaks)
    else:
        ns = Namespace()
        ns.quiet = True
        ns.huntrleaks = huntrleaks
        return refleak.dash_R(ns, "", func)

# -*- coding: utf-8 -*-

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

    parser.addini('leaks_stab', 'the number of times the test is run to let'
                  ' gettotalrefcount settle down', default=5)
    parser.addini('leaks_run', 'the number of times the test is run', default=4)


@pytest.fixture
def config_options(request):
    return request.config.option


@pytest.fixture
def getini(request):
    return request.config.getini

# Modified from cpython-2.7/Lib/test/regrtest.py

import StringIO
import datetime
import getopt
import imp
import json
import math
import os
import platform
import random
import re
import shutil
import sys
import sysconfig
import tempfile
import time
import traceback
import unittest
import warnings

from . import support  # <- pytest-leaks edit
from collections import OrderedDict  # <- pytest-leaks edit


def dash_R(the_module, test, indirect_test, huntrleaks, quiet):
    """Run a test multiple times, looking for reference leaks.

    Returns:
        False if the test didn't leak references; True if we detected refleaks.
    """
    # This code is hackish and inelegant, but it seems to do the job.
    import copy_reg, _abcoll, _pyio

    if not hasattr(sys, 'gettotalrefcount'):
        raise Exception("Tracking reference leaks requires a debug build "
                        "of Python")

    # Avoid false positives due to various caches
    # filling slowly with random data:
    warm_caches()

    # Save current values for dash_R_cleanup() to restore.
    fs = warnings.filters[:]
    ps = copy_reg.dispatch_table.copy()
    pic = sys.path_importer_cache.copy()
    try:
        import zipimport
    except ImportError:
        zdc = None # Run unmodified on platforms without zipimport support
    else:
        zdc = zipimport._zip_directory_cache.copy()
    abcs = {}
    modules = _abcoll, _pyio
    for abc in [getattr(mod, a) for mod in modules for a in mod.__all__]:
        # XXX isinstance(abc, ABCMeta) leads to infinite recursion
        if not hasattr(abc, '_abc_registry'):
            continue
        for obj in abc.__subclasses__() + [abc]:
            abcs[obj] = obj._abc_registry.copy()

    # bpo-31217: Integer pool to get a single integer object for the same
    # value. The pool is used to prevent false alarm when checking for memory
    # block leaks. Fill the pool with values in -1000..1000 which are the most
    # common (reference, memory block, file descriptor) differences.
    int_pool = {value: value for value in range(-1000, 1000)}
    def get_pooled_int(value):
        return int_pool.setdefault(value, value)

    if indirect_test:
        def run_the_test():
            indirect_test()
    else:
        def run_the_test():
            imp.reload(the_module)

    deltas = []
    nwarmup, ntracked, fname = huntrleaks
    fname = os.path.join(support.SAVEDCWD, fname)

    # Pre-allocate to ensure that the loop doesn't allocate anything new
    repcount = nwarmup + ntracked
    rc_deltas = [0] * repcount
    fd_deltas = [0] * repcount
    rep_range = list(range(repcount))

    if not quiet:
        print >> sys.stderr, "beginning", repcount, "repetitions"
        print >> sys.stderr, ("1234567890"*(repcount//10 + 1))[:repcount]

    dash_R_cleanup(fs, ps, pic, zdc, abcs)

    # initialize variables to make pyflakes quiet
    rc_before = fd_before = 0

    for i in rep_range:
        run_the_test()

        if not quiet:
            sys.stderr.write('.')

        dash_R_cleanup(fs, ps, pic, zdc, abcs)

        rc_after = sys.gettotalrefcount()
        fd_after = support.fd_count()
        rc_deltas[i] = get_pooled_int(rc_after - rc_before)
        fd_deltas[i] = get_pooled_int(fd_after - fd_before)
        rc_before = rc_after
        fd_before = fd_after

    if not quiet:
        print >> sys.stderr

    # These checkers return False on success, True on failure
    def check_rc_deltas(deltas):
        # Checker for reference counters and memomry blocks.
        #
        # bpo-30776: Try to ignore false positives:
        #
        #   [3, 0, 0]
        #   [0, 1, 0]
        #   [8, -8, 1]
        #
        # Expected leaks:
        #
        #   [5, 5, 6]
        #   [10, 1, 1]
        return all(delta >= 1 for delta in deltas)

    def check_fd_deltas(deltas):
        return any(deltas)

    failed = False
    leaks = OrderedDict()  # <- pytest-leaks edit
    for deltas, item_name, checker in [
        (rc_deltas, 'references', check_rc_deltas),
        (fd_deltas, 'file descriptors', check_fd_deltas)
    ]:
        deltas = deltas[nwarmup:]
        if checker(deltas):
            # <pytest-leaks edit>
            leaks[item_name] = deltas
            continue
            # </pytest-leaks edit>
            msg = '%s leaked %s %s, sum=%s' % (test, deltas, item_name, sum(deltas))
            print >> sys.stderr, msg
            with open(fname, "a") as refrep:
                print >> refrep, msg
                refrep.flush()
            failed = True
    return leaks  # <- pytest-leaks edit

def dash_R_cleanup(fs, ps, pic, zdc, abcs):
    import gc, copy_reg

    # Restore some original values.
    warnings.filters[:] = fs
    copy_reg.dispatch_table.clear()
    copy_reg.dispatch_table.update(ps)
    sys.path_importer_cache.clear()
    sys.path_importer_cache.update(pic)
    try:
        import zipimport
    except ImportError:
        pass # Run unmodified on platforms without zipimport support
    else:
        zipimport._zip_directory_cache.clear()
        zipimport._zip_directory_cache.update(zdc)

    # clear type cache
    sys._clear_type_cache()

    # Clear ABC registries, restoring previously saved ABC registries.
    for abc, registry in abcs.items():
        abc._abc_registry = registry.copy()
        abc._abc_cache.clear()
        abc._abc_negative_cache.clear()

    clear_caches()

def clear_caches():
    import gc

    # Clear the warnings registry, so they can be displayed again
    for mod in sys.modules.values():
        if hasattr(mod, '__warningregistry__'):
            del mod.__warningregistry__

    # Clear assorted module caches.
    # Don't worry about resetting the cache if the module is not loaded
    try:
        distutils_dir_util = sys.modules['distutils.dir_util']
    except KeyError:
        pass
    else:
        distutils_dir_util._path_created.clear()

    re.purge()

    try:
        _strptime = sys.modules['_strptime']
    except KeyError:
        pass
    else:
        _strptime._regex_cache.clear()

    try:
        urlparse = sys.modules['urlparse']
    except KeyError:
        pass
    else:
        urlparse.clear_cache()

    try:
        urllib = sys.modules['urllib']
    except KeyError:
        pass
    else:
        urllib.urlcleanup()

    try:
        urllib2 = sys.modules['urllib2']
    except KeyError:
        pass
    else:
        urllib2.install_opener(None)

    try:
        dircache = sys.modules['dircache']
    except KeyError:
        pass
    else:
        dircache.reset()

    try:
        linecache = sys.modules['linecache']
    except KeyError:
        pass
    else:
        linecache.clearcache()

    try:
        mimetypes = sys.modules['mimetypes']
    except KeyError:
        pass
    else:
        mimetypes._default_mime_types()

    try:
        filecmp = sys.modules['filecmp']
    except KeyError:
        pass
    else:
        filecmp._cache.clear()

    try:
        struct = sys.modules['struct']
    except KeyError:
        pass
    else:
        struct._clearcache()

    try:
        doctest = sys.modules['doctest']
    except KeyError:
        pass
    else:
        doctest.master = None

    try:
        ctypes = sys.modules['ctypes']
    except KeyError:
        pass
    else:
        ctypes._reset_cache()

    # Collect cyclic trash.
    support.gc_collect()

def warm_caches():
    """Create explicitly internal singletons which are created on demand
    to prevent false positive when hunting reference leaks."""
    # char cache
    for i in range(256):
        chr(i)
    # unicode cache
    for i in range(256):
        unichr(i)
    # int cache
    list(range(-5, 257))

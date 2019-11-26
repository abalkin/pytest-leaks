import pytest

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

import uuid

from transcriber.service import InstanceSignals


def test_singleton_and_stop_signal():
    name = f"Local\\yat-test-{uuid.uuid4().hex}"
    owner = InstanceSignals.acquire(name)
    assert owner is not None
    try:
        assert InstanceSignals.acquire(name) is None
        assert not owner.stop_requested()
        assert InstanceSignals.request_stop(name)
        assert owner.stop_requested()
    finally:
        owner.close()
    assert not InstanceSignals.request_stop(name)
    replacement = InstanceSignals.acquire(name)
    assert replacement is not None
    replacement.close()


def test_stop_without_instance_is_safe():
    name = f"Local\\yat-test-{uuid.uuid4().hex}"
    assert not InstanceSignals.request_stop(name)

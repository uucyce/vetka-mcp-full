"""
Tests for cascade skip mechanism (conftest.py).

Verifies that @pytest.mark.depends_on("gate") + @cascade_gate("gate")
correctly skip downstream tests when a gate fixture fails.
"""
import pytest

from tests.conftest import _cascade_failures, cascade_gate


# ---------------------------------------------------------------------------
# Unit tests for cascade_gate decorator
# ---------------------------------------------------------------------------

class TestCascadeGateDecorator:
    """Unit tests for the cascade_gate decorator."""

    def setup_method(self):
        # Save and restore live_test_gate across unit tests
        self._saved = _cascade_failures.get("live_test_gate")
        _cascade_failures.clear()

    def teardown_method(self):
        _cascade_failures.clear()
        if self._saved is not None:
            _cascade_failures["live_test_gate"] = self._saved

    def test_passing_function_no_cascade(self):
        @cascade_gate("my_gate")
        def good_fixture():
            return 42

        result = good_fixture()
        assert result == 42
        assert "my_gate" not in _cascade_failures

    def test_failing_function_records_cascade(self):
        @cascade_gate("broken_gate")
        def bad_fixture():
            raise ConnectionError("server down")

        with pytest.raises(ConnectionError):
            bad_fixture()

        assert "broken_gate" in _cascade_failures
        assert "ConnectionError" in _cascade_failures["broken_gate"]
        assert "server down" in _cascade_failures["broken_gate"]

    def test_passing_generator_no_cascade(self):
        @cascade_gate("gen_gate")
        def gen_fixture():
            yield "hello"

        gen = gen_fixture()
        value = next(gen)
        assert value == "hello"
        assert "gen_gate" not in _cascade_failures

    def test_failing_generator_records_cascade(self):
        @cascade_gate("gen_broken")
        def gen_fixture():
            raise RuntimeError("setup failed")
            yield  # noqa: unreachable

        with pytest.raises(RuntimeError):
            gen = gen_fixture()
            next(gen)

        assert "gen_broken" in _cascade_failures

    def test_multiple_gates_independent(self):
        @cascade_gate("gate_a")
        def fixture_a():
            raise ValueError("a broke")

        @cascade_gate("gate_b")
        def fixture_b():
            return "ok"

        with pytest.raises(ValueError):
            fixture_a()
        fixture_b()

        assert "gate_a" in _cascade_failures
        assert "gate_b" not in _cascade_failures


# ---------------------------------------------------------------------------
# Integration tests using pytest's pytester (if available) or manual marker check
# ---------------------------------------------------------------------------

class TestCascadeSkipMarker:
    """Test the marker registration and cascade_failures dict interaction."""

    def setup_method(self):
        self._saved = dict(_cascade_failures)
        _cascade_failures.clear()

    def teardown_method(self):
        _cascade_failures.clear()
        _cascade_failures.update(self._saved)

    def test_depends_on_marker_is_registered(self):
        """Marker should be registered without warnings."""
        marker = pytest.mark.depends_on("bootstrap")
        assert marker.args == ("bootstrap",)

    def test_cascade_failures_dict_is_module_level(self):
        """Ensure the registry is shared across imports."""
        from tests.conftest import _cascade_failures as cf2
        _cascade_failures["test_shared"] = "error"
        assert cf2["test_shared"] == "error"

    def test_skip_message_format(self):
        """Verify the skip message contains gate name and error."""
        _cascade_failures["bootstrap"] = "ConnectionError: server unreachable"

        # Simulate what pytest_runtest_setup does
        gate = "bootstrap"
        msg = f"cascade skip: gate '{gate}' failed — {_cascade_failures[gate]}"
        assert "cascade skip" in msg
        assert "bootstrap" in msg
        assert "ConnectionError" in msg


# ---------------------------------------------------------------------------
# Live cascade skip test — uses actual pytest mechanics
# ---------------------------------------------------------------------------

# Pre-populate a known failure to test the skip mechanism.
# pytest_runtest_setup runs before setup_method, so we set it here.
_cascade_failures["live_test_gate"] = "RuntimeError: simulated bootstrap failure"


class TestLiveCascadeSkip:
    """Tests that depend on a known-failing gate get skipped."""

    @pytest.mark.depends_on("live_test_gate")
    def test_skipped_by_cascade(self):
        """This test should be SKIPPED because live_test_gate failed."""
        pytest.fail("This should never execute — cascade skip should have caught it")

    @pytest.mark.depends_on("live_test_gate")
    def test_also_skipped(self):
        """Second dependent — also skipped."""
        pytest.fail("Should not reach here")

    def test_not_dependent_runs_fine(self):
        """No depends_on marker — should run normally."""
        assert True


class TestMultiGateDependency:
    """Test depending on multiple gates."""

    @pytest.mark.depends_on("nonexistent_gate_x", "nonexistent_gate_y")
    def test_runs_when_no_gates_failed(self):
        """Neither gate failed — test runs."""
        assert True

    @pytest.mark.depends_on("live_test_gate")
    def test_skipped_when_gate_failed(self):
        """live_test_gate was pre-populated as failed — test should skip."""
        pytest.fail("Should have been skipped")

    @pytest.mark.depends_on("nonexistent_gate_z", "live_test_gate")
    def test_skipped_when_any_gate_failed(self):
        """One of two gates failed — test should skip."""
        pytest.fail("Should have been skipped")

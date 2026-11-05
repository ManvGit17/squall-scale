from scaling import Action, FleetState, ScalingConfig, decide

CFG = ScalingConfig(
    min_backends=2, max_backends=6,
    high_watermark_ms=150.0, low_watermark_ms=70.0,
    up_cooldown_s=10.0, down_cooldown_s=25.0,
)


def test_grows_to_minimum_regardless_of_signal():
    state = FleetState(backends=1, signal_ms=None,
                       seconds_since_up=0, seconds_since_down=0)
    assert decide(state, CFG) is Action.UP


def test_shrinks_above_maximum():
    state = FleetState(backends=7, signal_ms=10.0,
                       seconds_since_up=999, seconds_since_down=999)
    assert decide(state, CFG) is Action.DOWN


def test_holds_without_a_signal():
    state = FleetState(backends=3, signal_ms=None,
                       seconds_since_up=999, seconds_since_down=999)
    assert decide(state, CFG) is Action.NONE


def test_scales_up_when_hot_and_cooled_down():
    state = FleetState(backends=2, signal_ms=200.0,
                       seconds_since_up=11, seconds_since_down=0)
    assert decide(state, CFG) is Action.UP


def test_does_not_scale_up_during_cooldown():
    state = FleetState(backends=2, signal_ms=200.0,
                       seconds_since_up=5, seconds_since_down=0)
    assert decide(state, CFG) is Action.NONE


def test_does_not_scale_up_at_maximum():
    state = FleetState(backends=6, signal_ms=500.0,
                       seconds_since_up=999, seconds_since_down=999)
    assert decide(state, CFG) is Action.NONE


def test_scales_down_when_cold_and_cooled_down():
    state = FleetState(backends=4, signal_ms=50.0,
                       seconds_since_up=0, seconds_since_down=26)
    assert decide(state, CFG) is Action.DOWN


def test_does_not_scale_down_during_cooldown():
    state = FleetState(backends=4, signal_ms=50.0,
                       seconds_since_up=0, seconds_since_down=10)
    assert decide(state, CFG) is Action.NONE


def test_does_not_scale_down_at_minimum():
    state = FleetState(backends=2, signal_ms=10.0,
                       seconds_since_up=999, seconds_since_down=999)
    assert decide(state, CFG) is Action.NONE


def test_holds_between_watermarks():
    state = FleetState(backends=4, signal_ms=100.0,
                       seconds_since_up=999, seconds_since_down=999)
    assert decide(state, CFG) is Action.NONE

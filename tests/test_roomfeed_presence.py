from multitracker.roomfeed.presence import NON_GAME_TAGS, RECENT_SECONDS, Presence


def test_constants():
    assert NON_GAME_TAGS == frozenset({"Tracker", "TextOnly", "HintGame"})
    assert RECENT_SECONDS == 600


def test_default_is_unknown():
    p = Presence(set())
    assert p.state(1, 0.0) == "unknown"
    assert p.last_check(1) is None


def test_session_start_tracked_is_unknown():
    p = Presence({1, 2})
    p.session_start({1: 20, 2: 0})
    assert p.state(1, 0.0) == "unknown"
    assert p.state(2, 0.0) == "unknown"


def test_session_start_untracked_mapping():
    p = Presence(set())
    p.session_start({1: 10, 2: 20, 3: 5, 4: 0, 5: 30})
    assert p.state(1, 0.0) == "playing"
    assert p.state(2, 0.0) == "playing"
    assert p.state(3, 0.0) == "connected"
    assert p.state(4, 0.0) == "offline"
    assert p.state(5, 0.0) == "unknown"
    assert p.state(6, 0.0) == "unknown"  # absent


def test_session_start_remembers_statuses_for_part():
    p = Presence(set())
    p.session_start({1: 5, 2: 0})
    p.join(1, [])
    p.part(1)
    assert p.state(1, 0.0) == "connected"
    p.join(2, [])
    p.part(2)
    assert p.state(2, 0.0) == "offline"


def test_status_ignored_for_tracked_slot():
    p = Presence({1})
    p.status(1, 20)
    assert p.state(1, 0.0) == "unknown"
    p.part(1)
    p.status(1, 5)
    assert p.state(1, 0.0) == "offline"


def test_status_zero_is_offline():
    p = Presence(set())
    p.status(1, 20)
    p.status(1, 0)
    assert p.state(1, 0.0) == "offline"


def test_status_ready_and_playing_are_playing():
    p = Presence(set())
    p.status(1, 10)
    p.status(2, 20)
    assert p.state(1, 0.0) == "playing"
    assert p.state(2, 0.0) == "playing"


def test_status_connected_keeps_playing_else_connected():
    p = Presence(set())
    p.status(1, 20)
    p.status(1, 5)
    assert p.state(1, 0.0) == "playing"
    p.status(2, 5)
    assert p.state(2, 0.0) == "connected"


def test_status_goal_leaves_state_unchanged():
    p = Presence(set())
    p.status(1, 20)
    p.status(1, 30)
    assert p.state(1, 0.0) == "playing"
    p.status(2, 30)
    assert p.state(2, 0.0) == "unknown"


def test_join_game_client_is_playing():
    p = Presence(set())
    p.join(1, [])
    p.join(2, ["AP", "DeathLink"])
    assert p.state(1, 0.0) == "playing"
    assert p.state(2, 0.0) == "playing"


def test_join_game_client_is_playing_even_if_tracked():
    p = Presence({1})
    p.join(1, ["AP"])
    assert p.state(1, 0.0) == "playing"


def test_join_tool_client_untracked_offline_or_unknown_is_connected():
    p = Presence(set())
    p.join(1, ["Tracker"])
    assert p.state(1, 0.0) == "connected"
    p.status(2, 0)
    p.join(2, ["TextOnly"])
    assert p.state(2, 0.0) == "connected"
    p.join(3, ["HintGame", "AP"])
    assert p.state(3, 0.0) == "connected"


def test_join_tool_client_does_not_downgrade_playing():
    p = Presence(set())
    p.status(1, 20)
    p.join(1, ["Tracker"])
    assert p.state(1, 0.0) == "playing"
    p.status(2, 5)
    p.join(2, ["Tracker"])
    assert p.state(2, 0.0) == "connected"


def test_join_tool_client_tracked_is_ignored():
    p = Presence({1})
    p.join(1, ["Tracker"])
    assert p.state(1, 0.0) == "unknown"


def test_part_tracked_is_offline():
    p = Presence({1})
    p.join(1, [])
    p.part(1)
    assert p.state(1, 0.0) == "offline"


def test_part_untracked_depends_on_last_status():
    p = Presence(set())
    p.status(1, 20)
    p.part(1)
    assert p.state(1, 0.0) == "connected"
    p.status(2, 30)
    p.part(2)
    assert p.state(2, 0.0) == "offline"
    p.status(3, 0)
    p.part(3)
    assert p.state(3, 0.0) == "offline"
    p.part(4)  # never seen
    assert p.state(4, 0.0) == "offline"


def test_check_overrides_to_playing_while_recent():
    p = Presence(set())
    p.status(1, 0)
    p.check(1, 1000.0)
    assert p.last_check(1) == 1000.0
    assert p.state(1, 1000.0 + RECENT_SECONDS) == "playing"
    assert p.state(1, 1000.0 + RECENT_SECONDS + 1) == "offline"


def test_check_stores_latest_time():
    p = Presence(set())
    p.check(1, 5.0)
    p.check(1, 9.0)
    assert p.last_check(1) == 9.0


def test_check_keeps_latest_when_called_out_of_order():
    p = Presence(set())
    p.check(1, 9.0)
    p.check(1, 5.0)
    assert p.last_check(1) == 9.0

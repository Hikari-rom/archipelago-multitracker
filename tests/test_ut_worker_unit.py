"""ut_worker helpers that need no Archipelago world."""
from multitracker.logic.ut_worker import adapter_refusal

TRACEBACK = """Traceback (most recent call last):
  File "worlds/tww/randomizers/Charts.py", line 88, in setup_progress_sunken_treasure_locations
multitracker.logic.ut_worker.LogicUnavailable: The Wind Waker : cartes mélangées (randomize_charts)

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
Exception: Exception in <bound method TWWWorld.create_regions> for player 1, named P1.
"""


def test_adapter_refusal_is_found_in_the_universal_tracker_traceback():
    assert adapter_refusal(TRACEBACK) == "The Wind Waker : cartes mélangées (randomize_charts)"


def test_other_generation_errors_are_not_refusals():
    assert adapter_refusal("Traceback (most recent call last):\nKeyError: 'x'\n") is None
    assert adapter_refusal("") is None

import os


def get_test_hook_environment():
    """
    Return the environment variables necessary to run the test engine.

    :returns: Dictionary of environment variables necessary to run
        the test engine.
    """
    return {"SHOTGUN_TEST_HOOK": os.path.abspath(os.path.dirname(__file__))}

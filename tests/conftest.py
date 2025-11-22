import os
import pytest
import random
import localis
from localis.registries import Registry


def pytest_addoption(parser: pytest.Parser):
    parser.addoption(
        "--seed",
        default=None,
        help="Set a specific random seed for debugging tests.",
    )

    parser.addoption(
        "-F",
        "--fast",
        action="store_true",
        default=False,
        help="Skips slow tests (integration, analysis, etc.)",
    )


def pytest_configure(config: pytest.Config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (skipped with --fast)"
    )


def pytest_collection_modifyitems(config: pytest.Config, items):
    if not config.getoption("--fast"):
        return

    skip_slow = pytest.mark.skip(reason="use --fast to skip slow tests.")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


_SESSION_SEED = None


@pytest.fixture(scope="session", autouse=True)
def seed(request: pytest.FixtureRequest):
    global _SESSION_SEED
    seed = request.config.getoption("--seed")
    if seed is not None:
        seed = int(seed)
    else:
        seed = random.randrange(1, 10000001)
    _SESSION_SEED = seed

    yield seed


@pytest.fixture(scope="session")
def select_random(seed):
    def callback(reg: Registry, seed_offset: int = 0):
        rng = random.Random(seed + seed_offset)
        id = rng.choice(range(1, reg.count))
        return reg.get(id=id)

    return callback


@pytest.fixture(scope="session")
def country(select_random) -> localis.Country:
    """Selects a single country to be tested with the seed that generated it."""
    return select_random(localis.countries)


@pytest.fixture(scope="session")
def sub(select_random) -> localis.Subdivision:
    """Selects a single subdivision to be tested with the seed that generated it."""
    return select_random(localis.subdivisions)


@pytest.fixture(scope="session")
def city(select_random) -> localis.City:
    """Selects a single city to be tested with the seed that generated it."""
    return select_random(localis.cities)


@pytest.fixture(scope="session", autouse=True)
def ensure_cities_loaded(request: pytest.FixtureRequest):
    """Ensure cities are loaded before running city-dependent tests

    This runs once per session and loads cities if needed."""

    from localis import cities

    if not cities._loaded:
        print("\n⚠️  Cities not loaded. Attempting to load...")
    cities.load(confirmed=True)


def pytest_itemcollected(item: pytest.Item):
    """Display class and function docstrings, fallback to names, and include filename."""
    # File name
    filename = os.path.basename(item.fspath)
    file_title = filename.replace("test_", "").replace(".py", "").title()

    # Class docstring
    cls_doc = getattr(getattr(item.parent, "obj", None), "__doc__", None)
    cls_title = (
        cls_doc.strip().split("\n")[0]
        if cls_doc
        else getattr(getattr(item.parent, "obj", None), "__name__", "")
    )

    # Function docstring
    try:
        func_doc: str = getattr(item.obj, "__doc__", None)
        func_title: str = item.obj.__name__ + " > " + func_doc.strip().split("\n")[0]
    except AttributeError as e:
        e.add_note("Did you forget to include a docstring?")
        raise e

    parts = [file_title]
    if cls_title:
        parts.append(cls_title)
    if func_title:
        parts.append(func_title)

    # detect parametrized id value and append
    if "[" in item.name:
        parts.append("[" + item.name.split("[")[1])

    item._nodeid = " ".join(parts)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook wrapper to attach extra information (like the seed) to the report object.
    """
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        global _SESSION_SEED
        seed_message = f" (Reproduce with: pytest --seed={_SESSION_SEED})"
        report.nodeid += seed_message

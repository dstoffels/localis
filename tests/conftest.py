import os
import pytest

BLUE = "\033[94m"
BROWN = "\033[33m"
RESET = "\033[0m"


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
    func_doc = getattr(item.obj, "__doc__", None)
    func_title: str = item.obj.__name__ + "::" + func_doc.strip().split("\n")[0]

    # Clean function title
    # func_title = func_title.replace("test_", "")

    parts = [file_title]
    if cls_title:
        parts.append(cls_title)
    if func_title:
        parts.append(func_title)

    # detect parametrized id value and append
    if "[" in item.name:
        parts.append("[" + item.name.split("[")[1])

    item._nodeid = " ".join(parts)


def pytest_addoption(parser):
    parser.addoption(
        "--benchmark",
        action="store_true",
        default=False,
        help="Run tests marked with benchmark",
    )

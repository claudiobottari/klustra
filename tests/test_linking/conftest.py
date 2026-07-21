from __future__ import annotations

import pytest


@pytest.fixture
def valid_ids() -> set[str]:
    return {"prod.cable.p-laser-320kv", "prod.cable.xlpe-400kv", "mat.copper", "proc.extrusion"}


@pytest.fixture
def aliases() -> dict[str, str]:
    return {
        "P-Laser 320kV": "prod.cable.p-laser-320kv",
        "copper": "mat.copper",
    }


@pytest.fixture
def body_with_links() -> str:
    return (
        "This cable uses [[mat.copper]] conductors.\n"
        "See also [[prod.cable.xlpe-400kv]] for comparison.\n"
        "The [[proc.extrusion]] process is critical.\n"
    )


@pytest.fixture
def body_with_broken_links() -> str:
    return (
        "Refer to [[mat.copper]] and [[nonexistent.entity]] for details.\n"
        "Also see [[another.missing]].\n"
    )


@pytest.fixture
def multi_page_fixture() -> list[tuple[str, str]]:
    return [
        ("prod.cable.p-laser-320kv", "Uses [[mat.copper]] and [[proc.extrusion]]."),
        ("prod.cable.xlpe-400kv", "Similar to [[prod.cable.p-laser-320kv]]."),
        ("mat.copper", "Used in [[prod.cable.p-laser-320kv]] and [[prod.cable.xlpe-400kv]]."),
        ("proc.extrusion", "Applied to [[mat.copper]] processing."),
    ]

from pathlib import Path

import pytest

from klustra.core.errors import ConfigError, ConnectorNotFoundError
from klustra.core.file_state_store import FileStateStore
from klustra.ingestion.connectors import ConnectorRegistry, LocalFolderConnector
from klustra.ingestion.domain_registry import (
    LocalFolderSourceConfig,
    check_instructions,
    get_domain,
    list_domains,
    load_domain,
)
from klustra.ingestion.translator_registry import TranslatorRegistry

# ---------------------------------------------------------------------------
# load_domain
# ---------------------------------------------------------------------------

_VALID_TOML = """\
label = "engineering"
title = "Engineering"
description = "Tech docs"

[[sources]]
type = "local_folder"
path = "C:/data/engineering"
recursive = true
glob = ["*.xlsx", "*.pdf"]
"""


def test_load_domain_valid(tmp_path: Path) -> None:
    p = tmp_path / "engineering.toml"
    p.write_text(_VALID_TOML, encoding="utf-8")
    cfg = load_domain(p)
    assert cfg.label == "engineering"
    assert len(cfg.sources) == 1
    src = cfg.sources[0]
    assert isinstance(src, LocalFolderSourceConfig)
    assert src.path == "C:/data/engineering"
    assert src.glob == ["*.xlsx", "*.pdf"]


def test_load_domain_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_domain(tmp_path / "missing.toml")


def test_load_domain_invalid_toml_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.toml"
    p.write_text("not valid toml ===", encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid TOML"):
        load_domain(p)


def test_load_domain_invalid_schema_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.toml"
    p.write_text("label = 123\ntitle = 'x'\ndescription = 'y'\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid domain config"):
        load_domain(p)


def test_load_domain_no_sources(tmp_path: Path) -> None:
    p = tmp_path / "empty.toml"
    p.write_text('label = "x"\ntitle = "X"\ndescription = "desc"\n', encoding="utf-8")
    cfg = load_domain(p)
    assert cfg.sources == []


# ---------------------------------------------------------------------------
# list_domains
# ---------------------------------------------------------------------------


def test_list_domains(tmp_path: Path) -> None:
    domains_dir = tmp_path / ".klustra" / "domains"
    domains_dir.mkdir(parents=True)
    for label in ("alpha", "beta"):
        (domains_dir / f"{label}.toml").write_text(
            f'label = "{label}"\ntitle = "{label.title()}"\ndescription = "desc"\n',
            encoding="utf-8",
        )
    domains = list_domains(tmp_path / ".klustra")
    assert len(domains) == 2
    assert {d.label for d in domains} == {"alpha", "beta"}


def test_list_domains_empty_dir(tmp_path: Path) -> None:
    domains_dir = tmp_path / ".klustra" / "domains"
    domains_dir.mkdir(parents=True)
    assert list_domains(tmp_path / ".klustra") == []


def test_list_domains_missing_dir(tmp_path: Path) -> None:
    assert list_domains(tmp_path / ".klustra") == []


# ---------------------------------------------------------------------------
# get_domain
# ---------------------------------------------------------------------------


def test_get_domain_found(tmp_path: Path) -> None:
    domains_dir = tmp_path / ".klustra" / "domains"
    domains_dir.mkdir(parents=True)
    (domains_dir / "eng.toml").write_text(
        'label = "eng"\ntitle = "Engineering"\ndescription = "desc"\n',
        encoding="utf-8",
    )
    cfg = get_domain("eng", tmp_path / ".klustra")
    assert cfg is not None
    assert cfg.label == "eng"


def test_get_domain_not_found(tmp_path: Path) -> None:
    (tmp_path / ".klustra" / "domains").mkdir(parents=True)
    assert get_domain("missing", tmp_path / ".klustra") is None


# ---------------------------------------------------------------------------
# LocalFolderConnector
# ---------------------------------------------------------------------------


def test_local_folder_connector_sync(tmp_path: Path, registry: TranslatorRegistry) -> None:
    folder = tmp_path / "data"
    folder.mkdir()
    (folder / "a.txt").write_text("hello", encoding="utf-8")
    state = FileStateStore(tmp_path)
    connector = LocalFolderConnector(registry, run_id="r1")
    source = LocalFolderSourceConfig(type="local_folder", path=str(folder), recursive=True)
    cs = connector.sync(source, state)
    assert len(cs.sources.added) == 1


# ---------------------------------------------------------------------------
# ConnectorRegistry
# ---------------------------------------------------------------------------


def test_connector_registry_get(registry: TranslatorRegistry) -> None:
    reg = ConnectorRegistry()
    connector = LocalFolderConnector(registry)
    reg.register(connector)
    assert reg.get("local_folder") is connector


def test_connector_registry_missing_raises(registry: TranslatorRegistry) -> None:
    reg = ConnectorRegistry()
    with pytest.raises(ConnectorNotFoundError):
        reg.get("sharepoint")


# ---------------------------------------------------------------------------
# check_instructions
# ---------------------------------------------------------------------------


def test_check_instructions_found(tmp_path: Path) -> None:
    klustra_dir = tmp_path / ".klustra"
    instr_dir = klustra_dir / "instructions"
    instr_dir.mkdir(parents=True)
    instr_file = instr_dir / "engineering.md"
    instr_file.write_text("# Engineering instructions\n", encoding="utf-8")
    result = check_instructions("engineering", klustra_dir)
    assert result == instr_file


def test_check_instructions_missing_returns_none(tmp_path: Path) -> None:
    """Missing instructions file produces None (warning), not an error."""
    klustra_dir = tmp_path / ".klustra"
    klustra_dir.mkdir(parents=True)
    result = check_instructions("nonexistent", klustra_dir)
    assert result is None


# ---------------------------------------------------------------------------
# LocalFolderConnector equivalence to sync_folder
# ---------------------------------------------------------------------------


def test_local_folder_connector_matches_sync_folder(
    tmp_path: Path, registry: TranslatorRegistry
) -> None:
    """LocalFolderConnector.sync() produces the same ChangeSet as sync_folder directly."""
    folder = tmp_path / "data"
    folder.mkdir()
    (folder / "a.txt").write_text("alpha", encoding="utf-8")
    (folder / "b.txt").write_text("beta", encoding="utf-8")

    from klustra.ingestion.source_manager import sync_folder

    state_direct = FileStateStore(tmp_path / "direct")
    cs_direct = sync_folder(folder, state_direct, registry, run_id="run1", recursive=True)

    state_connector = FileStateStore(tmp_path / "connector")
    connector = LocalFolderConnector(registry, run_id="run1")
    source = LocalFolderSourceConfig(type="local_folder", path=str(folder), recursive=True)
    cs_connector = connector.sync(source, state_connector)

    assert sorted(cs_direct.sources.added) == sorted(cs_connector.sources.added)
    assert cs_direct.sources.modified == cs_connector.sources.modified
    assert cs_direct.sources.removed == cs_connector.sources.removed

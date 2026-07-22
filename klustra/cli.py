"""Typer CLI — thin wrapper over klustra.api (SPEC §12)."""

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from klustra.logging_setup import configure_logging

if TYPE_CHECKING:
    from klustra.api import Klustra
    from klustra.core.changeset import ChangeSet

app = typer.Typer(name="klustra", no_args_is_help=True)
domain_app = typer.Typer(name="domain", no_args_is_help=True)
app.add_typer(domain_app, name="domain")


@app.callback()
def main(
    verbose: Annotated[
        bool,
        typer.Option(
            "-v", "--verbose", help="Debug logging: request/response shapes, token counts"
        ),
    ] = False,
    quiet: Annotated[bool, typer.Option("-q", "--quiet", help="Warnings and errors only")] = False,
) -> None:
    """klustra: recursive knowledge abstraction engine."""
    if verbose and quiet:
        typer.echo("--verbose and --quiet are mutually exclusive", err=True)
        raise typer.Exit(1)
    configure_logging(verbose=verbose, quiet=quiet)


def _get_klustra(root: "Path | None" = None) -> "Klustra":
    from klustra.api import Klustra as _Klustra

    return _Klustra(root=root or Path("."))


# --- init ---


@app.command()
def init(
    path: Annotated[Path, typer.Argument(help="Project root directory")] = Path("."),
) -> None:
    """Scaffold a new klustra project (klustra.toml, .klustra/ dirs, instructions template)."""
    root = path.resolve()
    root.mkdir(parents=True, exist_ok=True)

    toml_path = root / "klustra.toml"
    if not toml_path.exists():
        toml_path.write_text(
            '[llm.extraction]\nprovider = "openrouter"\nmodel = "deepseek/deepseek-chat"\n\n'
            '[llm.librarian]\nprovider = "openrouter"\nmodel = "deepseek/deepseek-chat"\n',
            encoding="utf-8",
        )
        typer.echo(f"Created {toml_path}")
    else:
        typer.echo(f"Already exists: {toml_path}")

    for subdir in [".klustra", ".klustra/domains", ".klustra/instructions", ".klustra/vault"]:
        d = root / subdir
        d.mkdir(parents=True, exist_ok=True)

    instructions_template = root / ".klustra" / "instructions" / "_template.md"
    if not instructions_template.exists():
        instructions_template.write_text(
            "# Domain Instructions\n\nAdd domain-specific instructions here.\n",
            encoding="utf-8",
        )

    typer.echo("Project initialized.")


# --- ingest ---


@app.command()
def ingest(
    path: Annotated[Path, typer.Argument(help="File or directory to ingest")],
    recursive: Annotated[bool, typer.Option("-r", "--recursive", help="Recurse")] = True,
    domain: Annotated[str | None, typer.Option("-d", "--domain", help="Domain label")] = None,
) -> None:
    """Ingest a file or folder into the knowledge base."""
    nx = _get_klustra()
    resolved = path.resolve()
    if resolved.is_dir():
        cs = nx.ingest_folder(resolved, recursive=recursive)
    else:
        cs = nx.ingest_file(resolved, domain=domain)
    _print_changeset(cs)


# --- update ---


@app.command()
def update(
    path: Annotated[Path, typer.Argument(help="File to update")],
) -> None:
    """Re-hash an already-tracked source file."""
    nx = _get_klustra()
    cs = nx.update_source(path.resolve())
    _print_changeset(cs)


# --- remove ---


@app.command()
def remove(
    path: Annotated[Path, typer.Argument(help="File to remove")],
) -> None:
    """Remove a source and cascade to pages."""
    nx = _get_klustra()
    cs = nx.remove_source(path.resolve())
    _print_changeset(cs)


# --- sync ---


@app.command()
def sync(
    path: Annotated[Path | None, typer.Argument(help="Directory to sync")] = None,
    domain: Annotated[str | None, typer.Option("--domain", help="Sync a domain")] = None,
    all_domains: Annotated[bool, typer.Option("--all", help="Sync all domains")] = False,
) -> None:
    """Sync a folder or domain (diff-based add/update/remove)."""
    nx = _get_klustra()
    if all_domains:
        cs = nx.sync_all()
    elif domain:
        cs = nx.sync_domain(domain)
    elif path:
        cs = nx.sync_folder(path.resolve())
    else:
        typer.echo("Provide a path, --domain, or --all", err=True)
        raise typer.Exit(1)
    _print_changeset(cs)


# --- compile ---


@app.command(name="compile")
def compile_cmd(
    fresh: Annotated[
        bool,
        typer.Option(
            "--fresh",
            "--no-resume",
            help="Discard checkpoints and recompile every source from scratch.",
        ),
    ] = False,
) -> None:
    """Run the full compile pipeline (extraction + librarian merge).

    Resumes from the last incomplete source by default; pass --fresh to rebuild.
    """
    nx = _get_klustra()
    results = nx.compile(fresh=fresh)
    typer.echo(f"Compiled {len(results)} page(s).")


# --- validate ---


@app.command()
def validate() -> None:
    """Check OKF conformance on all pages."""
    nx = _get_klustra()
    findings = nx.validate()
    if not findings:
        typer.echo("All pages conform.")
    else:
        for f in findings:
            typer.echo(f"  {f.entity_id}: {f.message}")
        raise typer.Exit(1)


# --- lint ---


@app.command()
def lint() -> None:
    """Run quality checks on all pages."""
    nx = _get_klustra()
    findings = nx.lint()
    if not findings:
        typer.echo("No lint findings.")
    else:
        for f in findings:
            typer.echo(f"  [{f.severity}] {f.entity_id}: {f.category} — {f.message}")
        errors = [f for f in findings if f.severity == "error"]
        if errors:
            raise typer.Exit(1)


# --- export ---


@app.command()
def export(
    target: Annotated[str, typer.Argument(help="Export target (obsidian, okf_bundle)")],
    output_dir: Annotated[Path, typer.Option("-o", "--output", help="Output directory")],
) -> None:
    """Export pages to the specified format."""
    nx = _get_klustra()
    nx.export(target, output_dir)
    typer.echo(f"Exported to {output_dir} ({target}).")


# --- domain subcommands ---


@domain_app.command("list")
def domain_list() -> None:
    """List all configured domains."""
    nx = _get_klustra()
    domains = nx.domain_list()
    if not domains:
        typer.echo("No domains configured.")
        return
    for d in domains:
        typer.echo(f"  {d.label}: {d.title}")


@domain_app.command("show")
def domain_show(
    label: Annotated[str, typer.Argument(help="Domain label")],
) -> None:
    """Show configuration for a specific domain."""
    from klustra.ingestion.domain_registry import check_instructions

    nx = _get_klustra()
    domain_cfg = nx.domain_show(label)
    if domain_cfg is None:
        typer.echo(f"Domain {label!r} not found.", err=True)
        raise typer.Exit(1)
    typer.echo(f"Label: {domain_cfg.label}")
    typer.echo(f"Title: {domain_cfg.title}")
    typer.echo(f"Description: {domain_cfg.description}")
    typer.echo(f"Sources: {len(domain_cfg.sources)}")
    for src in domain_cfg.sources:
        typer.echo(f"  - [{src.type}] {src.path}")

    klustra_dir = nx.root / ".klustra"
    instr_path = check_instructions(label, klustra_dir)
    if instr_path:
        typer.echo(f"Instructions: {instr_path} (found)")
    else:
        expected = klustra_dir / "instructions" / f"{label}.md"
        typer.echo(f"Instructions: {expected} (WARNING: not found)")


# --- hierarchy (stub) ---


@app.command()
def hierarchy(
    full: Annotated[bool, typer.Option("--full", help="Force full rebuild")] = False,
) -> None:
    """Build cluster/home page hierarchy (RAPTOR — SPEC §6)."""
    from klustra.core.errors import ConfigError

    nx = _get_klustra()
    try:
        result = nx.build_hierarchy(full=full)
    except (ConfigError, NotImplementedError) as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from None
    typer.echo(f"Built {len(result.pages)} page(s), max_level={result.max_level}.")


# --- stats ---


@app.command()
def stats() -> None:
    """Show token accounting from last compile."""
    nx = _get_klustra()
    entries = nx._sink.entries
    if not entries:
        typer.echo("No accounting data.")
        return
    total_in = sum(e.tokens_in for e in entries)
    total_out = sum(e.tokens_out for e in entries)
    typer.echo(f"Calls: {len(entries)}")
    typer.echo(f"Tokens in:  {total_in}")
    typer.echo(f"Tokens out: {total_out}")


# --- helpers ---


def _print_changeset(cs: "ChangeSet") -> None:
    parts: list[str] = []
    if cs.sources.added:
        parts.append(f"+{len(cs.sources.added)} source(s)")
    if cs.sources.modified:
        parts.append(f"~{len(cs.sources.modified)} source(s)")
    if cs.sources.removed:
        parts.append(f"-{len(cs.sources.removed)} source(s)")
    if cs.pages.removed:
        parts.append(f"-{len(cs.pages.removed)} page(s)")
    if cs.pages.affected:
        parts.append(f"~{len(cs.pages.affected)} page(s) affected")
    if not parts:
        typer.echo("No changes.")
    else:
        typer.echo(", ".join(parts))

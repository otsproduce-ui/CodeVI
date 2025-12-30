"""
CodeVI CLI - Unified command interface
"""
import typer
from pathlib import Path
import sys

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from packages.core.ingest import ingest_repo
from backend.search_engine import SearchEngine
import json

app = typer.Typer(help="CodeVI - Codebase analysis and search")


@app.command()
def ingest(
    repo: str = typer.Option(..., "--repo", "-r", help="Path to your project root"),
    out: str = typer.Option("./data", "--out", "-o", help="Output folder")
):
    """Extract routes, API calls, and relationships from codebase"""
    repo_p = Path(repo).resolve()
    out_p = Path(out).resolve()
    out_p.mkdir(parents=True, exist_ok=True)

    if not repo_p.exists():
        typer.echo(f"Error: Path does not exist: {repo_p}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Ingesting codebase at: {repo_p}")
    result = ingest_repo(repo_p)

    (out_p / "entities.jsonl").write_text(
        "\n".join(json.dumps(n, ensure_ascii=False) for n in result["nodes"]),
        encoding="utf-8"
    )
    (out_p / "edges.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in result["edges"]),
        encoding="utf-8"
    )
    
    typer.echo(f"✓ Wrote {len(result['nodes'])} nodes and {len(result['edges'])} edges to {out_p}")


@app.command()
def index(
    repo: str = typer.Option(..., "--repo", "-r", help="Path to your project root"),
    out: str = typer.Option("./data", "--out", "-o", help="Output folder")
):
    """Index codebase for BM25 search"""
    repo_p = Path(repo).resolve()
    out_p = Path(out).resolve()
    out_p.mkdir(parents=True, exist_ok=True)

    if not repo_p.exists():
        typer.echo(f"Error: Path does not exist: {repo_p}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Indexing codebase at: {repo_p}")
    search_engine = SearchEngine(repo_p)
    search_engine.index_codebase()
    
    typer.echo(f"✓ Indexed {search_engine.get_file_count()} files")
    
    # Also run ingest to extract routes
    typer.echo("Extracting routes and relationships...")
    result = ingest_repo(repo_p)
    
    (out_p / "entities.jsonl").write_text(
        "\n".join(json.dumps(n, ensure_ascii=False) for n in result["nodes"]),
        encoding="utf-8"
    )
    (out_p / "edges.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in result["edges"]),
        encoding="utf-8"
    )
    
    typer.echo(f"✓ Extracted {len(result['nodes'])} nodes and {len(result['edges'])} edges")


@app.command()
def query(
    query: str = typer.Option(..., "--query", "-q", help="Search query"),
    repo: str = typer.Option(".", "--repo", "-r", help="Path to indexed project root"),
    max_results: int = typer.Option(10, "--max", "-m", help="Maximum results")
):
    """Search indexed codebase"""
    repo_p = Path(repo).resolve()
    
    if not repo_p.exists():
        typer.echo(f"Error: Path does not exist: {repo_p}", err=True)
        raise typer.Exit(1)

    search_engine = SearchEngine(repo_p)
    
    # Try to load existing index or index on the fly
    if not search_engine.is_indexed():
        typer.echo("Codebase not indexed. Indexing now...")
        search_engine.index_codebase()
    
    results = search_engine.search(query, max_results=max_results)
    
    if not results:
        typer.echo("No results found.")
        return
    
    typer.echo(f"\nFound {len(results)} results:\n")
    for i, result in enumerate(results, 1):
        typer.echo(f"{i}. {result['file_path']}:{result['line_number']} (score: {result['score']:.2f})")
        typer.echo(f"   {result['content'].split(chr(10))[0][:80]}...")
        typer.echo()


if __name__ == "__main__":
    app()


"""
Forge CLI - Command Line Interface

Main entry point for Forge commands.
"""

import asyncio
from pathlib import Path
from typing import Any, Coroutine, Optional, TypeVar

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from forge.agents.incident_responder import IncidentResponder
from forge.agents.knowledge_gap_detector import KnowledgeGapDetector
from forge.agents.postmortem_generator import PostmortemGenerator
from forge.core.config import get_settings
from forge.core.logging import setup_logging
from forge.ingestion.engine import IngestionEngine

app = typer.Typer(
    name="forge",
    help="🔥 Forge - The Never-Forget DevOps Intelligence Platform",
    add_completion=False,
)

console = Console()

T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Helper to run async functions from sync CLI context."""
    return asyncio.run(coro)


@app.command()
def ingest(
    incidents_path: Optional[Path] = typer.Option(
        None,
        "--incidents",
        "-i",
        help="Path to incidents JSON file",
    ),
    architecture_path: Optional[Path] = typer.Option(
        None,
        "--architecture",
        "-a",
        help="Path to architecture JSON file",
    ),
    postmortems_path: Optional[Path] = typer.Option(
        None,
        "--postmortems",
        "-p",
        help="Path to postmortems JSON file",
    ),
    dataset_name: Optional[str] = typer.Option(
        None,
        "--dataset",
        "-d",
        help="Dataset name prefix (e.g., 'forge' creates forge_incidents, forge_architecture, forge_postmortems)",
    ),
):
    """
    📥 Ingest DevOps data into Cognee knowledge graph.

    Loads incidents, architecture, and postmortems into Cognee Cloud
    with temporal awareness for incident timelines.
    """
    setup_logging()
    settings = get_settings()

    console.print(
        Panel.fit(
            "[bold cyan]🔥 Forge Data Ingestion[/bold cyan]\n"
            "[dim]Loading DevOps knowledge into Cognee Cloud[/dim]",
            border_style="cyan",
        )
    )

    async def _ingest():
        engine = IngestionEngine()

        # Connect to Cognee Cloud
        console.print("\n[yellow]Connecting to Cognee Cloud...[/yellow]")
        await engine.cognee.connect()
        console.print("[green]✓ Connected to Cognee Cloud[/green]\n")

        results = {}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Build per-type dataset names when a prefix is provided
            incidents_dataset = f"{dataset_name}_incidents" if dataset_name else None
            architecture_dataset = f"{dataset_name}_architecture" if dataset_name else None
            postmortems_dataset = f"{dataset_name}_postmortems" if dataset_name else None

            # Ingest incidents
            task = progress.add_task(
                "[cyan]Ingesting incidents with temporal awareness...", total=None
            )
            try:
                count = await engine.ingest_incidents(
                    data_path=incidents_path, dataset_name=incidents_dataset
                )
                results["incidents"] = count
                progress.update(task, description=f"[green]✓ Ingested {count} incidents")
            except Exception as e:
                progress.update(task, description=f"[red]✗ Failed to ingest incidents: {e}")
                results["incidents"] = 0

            # Ingest architecture
            task = progress.add_task(
                "[cyan]Ingesting architecture (services, teams, runbooks)...", total=None
            )
            try:
                count = await engine.ingest_architecture(
                    data_path=architecture_path, dataset_name=architecture_dataset
                )
                results["architecture"] = count
                progress.update(
                    task, description=f"[green]✓ Ingested {count} architecture items"
                )
            except Exception as e:
                progress.update(
                    task, description=f"[red]✗ Failed to ingest architecture: {e}"
                )
                results["architecture"] = 0

            # Ingest postmortems
            task = progress.add_task(
                "[cyan]Ingesting postmortems with temporal awareness...", total=None
            )
            try:
                count = await engine.ingest_postmortems(
                    data_path=postmortems_path, dataset_name=postmortems_dataset
                )
                results["postmortems"] = count
                progress.update(
                    task, description=f"[green]✓ Ingested {count} postmortems"
                )
            except Exception as e:
                progress.update(
                    task, description=f"[red]✗ Failed to ingest postmortems: {e}"
                )
                results["postmortems"] = 0

        # Disconnect
        await engine.cognee.disconnect()

        # Display results
        console.print()
        table = Table(title="Ingestion Summary", show_header=True, header_style="bold cyan")
        table.add_column("Dataset", style="cyan")
        table.add_column("Items Ingested", justify="right", style="green")

        for dataset, count in results.items():
            table.add_row(dataset, str(count))

        total = sum(results.values())
        table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")

        console.print(table)
        console.print(
            "\n[green bold]✓ Ingestion complete![/green bold]\n"
            "[dim]Your DevOps knowledge is now available in Cognee Cloud.[/dim]"
        )

    run_async(_ingest())


@app.command()
def status():
    """
    📊 Check Forge and Cognee Cloud status.
    """
    setup_logging()
    settings = get_settings()

    console.print(
        Panel.fit(
            "[bold cyan]🔥 Forge Status[/bold cyan]",
            border_style="cyan",
        )
    )

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Configuration", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Cognee Cloud URL", settings.cognee_service_url)
    table.add_row("Cognee API Key", "✓ Configured" if settings.cognee_api_key else "✗ Not configured")
    table.add_row("LLM Provider", settings.llm_provider)
    table.add_row("LLM API Key", "✓ Configured" if settings.llm_api_key else "✗ Not configured")
    table.add_row("Incidents Dataset", str(settings.incidents_data_path))
    table.add_row("Architecture Dataset", str(settings.architecture_data_path))
    table.add_row("Postmortems Dataset", str(settings.postmortem_data_path))

    console.print(table)


@app.command()
def respond(
    alert: str = typer.Option(
        ...,
        "--alert",
        "-a",
        help="Alert text or incident description",
    ),
    services: Optional[str] = typer.Option(
        None,
        "--services",
        "-s",
        help="Comma-separated list of affected services",
    ),
    severity: str = typer.Option(
        "P2",
        "--severity",
        help="Incident severity (P1, P2, P3, P4)",
    ),
):
    """
    🔥 Diagnose an incident using the Incident Responder agent.

    Uses temporal awareness and session memory to analyze incidents.
    """
    setup_logging()

    console.print(
        Panel.fit(
            "[bold cyan]🔥 Incident Responder[/bold cyan]\n"
            "[dim]Analyzing incident with knowledge graph[/dim]",
            border_style="cyan",
        )
    )

    async def _respond():
        affected_services = services.split(",") if services else None

        responder = IncidentResponder()

        console.print("\n[yellow]Diagnosing incident...[/yellow]")
        diagnosis = await responder.diagnose_incident(
            alert_text=alert,
            affected_services=affected_services,
            severity=severity,
        )

        console.print("[green]✓ Diagnosis complete[/green]\n")
        console.print(f"[dim]Session ID: {diagnosis['session_id']}[/dim]")
        console.print(f"[dim]Confidence: {diagnosis.get('confidence', 0.0):.2f}[/dim]\n")

        # Display diagnosis
        console.print(Panel(diagnosis["diagnosis"], title="Diagnosis", border_style="cyan"))

        # Show similar incidents
        if diagnosis.get("similar_incidents"):
            console.print(f"\n[bold cyan]Similar Incidents Found:[/bold cyan] {len(diagnosis['similar_incidents'])}")
            for i, incident in enumerate(diagnosis["similar_incidents"][:3], 1):
                text = incident.get("text", str(incident))[:200]
                console.print(f"  {i}. {text}...")

        console.print("\n[dim]Use 'forge respond --continue' to continue investigation[/dim]")
        console.print("[dim]Use 'forge respond --resolve' to mark as resolved[/dim]\n")

    run_async(_respond())


@app.command()
def postmortem(
    incident_id: str = typer.Option(
        ...,
        "--incident",
        "-i",
        help="Incident ID (e.g., INC-001)",
    ),
    session_id: str = typer.Option(
        ...,
        "--session",
        "-s",
        help="Session ID from incident response",
    ),
    context: Optional[str] = typer.Option(
        None,
        "--context",
        "-c",
        help="Additional context for the postmortem",
    ),
):
    """
    📝 Generate a postmortem report using the Postmortem Generator agent.

    Creates structured postmortems from incident session memory.
    """
    setup_logging()

    console.print(
        Panel.fit(
            "[bold cyan]📝 Postmortem Generator[/bold cyan]\n"
            "[dim]Generating structured postmortem report[/dim]",
            border_style="cyan",
        )
    )

    async def _postmortem():
        generator = PostmortemGenerator()

        console.print("\n[yellow]Generating postmortem...[/yellow]")
        postmortem = await generator.generate_postmortem(
            incident_id=incident_id,
            incident_session_id=session_id,
            additional_context=context or "",
        )

        console.print("[green]✓ Postmortem generated[/green]\n")

        # Display postmortem
        console.print(
            Panel(
                postmortem["postmortem_text"],
                title=f"Postmortem for {incident_id}",
                border_style="green",
            )
        )

        console.print(f"\n[dim]Generated at: {postmortem['generated_at']}[/dim]")
        console.print("[dim]Postmortem stored in knowledge graph[/dim]\n")

    run_async(_postmortem())


@app.command()
def gaps():
    """
    🔍 Detect knowledge gaps using the Knowledge Gap Detector agent.

    Identifies missing postmortems, runbooks, and documentation.
    """
    setup_logging()

    console.print(
        Panel.fit(
            "[bold cyan]🔍 Knowledge Gap Detector[/bold cyan]\n"
            "[dim]Analyzing knowledge graph for gaps[/dim]",
            border_style="cyan",
        )
    )

    async def _gaps():
        detector = KnowledgeGapDetector()

        console.print("\n[yellow]Detecting knowledge gaps...[/yellow]")
        gaps = await detector.detect_gaps()

        console.print("[green]✓ Gap detection complete[/green]\n")

        # Display summary
        console.print(Panel.fit(
            f"[bold]Knowledge Gaps Detected:[/bold]\n"
            f"  • Incidents without postmortems: {len(gaps['missing_postmortems'])}\n"
            f"  • Services without runbooks: {len(gaps['missing_runbooks'])}\n"
            f"  • Recurring patterns: {len(gaps['recurring_patterns'])}\n"
            f"  • Documentation gaps: {len(gaps['documentation_gaps'])}",
            title="Knowledge Gap Summary",
            border_style="yellow",
        ))

        # Show details
        if gaps["missing_postmortems"]:
            console.print("\n[bold red]Incidents Without Postmortems:[/bold red]")
            for incident in gaps["missing_postmortems"][:5]:
                console.print(f"  • {incident.get('id')}: {incident.get('title', 'Unknown')[:100]}")

        if gaps["missing_runbooks"]:
            console.print("\n[bold yellow]Services Without Runbooks:[/bold yellow]")
            for service in gaps["missing_runbooks"][:5]:
                console.print(f"  • {service.get('name')}: {service.get('description', 'Unknown')[:100]}")

        if gaps["recurring_patterns"]:
            console.print("\n[bold cyan]Recurring Patterns:[/bold cyan]")
            for pattern in gaps["recurring_patterns"][:5]:
                console.print(f"  • {pattern['pattern'][:150]}...")

        if gaps["recommendations"]:
            console.print("\n[bold green]Top Recommendations:[/bold green]")
            for i, rec in enumerate(gaps["recommendations"][:5], 1):
                console.print(f"  {i}. {rec['recommendation']}")

        console.print(f"\n[dim]Detected at: {gaps['detected_at']}[/dim]\n")

    run_async(_gaps())


@app.command()
def demo():
    """
    🎬 Run the Forge demo scenario.

    Demonstrates incident response, postmortem generation,
    and knowledge gap detection.
    """
    setup_logging()

    console.print(
        Panel.fit(
            "[bold cyan]🔥 Forge Demo[/bold cyan]\n"
            "[dim]Running full incident lifecycle demonstration[/dim]",
            border_style="cyan",
        )
    )

    async def _demo():
        # Step 1: Simulate an incident
        console.print("\n[yellow]Step 1: Simulating incident...[/yellow]")
        alert_text = """
        CRITICAL ALERT: payments-service is experiencing HTTP 500 errors.
        Error rate has spiked to 45% in the last 5 minutes.
        Affected endpoint: /api/v1/checkout
        Latency has increased from 200ms to 8s.
        Database connection pool appears exhausted.
        """

        console.print("[green]✓ Incident detected[/green]")
        console.print(f"[dim]Alert: {alert_text[:100]}...[/dim]\n")

        # Step 2: Incident Responder diagnosis
        console.print("[yellow]Step 2: Incident Responder analyzing...[/yellow]")
        responder = IncidentResponder()
        diagnosis = await responder.diagnose_incident(
            alert_text=alert_text,
            affected_services=["payments-service"],
            severity="P1",
        )

        console.print("[green]✓ Diagnosis complete[/green]")
        console.print(f"[dim]Session ID: {diagnosis['session_id']}[/dim]")
        console.print(f"[dim]Confidence: {diagnosis.get('confidence', 0.0):.2f}[/dim]\n")

        # Display diagnosis
        console.print(Panel(diagnosis["diagnosis"], title="Diagnosis", border_style="cyan"))

        # Step 3: Continue investigation
        console.print("\n[yellow]Step 3: Continuing investigation...[/yellow]")
        new_info = "Database logs show connection pool at 100% capacity. Restarting service."
        updated = await responder.continue_investigation(new_info)
        console.print("[green]✓ Investigation updated[/green]\n")

        # Step 4: Resolve incident
        console.print("[yellow]Step 4: Resolving incident...[/yellow]")
        resolution = await responder.resolve_incident(
            "Increased connection pool size from 50 to 100. Added monitoring alerts."
        )
        console.print("[green]✓ Incident resolved[/green]")
        console.print(f"[dim]Memory bridged: {resolution['memory_bridged']}[/dim]")
        console.print(f"[dim]Truth subspace built: {resolution['truth_subspace_built']}[/dim]\n")

        # Step 5: Generate postmortem
        console.print("[yellow]Step 5: Generating postmortem...[/yellow]")
        generator = PostmortemGenerator()
        postmortem = await generator.generate_postmortem(
            incident_id="INC-DEMO-001",
            incident_session_id=diagnosis["session_id"],
        )
        console.print("[green]✓ Postmortem generated[/green]\n")

        # Display postmortem
        console.print(
            Panel(
                postmortem["postmortem_text"],
                title="Generated Postmortem",
                border_style="green",
            )
        )

        # Step 6: Detect knowledge gaps
        console.print("\n[yellow]Step 6: Detecting knowledge gaps...[/yellow]")
        detector = KnowledgeGapDetector()
        gaps = await detector.detect_gaps()
        console.print("[green]✓ Gap detection complete[/green]\n")

        # Display gaps summary
        console.print(Panel.fit(
            f"[bold]Knowledge Gaps Detected:[/bold]\n"
            f"  • Incidents without postmortems: {len(gaps['missing_postmortems'])}\n"
            f"  • Services without runbooks: {len(gaps['missing_runbooks'])}\n"
            f"  • Recurring patterns: {len(gaps['recurring_patterns'])}\n"
            f"  • Documentation gaps: {len(gaps['documentation_gaps'])}",
            title="Knowledge Gap Summary",
            border_style="yellow",
        ))

        if gaps["recommendations"]:
            console.print("\n[bold cyan]Top Recommendations:[/bold cyan]")
            for i, rec in enumerate(gaps["recommendations"][:3], 1):
                console.print(f"  {i}. {rec['recommendation']}")

        console.print("\n[green bold]✓ Demo complete![/green bold]")
        console.print("[dim]Forge has demonstrated the full incident lifecycle with persistent memory.[/dim]\n")

    run_async(_demo())


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show Forge version",
    ),
):
    """
    🔥 Forge - The Never-Forget DevOps Intelligence Platform

    Powered by Cognee Cloud's hybrid graph-vector memory layer.
    """
    if version:
        from forge import __version__

        console.print(f"Forge v{__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()

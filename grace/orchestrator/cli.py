# AI_HEADER
# module: M-ORCH-CLI
# wave: W-ORCH-1
# purpose: Orchestrator CLI

import click
from pathlib import Path
from .core import GraceOrchestrator


@click.group()
def cli():
    """GRACE orchestrator CLI."""
    pass


@cli.command()
@click.option('--plan', default='grace/development-plan.xml', help='Path to development plan')
def status(plan):
    """Show orchestrator status."""
    orch = GraceOrchestrator(Path(plan))
    progress = orch.get_progress()

    click.echo(f"📊 GRACE Orchestrator Status")
    click.echo(f"")
    click.echo(f"Total waves: {progress['total']}")
    click.echo(f"✅ Completed: {progress['completed']}")
    click.echo(f"🔄 In progress: {progress['in_progress']}")
    click.echo(f"⏳ Pending: {progress['pending']}")
    click.echo(f"Progress: {progress['percentage']:.1f}%")


@cli.command()
@click.option('--plan', default='grace/development-plan.xml', help='Path to development plan')
def next(plan):
    """Show next waves ready to execute."""
    orch = GraceOrchestrator(Path(plan))
    ready = orch.get_ready_waves()

    if not ready:
        click.echo("✅ No waves ready (all dependencies satisfied or all completed)")
        return

    click.echo(f"🚀 Ready to execute ({len(ready)} waves):")
    click.echo("")

    for wave in ready:
        click.echo(f"  {wave.id} — {wave.title}")
        click.echo(f"    Phase: {wave.phase}")
        if wave.dependencies:
            click.echo(f"    Dependencies: {', '.join(wave.dependencies)}")
        click.echo("")


@cli.command()
@click.argument('wave_id')
@click.option('--plan', default='grace/development-plan.xml', help='Path to development plan')
def complete(wave_id, plan):
    """Mark wave as completed."""
    orch = GraceOrchestrator(Path(plan))
    wave = orch.get_wave(wave_id)

    if not wave:
        click.echo(f"❌ Wave {wave_id} not found")
        return

    orch.mark_completed(wave_id)
    click.echo(f"✅ Marked {wave_id} as completed")


@cli.command()
@click.option('--packets', default='grace/packets', help='Path to packets directory')
@click.argument('wave_id', required=False)
def validate(packets, wave_id):
    """Validate wave packets against GRACE canon."""
    from .validator import PacketValidator

    validator = PacketValidator(Path(packets))

    if wave_id:
        # Validate single packet
        is_valid, errors = validator.validate_packet(wave_id)

        if is_valid:
            click.echo(f"✅ {wave_id} is valid")
        else:
            click.echo(f"❌ {wave_id} has errors:")
            for error in errors:
                click.echo(f"  - {error}")
    else:
        # Validate all packets
        results = validator.validate_all()

        valid_count = sum(1 for r in results.values() if r['valid'])
        total_count = len(results)

        click.echo(f"📋 Packet Validation Results")
        click.echo(f"")
        click.echo(f"Valid: {valid_count}/{total_count}")
        click.echo(f"")

        # Show invalid packets
        invalid = {k: v for k, v in results.items() if not v['valid']}
        if invalid:
            click.echo("❌ Invalid packets:")
            for wave_id, result in invalid.items():
                click.echo(f"  {wave_id}:")
                for error in result['errors']:
                    click.echo(f"    - {error}")
        else:
            click.echo("✅ All packets are valid")


if __name__ == '__main__':
    cli()

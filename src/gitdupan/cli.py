import click
from rich.console import Console

console = Console()

@click.group()
@click.version_option()
def cli():
    """GitDuPan - A Git-like data management tool synced with Baidu Netdisk."""
    pass

@cli.command()
def init():
    """Initialize a new gitdupan repository."""
    from gitdupan.core.repo import init_repo
    try:
        init_repo()
        console.print("[green]Initialized empty GitDuPan repository.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@cli.command()
@click.option('--app-key', prompt='Your Baidu Netdisk App Key', help='Baidu Developer Platform App Key')
@click.option('--secret-key', prompt='Your Baidu Netdisk Secret Key', hide_input=True, help='Baidu Developer Platform Secret Key')
def login(app_key, secret_key):
    """Login to Baidu Netdisk and authorize GitDuPan."""
    from gitdupan.core.auth import login as auth_login
    auth_login(app_key, secret_key)

@cli.command()
@click.argument('files', nargs=-1)
def add(files):
    """Add file contents to the index."""
    from gitdupan.core.repo import add_files
    if not files:
        console.print("[yellow]Nothing specified, nothing added.[/yellow]")
        return
    try:
        added_count = add_files(files)
        console.print(f"[green]Added {added_count} file(s).[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@cli.command()
@click.option('-m', '--message', required=True, help="Commit message")
@click.option('-a', '--author', default="GitDuPan User", help="Author name")
def commit(message, author):
    """Record changes to the repository."""
    from gitdupan.core.repo import commit as repo_commit
    try:
        commit_hash = repo_commit(message, author)
        console.print(f"[green]Created commit {commit_hash[:8]}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@cli.command()
def status():
    """Show the working tree status."""
    from gitdupan.core.repo import status as repo_status
    try:
        stat = repo_status()
        if stat["staged"]:
            console.print("[green]Staged files:[/green]")
            for f in stat["staged"]:
                console.print(f"  [green]{f}[/green]")
        if stat["modified"]:
            console.print("[yellow]Modified files (not staged):[/yellow]")
            for f in stat["modified"]:
                console.print(f"  [yellow]{f}[/yellow]")
        if stat["untracked"]:
            console.print("[red]Untracked files:[/red]")
            for f in stat["untracked"]:
                console.print(f"  [red]{f}[/red]")
        if not any(stat.values()):
            console.print("Nothing to commit, working tree clean")
        elif stat["untracked"] or stat["modified"]:
            console.print("\n[yellow]Use `gitdupan add <file>` to include in what will be committed.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@cli.command()
def log():
    """Show commit logs."""
    from gitdupan.core.repo import get_log
    from datetime import datetime
    try:
        logs = get_log()
        if not logs:
            console.print("No commits yet.")
            return
        for entry in logs:
            dt = datetime.fromtimestamp(entry['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            console.print(f"[bold yellow]commit {entry['hash']}[/bold yellow]")
            console.print(f"Author: {entry['author']}")
            console.print(f"Date:   {dt}")
            console.print(f"\n    {entry['message']}\n")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@cli.command()
@click.argument('commit_hash')
def checkout(commit_hash):
    """Checkout a commit."""
    from gitdupan.core.repo import checkout as repo_checkout
    try:
        repo_checkout(commit_hash)
        console.print(f"[green]Checked out commit {commit_hash}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@cli.command()
@click.argument('action')
@click.argument('url', required=False)
def remote(action, url):
    """Manage remote repository (e.g. `remote add /apps/gitdupan/myrepo`)."""
    from gitdupan.core.sync import set_remote
    if action == "add":
        if not url:
            console.print("[red]URL is required for add[/red]")
            return
        try:
            set_remote(url)
            console.print(f"[green]Remote set to {url}[/green]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    else:
        console.print(f"[red]Unknown action {action}[/red]")

@cli.command()
def push():
    """Push local changes to Baidu Netdisk."""
    from gitdupan.core.sync import push as sync_push
    try:
        console.print("[yellow]Pushing to remote...[/yellow]")
        result = sync_push()
        console.print(f"[green]{result}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@cli.command()
def pull():
    """Pull remote changes from Baidu Netdisk."""
    from gitdupan.core.sync import pull as sync_pull
    try:
        console.print("[yellow]Pulling from remote...[/yellow]")
        result = sync_pull()
        console.print(f"[green]{result}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@cli.command()
@click.argument('url')
@click.argument('dest', required=False)
def clone(url, dest):
    """Clone a repository into a new directory."""
    from gitdupan.core.sync import clone as sync_clone
    try:
        console.print(f"[yellow]Cloning into '{dest or url.strip('/').split('/')[-1]}' from {url}...[/yellow]")
        result = sync_clone(url, dest)
        console.print(f"[green]{result}[/green]")
        console.print("[green]Clone successful![/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

if __name__ == '__main__':
    cli()

import click
from rich.console import Console

console = Console()

@click.group()
@click.version_option()
def cli():
    """GitDuPan - 一个同步到百度网盘的类Git数据管理工具。"""
    pass

@cli.command()
def init():
    """初始化一个新的 gitdupan 仓库。"""
    from gitdupan.core.repo import init_repo
    try:
        init_repo()
        console.print("[green]Initialized empty GitDuPan repository.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@cli.command()
@click.option('--app-key', help='百度开发者平台 App Key（可选，用于自定义授权）')
@click.option('--secret-key', help='百度开发者平台 Secret Key（可选，用于自定义授权）')
def login(app_key, secret_key):
    """登录百度网盘并授权 GitDuPan。"""
    from gitdupan.core.auth import login as auth_login
    if (app_key and not secret_key) or (not app_key and secret_key):
        console.print("[red]错误: 如果使用自定义授权，必须同时提供 --app-key 和 --secret-key。[/red]")
        return
    auth_login(app_key, secret_key)

@cli.command()
@click.argument('files', nargs=-1)
def add(files):
    """将文件内容添加到暂存区（Index）。"""
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
@click.option('-m', '--message', required=True, help="提交信息")
@click.option('-a', '--author', default="GitDuPan User", help="作者名称")
def commit(message, author):
    """记录仓库的更改（创建 Commit）。"""
    from gitdupan.core.repo import commit as repo_commit
    try:
        commit_hash = repo_commit(message, author)
        console.print(f"[green]Created commit {commit_hash[:8]}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@cli.command()
def status():
    """显示工作区状态。"""
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
    """显示提交日志。"""
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
    """检出（切换）到一个特定的 commit。"""
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
    """管理远程仓库 (例如: `remote add /apps/gitdupan/myrepo`)。"""
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
    """将本地更改推送到百度网盘。"""
    from gitdupan.core.sync import push as sync_push
    try:
        console.print("[yellow]Pushing to remote...[/yellow]")
        result = sync_push()
        console.print(f"[green]{result}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@cli.command()
def pull():
    """从百度网盘拉取远程更改。"""
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
    """克隆一个远程仓库到新目录中。"""
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

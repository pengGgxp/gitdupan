@echo off
uv run pyinstaller --name gitdupan --onefile --console src/gitdupan/cli.py
echo [green]Build completed successfully[/green]

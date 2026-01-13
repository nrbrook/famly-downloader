# Famly Photo Downloader

Download all photos of your child from [Famly.co](https://app.famly.co).

## Quick Start

```bash
# Install Playwright browser (first time only)
uv run --with playwright playwright install chromium

# Run the script
uv run famly_downloader.py --login
```

This opens a browser for you to log in, then automatically downloads all your child's photos.

> **Don't have uv?** Install it with `curl -LsSf https://astral.sh/uv/install.sh | sh` or use the [traditional install](#traditional-install) instead.

## How It Works

1. Opens a Chromium browser window
2. You log into Famly normally
3. Script captures your session and detects your children
4. You select which child's photos to download
5. Photos download to `./famly_photos/`

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--login` | `-l` | Open browser for interactive login |
| `--child-id` | `-c` | Your child's UUID (manual mode) |
| `--access-token` | `-t` | Your Famly access token (manual mode) |
| `--output` | `-o` | Output directory (default: `./famly_photos`) |
| `--workers` | `-w` | Number of parallel downloads (default: 4) |
| `--thumbnail-only` | | Download smaller thumbnail versions |
| `--dry-run` | | List images without downloading |

## Examples

```bash
# Interactive login with custom output directory
uv run famly_downloader.py --login --output ~/Pictures/famly

# Faster downloads with 8 parallel workers
uv run famly_downloader.py --login -w 8

# Preview what would be downloaded
uv run famly_downloader.py --login --dry-run

# Manual credentials (if you have them)
uv run famly_downloader.py -c "abc123..." -t "xyz789..."
```

## Output

Photos are saved as `YYYY-MM-DD_HHMMSS_imageId.jpg` (e.g., `2026-01-07_165003_f303f6e6.jpg`).

Multiple children get separate subfolders.

## Traditional Install

If you prefer pip over uv:

```bash
pip install -r requirements.txt
playwright install chromium
python famly_downloader.py --login
```

## Manual Credentials

If interactive login doesn't work, you can provide credentials manually:

1. Log into [Famly](https://app.famly.co) in your browser
2. Open DevTools (F12) → Network tab
3. Navigate to your child's photos
4. Find a request to `images/tagged` and copy:
   - `childId` from the URL
   - `x-famly-accesstoken` from the headers

```bash
uv run famly_downloader.py --child-id "YOUR_CHILD_ID" --access-token "YOUR_TOKEN"
```

## Notes

- Access tokens expire periodically; run `--login` again if you get a 401 error
- Existing files are skipped, so you can safely re-run the script
- Downloads highest resolution versions by default

## Development

```bash
# Install pre-commit hooks
uvx pre-commit install

# Lint & format
uvx ruff check .        # lint
uvx ruff check --fix .  # auto-fix
uvx ruff format .       # format

# Run pre-commit manually
uvx pre-commit run --all-files
```

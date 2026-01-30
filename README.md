# Famly Photo Downloader

Download all photos of your child from [Famly.co](https://app.famly.co).

## Quick Start

```bash
# Install Playwright browser (first time only)
uv run --with playwright playwright install chromium

# First run - log in via browser
uv run famly_downloader.py --login

# Future runs - just run to download new photos
uv run famly_downloader.py
```

First run opens a browser for login and caches your credentials. After that, just run without `--login` to download any new photos.

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
| `--full` | | Fetch all images, ignore last sync timestamp |
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

- **Credentials are cached** in `.famly_credentials.json` in the output directory - just run without arguments after first login
- Access tokens expire periodically; run `--login` again if you get a 401 error
- Existing files are skipped, so you can safely re-run the script
- Downloads highest resolution versions by default

## Publishing Your Archive

Once you've downloaded your photos, you can publish them to various hosting providers.

### Configuration File (Recommended)

Create a config file to store your settings (gitignored by default):

```bash
# Option 1: YAML (requires PyYAML: pip install pyyaml)
cp publish.example.yaml .publish.yaml

# Option 2: JSON (no extra dependencies)
cp publish.example.json .publish.json
```

Example `.publish.yaml`:

```yaml
provider: cloudflare
project_name: my-child-photos

cloudflare:
  account_id: "abc123..."
  api_token: "xyz789..."
  access_emails:
    - you@example.com
    - family@example.com
```

Then just run:

```bash
uv run publish.py
```

### Cloudflare Pages (Recommended)

Deploy to Cloudflare Pages with optional access control:

```bash
# Basic deployment (public)
uv run publish.py --provider cloudflare ./famly_photos

# With access control (requires CLOUDFLARE_API_TOKEN)
uv run publish.py --provider cloudflare \
  --access-emails user@example.com \
  --access-emails family@example.com \
  ./famly_photos

# Custom project name
uv run publish.py --provider cloudflare --project-name my-child-photos ./famly_photos
```

Environment variables:
- `CLOUDFLARE_ACCOUNT_ID` - Your Cloudflare account ID
- `CLOUDFLARE_API_TOKEN` - API token for setting up Access control

### AWS S3

Deploy to an S3 bucket (requires AWS CLI configured):

```bash
# Using environment variable
export S3_BUCKET=my-bucket
uv run publish.py --provider s3 ./famly_photos

# Using command line
uv run publish.py --provider s3 --bucket my-bucket --region eu-west-1 ./famly_photos

# With path prefix
uv run publish.py --provider s3 --bucket my-bucket --prefix photos/famly ./famly_photos
```

### Create Zip File

Create a zip file for manual sharing:

```bash
uv run publish.py --provider zip ./famly_photos
uv run publish.py --provider zip --output-dir ~/Downloads ./famly_photos
```

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

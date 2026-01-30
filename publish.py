#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Publish Famly photo archive to various providers.

Supports multiple deployment targets:
- zip: Create a zip file for manual sharing
- cloudflare: Deploy to Cloudflare Pages with optional Access control
- s3: Deploy to AWS S3 bucket

Configuration can be provided via:
- Command-line arguments (highest priority)
- Environment variables
- Configuration file (.publish.yaml or .publish.json)

Usage:
    # List available providers
    ./publish.py --list-providers

    # Deploy to Cloudflare Pages
    ./publish.py --provider cloudflare ./famly_photos

    # Deploy to Cloudflare Pages with access control
    ./publish.py --provider cloudflare --access-emails user@example.com ./famly_photos

    # Deploy to S3
    ./publish.py --provider s3 --bucket my-bucket ./famly_photos

    # Create a zip file
    ./publish.py --provider zip ./famly_photos

    # Use custom config file
    ./publish.py --config my-config.yaml ./famly_photos
"""

import argparse
import contextlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Default config file locations (searched in order)
DEFAULT_CONFIG_FILES = [".publish.yaml", ".publish.json"]


@dataclass
class PublishConfig:
    """Configuration for publishing."""

    provider: str | None = None
    source_dir: str = "./famly_photos"
    project_name: str = "famly-photos"

    # Cloudflare settings
    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""
    cloudflare_access_emails: list[str] = field(default_factory=list)

    # S3 settings
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_prefix: str = ""
    s3_custom_url: str | None = None

    # Zip settings
    zip_output_dir: str = "."

    @classmethod
    def from_dict(cls, data: dict) -> "PublishConfig":
        """Create config from dictionary.

        Parameters
        ----------
        data : dict
            Configuration dictionary, typically loaded from YAML/JSON.

        Returns
        -------
        PublishConfig
            Populated configuration object.
        """
        config = cls()

        # Top-level settings
        config.provider = data.get("provider", config.provider)
        config.source_dir = data.get("source_dir", config.source_dir)
        config.project_name = data.get("project_name", config.project_name)

        # Cloudflare settings
        if "cloudflare" in data:
            cf = data["cloudflare"]
            config.cloudflare_account_id = cf.get("account_id", config.cloudflare_account_id)
            config.cloudflare_api_token = cf.get("api_token", config.cloudflare_api_token)
            config.cloudflare_access_emails = cf.get(
                "access_emails", config.cloudflare_access_emails
            )

        # S3 settings
        if "s3" in data:
            s3 = data["s3"]
            config.s3_bucket = s3.get("bucket", config.s3_bucket)
            config.s3_region = s3.get("region", config.s3_region)
            config.s3_prefix = s3.get("prefix", config.s3_prefix)
            config.s3_custom_url = s3.get("custom_url", config.s3_custom_url)

        # Zip settings
        if "zip" in data:
            z = data["zip"]
            config.zip_output_dir = z.get("output_dir", config.zip_output_dir)

        return config


def load_config(config_path: Path | None = None) -> PublishConfig:
    """Load configuration from file.

    Searches for config files in the current directory if no path is specified.
    Supports YAML (requires pyyaml) and JSON formats.

    Parameters
    ----------
    config_path : Path | None
        Explicit path to config file, or None to search default locations.

    Returns
    -------
    PublishConfig
        Loaded configuration, or defaults if no config file found.
    """
    config = PublishConfig()

    # Find config file
    if config_path:
        paths_to_try = [config_path]
    else:
        paths_to_try = [Path(f) for f in DEFAULT_CONFIG_FILES]

    config_file = None
    for path in paths_to_try:
        if path.exists():
            config_file = path
            break

    if not config_file:
        return config

    try:
        with open(config_file) as f:
            content = f.read()

        # Try YAML first, fall back to JSON
        data = None
        if config_file.suffix in (".yaml", ".yml"):
            try:
                import yaml

                data = yaml.safe_load(content)
            except ImportError:
                print(
                    f"Warning: PyYAML not installed, cannot read {config_file}",
                    file=sys.stderr,
                )
        elif config_file.suffix == ".json":
            data = json.loads(content)
        else:
            # Try YAML first, then JSON
            try:
                import yaml

                data = yaml.safe_load(content)
            except ImportError:
                with contextlib.suppress(json.JSONDecodeError):
                    data = json.loads(content)

        if data:
            config = PublishConfig.from_dict(data)
            print(f"Loaded config from {config_file}")

    except Exception as e:
        print(f"Warning: Failed to load config from {config_file}: {e}", file=sys.stderr)

    return config


@dataclass
class DeployResult:
    """Result of a deployment operation."""

    success: bool
    provider: str
    message: str
    url: str | None = None
    path: str | None = None


class DeployProvider(ABC):
    """Abstract base class for deployment providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    def deploy(self, source_dir: Path, project_name: str) -> DeployResult:
        """Deploy the source directory.

        Parameters
        ----------
        source_dir : Path
            Path to the directory to deploy.
        project_name : str
            Name for the deployed project.

        Returns
        -------
        DeployResult
            Result with deployment outcome.
        """
        pass


class ZipProvider(DeployProvider):
    """Creates a zip file for manual sharing."""

    def __init__(self, output_dir: str = "."):
        """Initialize with output directory for zip files.

        Parameters
        ----------
        output_dir : str
            Directory where zip files will be created.
        """
        self.output_dir = Path(output_dir)

    @property
    def name(self) -> str:
        return "zip"

    def deploy(self, source_dir: Path, project_name: str) -> DeployResult:
        """Creates a zip file of the photos archive."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        zip_filename = f"{project_name}-{date_str}.zip"
        zip_path = self.output_dir / zip_filename

        try:
            if zip_path.exists():
                zip_path.unlink()

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in source_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(source_dir)
                        zf.write(file_path, arcname)

            return DeployResult(
                success=True,
                provider=self.name,
                message=f"Created zip file: {zip_path}",
                path=str(zip_path),
            )
        except Exception as e:
            return DeployResult(
                success=False,
                provider=self.name,
                message=f"Failed to create zip: {e}",
            )


class S3Provider(DeployProvider):
    """Deploys archive to an AWS S3 bucket.

    Requires the AWS CLI to be installed and configured with appropriate credentials.
    The bucket should be configured for static website hosting if you want public access.
    """

    def __init__(
        self,
        bucket: str = "",
        region: str = "us-east-1",
        prefix: str = "",
        custom_url: str | None = None,
    ):
        """Initialize with S3 configuration.

        Parameters
        ----------
        bucket : str
            S3 bucket name.
        region : str
            AWS region for the bucket.
        prefix : str
            Optional path prefix within bucket.
        custom_url : str | None
            Custom URL for the deployed site (e.g., CloudFront domain).
        """
        self.bucket = bucket or os.environ.get("S3_BUCKET", "")
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.prefix = prefix
        self.custom_url = custom_url

    @property
    def name(self) -> str:
        return "s3"

    def _check_aws_cli(self) -> bool:
        """Checks if AWS CLI is available."""
        try:
            subprocess.run(["aws", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _get_s3_path(self, project_name: str) -> str:
        """Builds the S3 destination path."""
        if self.prefix:
            return f"s3://{self.bucket}/{self.prefix}/{project_name}/"
        return f"s3://{self.bucket}/{project_name}/"

    def _get_url(self, project_name: str) -> str:
        """Builds the public URL for the deployed site."""
        if self.custom_url:
            return self.custom_url

        path = f"{self.prefix}/{project_name}" if self.prefix else project_name
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{path}/index.html"

    def deploy(self, source_dir: Path, project_name: str) -> DeployResult:
        """Syncs files to S3."""
        if not self._check_aws_cli():
            return DeployResult(
                success=False,
                provider=self.name,
                message="AWS CLI not found. Install with: pip install awscli",
            )

        if not self.bucket:
            return DeployResult(
                success=False,
                provider=self.name,
                message="S3 bucket not configured. Set S3_BUCKET env var or use --bucket.",
            )

        s3_path = self._get_s3_path(project_name)

        try:
            cmd = [
                "aws",
                "s3",
                "sync",
                str(source_dir),
                s3_path,
                "--delete",
                "--region",
                self.region,
            ]
            print(f"  Running: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)

            return DeployResult(
                success=True,
                provider=self.name,
                message=f"Deployed to S3: {s3_path}",
                url=self._get_url(project_name),
            )
        except subprocess.CalledProcessError as e:
            return DeployResult(
                success=False,
                provider=self.name,
                message=f"S3 sync failed (exit code {e.returncode})",
            )


class CloudflareProvider(DeployProvider):
    """Deploys to Cloudflare Pages using Wrangler."""

    def __init__(
        self,
        account_id: str = "",
        api_token: str = "",
        access_emails: list[str] | None = None,
    ):
        """Initialize with Cloudflare configuration.

        Parameters
        ----------
        account_id : str
            Cloudflare account ID.
        api_token : str
            Cloudflare API token for Access API.
        access_emails : list[str] | None
            Email addresses to grant access to via Cloudflare Access.
        """
        self.account_id = account_id or os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
        self.api_token = api_token or os.environ.get("CLOUDFLARE_API_TOKEN", "")
        self.access_emails = access_emails or []
        self._account_id_fetched = False

    @property
    def name(self) -> str:
        return "cloudflare"

    def _ensure_account_id(self) -> bool:
        """Ensures account_id is set, fetching from wrangler if needed."""
        if self.account_id:
            return True
        if self._account_id_fetched:
            return bool(self.account_id)

        self._account_id_fetched = True

        try:
            import re

            result = subprocess.run(
                ["npx", "--yes", "wrangler", "whoami"],
                capture_output=True,
                text=True,
                check=True,
            )
            match = re.search(r"\b([a-f0-9]{32})\b", result.stdout)
            if match:
                self.account_id = match.group(1)
                return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        return False

    def _check_wrangler(self) -> bool:
        """Checks if wrangler CLI is available (via npx or directly)."""
        try:
            subprocess.run(
                ["npx", "--yes", "wrangler", "--version"],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        try:
            subprocess.run(
                ["wrangler", "--version"],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _get_env(self) -> dict[str, str]:
        """Gets environment with Cloudflare credentials set."""
        env = os.environ.copy()
        if self.account_id:
            env["CLOUDFLARE_ACCOUNT_ID"] = self.account_id
        return env

    def _project_exists(self, project_name: str) -> bool:
        """Checks if a Pages project exists."""
        cmd = [
            "npx",
            "--yes",
            "wrangler",
            "pages",
            "project",
            "list",
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, env=self._get_env()
            )
            return project_name in result.stdout
        except subprocess.CalledProcessError:
            return False

    def _create_project(self, project_name: str) -> bool:
        """Creates a new Pages project."""
        print(f"  Creating project: {project_name}")
        cmd = [
            "npx",
            "--yes",
            "wrangler",
            "pages",
            "project",
            "create",
            project_name,
            "--production-branch=main",
        ]

        try:
            subprocess.run(cmd, check=True, env=self._get_env())
            return True
        except subprocess.CalledProcessError:
            return False

    def _api_request(self, method: str, endpoint: str, data: dict | None = None) -> dict | None:
        """Makes an authenticated request to the Cloudflare API."""
        if not self.api_token or not self.account_id:
            return None

        url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            print(f"  API error: {e.code} - {error_body}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"  API error: {e}", file=sys.stderr)
            return None

    def _setup_access(self, project_name: str, emails: list[str]) -> bool:
        """Sets up Cloudflare Access for the Pages project.

        Creates an Access application and policy to restrict access to specified emails.
        """
        if not emails:
            return True

        if not self.api_token:
            print(
                "  Warning: No API token configured, skipping Access setup. "
                "Set CLOUDFLARE_API_TOKEN or use --api-token.",
                file=sys.stderr,
            )
            return True

        if not self._ensure_account_id():
            print(
                "  Warning: Could not determine account ID, skipping Access setup. "
                "Set CLOUDFLARE_ACCOUNT_ID or use --account-id.",
                file=sys.stderr,
            )
            return True

        domain = f"{project_name}.pages.dev"
        app_name = f"{project_name}-access"

        print(f"  Setting up Access for {domain} ({len(emails)} email(s))")

        existing_apps = self._api_request("GET", "access/apps")
        if existing_apps and existing_apps.get("success"):
            for app in existing_apps.get("result", []):
                if app.get("name") == app_name:
                    print(f"  Access application already exists: {app_name}")
                    app_id = app["id"]
                    return self._update_access_policy(app_id, emails)

        app_data = {
            "name": app_name,
            "domain": domain,
            "type": "self_hosted",
            "session_duration": "24h",
        }

        result = self._api_request("POST", "access/apps", app_data)
        if not result or not result.get("success"):
            print("  Warning: Failed to create Access application", file=sys.stderr)
            return True

        app_id = result["result"]["id"]

        policy_data = {
            "name": "Email Access",
            "decision": "allow",
            "include": [{"email": {"email": email}} for email in emails],
            "precedence": 1,
        }

        policy_result = self._api_request("POST", f"access/apps/{app_id}/policies", policy_data)
        if not policy_result or not policy_result.get("success"):
            print("  Warning: Failed to create Access policy", file=sys.stderr)
            return True

        print(f"  Access configured for: {', '.join(emails)}")
        return True

    def _update_access_policy(self, app_id: str, emails: list[str]) -> bool:
        """Updates an existing Access application's policy."""
        policies = self._api_request("GET", f"access/apps/{app_id}/policies")
        if not policies or not policies.get("success"):
            return True

        for policy in policies.get("result", []):
            if policy.get("name") == "Email Access":
                policy_id = policy["id"]
                policy_data = {
                    "name": "Email Access",
                    "decision": "allow",
                    "include": [{"email": {"email": email}} for email in emails],
                    "precedence": 1,
                }
                self._api_request("PUT", f"access/apps/{app_id}/policies/{policy_id}", policy_data)
                print(f"  Access policy updated for: {', '.join(emails)}")
                return True

        policy_data = {
            "name": "Email Access",
            "decision": "allow",
            "include": [{"email": {"email": email}} for email in emails],
            "precedence": 1,
        }
        self._api_request("POST", f"access/apps/{app_id}/policies", policy_data)
        print(f"  Access policy created for: {', '.join(emails)}")
        return True

    def deploy(self, source_dir: Path, project_name: str) -> DeployResult:
        """Deploys to Cloudflare Pages."""
        if not self._check_wrangler():
            return DeployResult(
                success=False,
                provider=self.name,
                message="Wrangler/npx not found. Install Node.js or run: npm install -g wrangler",
            )

        # Cloudflare project names must be lowercase, alphanumeric with hyphens
        cf_project_name = project_name.lower().replace("_", "-").replace(" ", "-")

        if not self._project_exists(cf_project_name):
            print(f"  Project '{cf_project_name}' not found, creating...")
            if not self._create_project(cf_project_name):
                return DeployResult(
                    success=False,
                    provider=self.name,
                    message=f"Failed to create project: {cf_project_name}",
                )

        cmd = [
            "npx",
            "--yes",
            "wrangler",
            "pages",
            "deploy",
            str(source_dir),
            "--project-name",
            cf_project_name,
            "--commit-dirty=true",
            "--branch=main",
        ]

        try:
            print(f"  Running: {' '.join(cmd)}")
            subprocess.run(cmd, check=True, env=self._get_env())

            if self.access_emails:
                self._setup_access(cf_project_name, self.access_emails)

            return DeployResult(
                success=True,
                provider=self.name,
                message=f"Deployed to Cloudflare Pages: {cf_project_name}",
                url=f"https://{cf_project_name}.pages.dev",
            )
        except subprocess.CalledProcessError as e:
            return DeployResult(
                success=False,
                provider=self.name,
                message=f"Deployment failed (exit code {e.returncode})",
            )


PROVIDERS: dict[str, type[DeployProvider]] = {
    "zip": ZipProvider,
    "s3": S3Provider,
    "cloudflare": CloudflareProvider,
}


def main(argv: list[str] | None = None) -> int:
    """Main entry point.

    Parameters
    ----------
    argv : list[str] | None
        Command-line arguments (defaults to sys.argv[1:]).

    Returns
    -------
    int
        Exit code (0 for success, non-zero for failure).
    """
    parser = argparse.ArgumentParser(
        description="Publish Famly photo archive to various providers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --provider zip ./famly_photos
  %(prog)s --provider cloudflare --project-name famly-photos ./famly_photos
  %(prog)s --provider cloudflare --access-emails user@example.com ./famly_photos
  %(prog)s --provider s3 --bucket my-bucket ./famly_photos

Configuration file (.publish.yaml):
  provider: cloudflare
  project_name: my-photos
  cloudflare:
    account_id: "abc123..."
    api_token: "xyz789..."
    access_emails:
      - user@example.com
      - family@example.com
  s3:
    bucket: my-bucket
    region: eu-west-1

Providers:
  zip        - Create a zip file for manual sharing
  s3         - Deploy to AWS S3 (requires AWS CLI)
  cloudflare - Deploy to Cloudflare Pages (requires wrangler CLI)

Priority (highest to lowest):
  1. Command-line arguments
  2. Environment variables
  3. Configuration file (.publish.yaml or .publish.json)

Environment variables:
  CLOUDFLARE_ACCOUNT_ID  - Cloudflare account ID
  CLOUDFLARE_API_TOKEN   - Cloudflare API token (for Access setup)
  S3_BUCKET              - S3 bucket name
  AWS_REGION             - AWS region (default: us-east-1)
""",
    )

    parser.add_argument(
        "source_dir",
        nargs="?",
        help="Directory to publish (default: ./famly_photos or from config)",
    )
    parser.add_argument(
        "--provider",
        "-p",
        choices=list(PROVIDERS.keys()),
        help="Deployment provider to use",
    )
    parser.add_argument(
        "--project-name",
        "-n",
        help="Project name for deployment (default: famly-photos)",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        help="Path to config file (default: .publish.yaml or .publish.json)",
    )
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="List available providers and exit",
    )

    # Cloudflare options
    cf_group = parser.add_argument_group("Cloudflare options")
    cf_group.add_argument(
        "--account-id",
        help="Cloudflare account ID (or set CLOUDFLARE_ACCOUNT_ID env var)",
    )
    cf_group.add_argument(
        "--api-token",
        help="Cloudflare API token for Access setup (or set CLOUDFLARE_API_TOKEN)",
    )
    cf_group.add_argument(
        "--access-emails",
        "-e",
        action="append",
        default=[],
        help="Email addresses to grant access via Cloudflare Access (can be repeated)",
    )

    # S3 options
    s3_group = parser.add_argument_group("S3 options")
    s3_group.add_argument(
        "--bucket",
        help="S3 bucket name (or set S3_BUCKET env var)",
    )
    s3_group.add_argument(
        "--region",
        help="AWS region (default: us-east-1)",
    )
    s3_group.add_argument(
        "--prefix",
        help="Path prefix within S3 bucket",
    )
    s3_group.add_argument(
        "--custom-url",
        help="Custom URL for the deployed site (e.g., CloudFront domain)",
    )

    # Zip options
    zip_group = parser.add_argument_group("Zip options")
    zip_group.add_argument(
        "--output-dir",
        help="Directory for zip output (default: current directory)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args(argv)

    if args.list_providers:
        print("Available providers:")
        for name in PROVIDERS:
            print(f"  {name}")
        return 0

    # Load config file
    config = load_config(args.config)

    # Merge: CLI args > config file (env vars handled in provider classes)
    provider_name = args.provider or config.provider
    source_dir_str = args.source_dir or config.source_dir
    project_name = args.project_name or config.project_name

    # Cloudflare settings
    account_id = args.account_id or config.cloudflare_account_id
    api_token = args.api_token or config.cloudflare_api_token
    access_emails = args.access_emails if args.access_emails else config.cloudflare_access_emails

    # S3 settings
    bucket = args.bucket or config.s3_bucket
    region = args.region or config.s3_region
    prefix = args.prefix if args.prefix is not None else config.s3_prefix
    custom_url = args.custom_url or config.s3_custom_url

    # Zip settings
    output_dir = args.output_dir or config.zip_output_dir

    if not provider_name:
        parser.error(
            "--provider is required (use --list-providers to see options, "
            "or set 'provider' in config file)"
        )

    source_dir = Path(source_dir_str)
    if not source_dir.exists():
        print(f"Error: Source directory not found: {source_dir}", file=sys.stderr)
        return 1

    if not source_dir.is_dir():
        print(f"Error: Not a directory: {source_dir}", file=sys.stderr)
        return 1

    # Create provider with merged options
    if provider_name == "zip":
        provider = ZipProvider(output_dir=output_dir)
    elif provider_name == "s3":
        provider = S3Provider(
            bucket=bucket,
            region=region,
            prefix=prefix,
            custom_url=custom_url,
        )
    elif provider_name == "cloudflare":
        provider = CloudflareProvider(
            account_id=account_id,
            api_token=api_token,
            access_emails=access_emails,
        )
    else:
        print(f"Unknown provider: {provider_name}", file=sys.stderr)
        return 1

    print(f"Publishing {source_dir} via {provider.name}...")

    result = provider.deploy(source_dir, project_name)

    if result.success:
        print(f"\n✓ {result.message}")
        if result.url:
            print(f"  URL: {result.url}")
        if result.path:
            print(f"  Path: {result.path}")
        return 0
    else:
        print(f"\n✗ {result.message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

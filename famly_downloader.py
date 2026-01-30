#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.28.0",
#     "tqdm>=4.64.0",
#     "playwright>=1.40.0",
# ]
# ///
"""
Famly Photo Downloader

Downloads all photos tagged with your child from Famly.co

Usage:
    # Run directly with uv (no install needed):
    uv run --with playwright playwright install chromium  # first time only
    uv run famly_downloader.py --login

    # Or with manual install:
    pip install -r requirements.txt
    playwright install chromium
    python famly_downloader.py --login

    # Manual mode (provide credentials):
    python famly_downloader.py --child-id "..." --access-token "..."
"""

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import requests
from tqdm import tqdm

from output_formats import FORMATTERS, get_formatter, get_photos_from_directory

DEFAULT_CONFIG = {
    "output_dir": "./famly_photos",
    "download_big": True,
    "max_workers": 4,
    "batch_size": 100,
}

CONFIG_FILENAME = ".famly_credentials.json"


def load_cached_credentials(output_dir: Path) -> dict | None:
    """
    Load cached credentials from the output directory.

    Parameters
    ----------
    output_dir : Path
        The output directory to look for cached credentials.

    Returns
    -------
    dict | None
        Cached credentials dict or None if not found/invalid.
    """
    config_path = output_dir / CONFIG_FILENAME
    if not config_path.exists():
        return None

    try:
        with open(config_path) as f:
            data = json.load(f)
        if data.get("access_token") and data.get("children"):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


def save_cached_credentials(
    output_dir: Path,
    access_token: str,
    children: list,
    last_sync: dict | None = None,
) -> None:
    """
    Save credentials to the output directory.

    Parameters
    ----------
    output_dir : Path
        The output directory to save credentials to.
    access_token : str
        The Famly API access token.
    children : list
        List of child dictionaries.
    last_sync : dict | None
        Dict mapping child_id to their newest image timestamp.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    config_path = output_dir / CONFIG_FILENAME

    # Preserve existing last_sync data if not provided
    existing_last_sync = {}
    if config_path.exists() and last_sync is None:
        try:
            with open(config_path) as f:
                existing = json.load(f)
                existing_last_sync = existing.get("last_sync", {})
        except (json.JSONDecodeError, OSError):
            pass

    data = {
        "access_token": access_token,
        "children": children,
        "saved_at": datetime.now().isoformat(),
        "last_sync": last_sync if last_sync is not None else existing_last_sync,
    }
    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Credentials cached to {config_path}")


def update_last_sync(output_dir: Path, child_id: str, timestamp: str) -> None:
    """
    Update the last sync timestamp for a child.

    Parameters
    ----------
    output_dir : Path
        The output directory with the config file.
    child_id : str
        The child's ID.
    timestamp : str
        The newest image timestamp.
    """
    config_path = output_dir / CONFIG_FILENAME
    if not config_path.exists():
        return

    try:
        with open(config_path) as f:
            data = json.load(f)

        if "last_sync" not in data:
            data["last_sync"] = {}
        data["last_sync"][child_id] = timestamp

        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)
    except (json.JSONDecodeError, OSError):
        pass


class FamlyBrowserAuth:
    """
    Handles browser-based authentication for Famly.
    Opens a browser window for the user to login, then extracts credentials.
    """

    @staticmethod
    def get_credentials_from_browser() -> dict:
        """
        Open a browser for the user to login and extract credentials.

        Returns
        -------
        dict
            Dictionary with 'access_token' and 'children' (list of child info).
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("\nError: Playwright is required for browser login.")
            print("Install it with: pip install playwright && playwright install chromium")
            sys.exit(1)

        print("\n" + "=" * 60)
        print("Opening browser for Famly login...")
        print("Please log in to your Famly account.")
        print("The browser will close automatically after login.")
        print("=" * 60 + "\n")

        credentials = {"access_token": None, "children": []}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            access_token = None

            def handle_request(request):
                nonlocal access_token
                if "app.famly.co/api" in request.url or "app.famly.co/graphql" in request.url:
                    headers = request.headers
                    if "x-famly-accesstoken" in headers:
                        access_token = headers["x-famly-accesstoken"]

            page.on("request", handle_request)

            page.goto("https://app.famly.co/#/login")

            print("Waiting for login...")
            try:
                page.wait_for_url("**/account/**", timeout=300000)
                time.sleep(2)
            except Exception as e:
                print(f"Timeout or error waiting for login: {e}")

            browser.close()

        if access_token:
            credentials["access_token"] = access_token
            credentials["children"] = FamlyBrowserAuth._fetch_children(access_token)

        return credentials

    @staticmethod
    def _fetch_children(access_token: str) -> list:
        """
        Fetch children list directly from the API.

        Parameters
        ----------
        access_token : str
            The Famly API access token.

        Returns
        -------
        list
            List of child dictionaries with 'id' and 'name'.
        """
        children = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:146.0) Gecko/20100101 Firefox/146.0",
            "Accept": "*/*",
            "x-famly-accesstoken": access_token,
        }

        # Fetch sidebar - children appear as items with type "Famly.Daycare:Child"
        try:
            response = requests.get(
                "https://app.famly.co/api/v2/sidebar",
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                item_type = item.get("type", "")
                if "Child" in item_type:
                    children.append(
                        {
                            "id": item.get("id"),
                            "name": item.get("title", "Unknown"),
                        }
                    )
        except Exception as e:
            print(f"  Warning: Could not fetch children: {e}")

        return children


class FamlyDownloader:
    """
    Downloads photos from Famly.co for a specific child.

    Parameters
    ----------
    child_id : str
        The UUID of the child whose photos to download.
    access_token : str
        The Famly API access token from browser session.
    output_dir : str
        Directory to save downloaded photos.
    download_big : bool
        Whether to download high-resolution versions.
    max_workers : int
        Number of parallel download threads.
    """

    BASE_URL = "https://app.famly.co/api/v2"

    def __init__(
        self,
        child_id: str,
        access_token: str,
        output_dir: str = "./famly_photos",
        download_big: bool = True,
        max_workers: int = 4,
    ):
        self.child_id = child_id
        self.access_token = access_token
        self.output_dir = Path(output_dir)
        self.download_big = download_big
        self.max_workers = max_workers

        self.session = requests.Session()
        self._setup_session()

    def _setup_session(self):
        """Configure the requests session with necessary headers."""
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:146.0) Gecko/20100101 Firefox/146.0",
                "Accept": "*/*",
                "Accept-Language": "en-GB,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://app.famly.co/",
                "content-type": "application/json",
                "x-famly-accesstoken": self.access_token,
                "x-famly-platform": "docker",
            }
        )

    def fetch_image_list(self, older_than: str | None = None, limit: int = 100) -> list:
        """
        Fetch a batch of images from the Famly API.

        Parameters
        ----------
        older_than : str | None
            ISO timestamp for pagination - fetch images older than this.
        limit : int
            Maximum number of images to fetch (max 100).

        Returns
        -------
        list
            List of image metadata dictionaries.
        """
        url = f"{self.BASE_URL}/images/tagged"
        params = {
            "childId": self.child_id,
            "limit": limit,
        }
        if older_than:
            params["olderThan"] = older_than

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def fetch_all_images(self, batch_size: int = 100, stop_at: str | None = None) -> list:
        """
        Fetch all images for the child, handling pagination.

        Parameters
        ----------
        batch_size : int
            Number of images to fetch per request.
        stop_at : str | None
            Stop fetching when reaching images older than this timestamp.

        Returns
        -------
        list
            Complete list of all image metadata.
        """
        all_images = []
        older_than = None
        reached_existing = False

        if stop_at:
            print("Fetching new images since last sync...")
        else:
            print("Fetching all images from Famly...")

        while True:
            batch = self.fetch_image_list(older_than=older_than, limit=batch_size)

            if not batch:
                break

            # Filter out images we've already synced
            if stop_at:
                new_batch = []
                for img in batch:
                    if img.get("createdAt", "") <= stop_at:
                        reached_existing = True
                        break
                    new_batch.append(img)
                batch = new_batch

            if batch:
                all_images.extend(batch)
                print(f"  Found {len(all_images)} new images so far...")

            if reached_existing or len(batch) < batch_size:
                break

            # Use the oldest image's timestamp for the next page
            last_image = batch[-1]
            older_than = last_image.get("createdAt")
            if not older_than:
                break

            time.sleep(0.5)

        if reached_existing:
            print("  Reached previously synced images")
        print(f"Total new images found: {len(all_images)}")
        return all_images

    def fetch_observations(self, first: int = 50, after: str | None = None) -> dict:
        """
        Fetch a batch of observations via GraphQL.

        Parameters
        ----------
        first : int
            Number of observations to fetch per request.
        after : str | None
            Cursor for pagination - fetch observations after this cursor.

        Returns
        -------
        dict
            GraphQL response with 'results' list and 'next' cursor.
        """
        query = """
        query GetObservations($childIds: [ChildId!], $first: Int!, $after: ObservationCursor) {
          childDevelopment {
            observations(childIds: $childIds, first: $first, after: $after) {
              results {
                id
                createdBy { name { fullName } profileImage { url } }
                remark { id date body richTextBody }
                children { id name }
                images { id width height url secret { prefix key path expires } }
                files { id name url }
                videos {
                  ... on TranscodedVideo {
                    id
                    videoUrl
                    thumbnailUrl
                    duration
                    width
                    height
                  }
                }
                behaviors { behaviorId }
                likes {
                  count
                  likedByMe
                  likes {
                    likedBy { name { fullName } }
                    reaction
                  }
                }
                comments {
                  count
                  results {
                    id
                    body
                    sentBy { name { fullName } profileImage { url } }
                    sentAt
                  }
                }
              }
              next
            }
          }
        }
        """
        variables = {
            "childIds": [self.child_id],
            "first": first,
        }
        if after:
            variables["after"] = after

        response = self.session.post(
            "https://app.famly.co/graphql",
            json={"query": query, "variables": variables},
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            raise ValueError(f"GraphQL errors: {data['errors']}")

        return data["data"]["childDevelopment"]["observations"]

    def fetch_all_observations(self, batch_size: int = 50) -> list:
        """
        Fetch all observations for the child with cursor-based pagination.

        Parameters
        ----------
        batch_size : int
            Number of observations to fetch per request.

        Returns
        -------
        list
            Complete list of all observation dictionaries.
        """
        all_observations = []
        cursor = None

        print("Fetching observations from Famly...")

        while True:
            result = self.fetch_observations(first=batch_size, after=cursor)
            batch = result.get("results", [])

            if not batch:
                break

            all_observations.extend(batch)
            print(f"  Found {len(all_observations)} observations so far...")

            cursor = result.get("next")
            if not cursor:
                break

            time.sleep(0.5)

        print(f"Total observations found: {len(all_observations)}")
        return all_observations

    def fetch_conversations(self) -> list[dict]:
        """
        Fetch all conversations from the REST API.

        Returns
        -------
        list[dict]
            List of conversation summaries with conversationId, participants, etc.
        """
        url = "https://app.famly.co/api/v2/conversations"
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.json()

    def fetch_conversation_messages(self, conversation_id: str) -> dict:
        """
        Fetch a single conversation with full message history.

        Parameters
        ----------
        conversation_id : str
            The conversation UUID.

        Returns
        -------
        dict
            Full conversation data including messages array.
        """
        url = f"https://app.famly.co/api/v2/conversations/{conversation_id}"
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.json()

    def _slugify(self, text: str, max_length: int = 30) -> str:
        """
        Convert text to a URL/filesystem-safe slug.

        Parameters
        ----------
        text : str
            Text to convert.
        max_length : int
            Maximum length of the slug.

        Returns
        -------
        str
            Slugified text.
        """
        slug = text.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = slug.strip("-")
        return slug[:max_length].rstrip("-")

    def _get_observation_dir_name(self, observation: dict) -> str:
        """
        Generate a directory name for an observation.

        Parameters
        ----------
        observation : dict
            Observation data from API.

        Returns
        -------
        str
            Directory name in format: YYYY-MM-DD_slug_id
        """
        date = observation.get("remark", {}).get("date", "unknown")
        body = observation.get("remark", {}).get("body", "")
        obs_id = observation.get("id", "unknown")[:8]

        # Get first line or first few words for the slug
        first_line = body.split("\n")[0] if body else "observation"
        slug = self._slugify(first_line)
        if not slug:
            slug = "observation"

        return f"{date}_{slug}_{obs_id}"

    def download_observation_images(self, observation: dict, obs_dir: Path) -> list[Path]:
        """
        Download all images for an observation to obs_dir/img/.

        Parameters
        ----------
        observation : dict
            Observation data from API.
        obs_dir : Path
            Directory for this observation.

        Returns
        -------
        list[Path]
            List of paths to downloaded images.
        """
        images = observation.get("images", [])
        if not images:
            return []

        img_dir = obs_dir / "img"
        img_dir.mkdir(parents=True, exist_ok=True)

        downloaded = []
        for img in images:
            img_id = img.get("id", "unknown")
            url = img.get("url", "")
            if not url:
                continue

            # Determine file extension from URL path
            path = img.get("secret", {}).get("path", "")
            ext = Path(path).suffix if path else ".jpg"
            if not ext:
                ext = ".jpg"

            filename = f"{img_id[:8]}{ext}"
            filepath = img_dir / filename

            if filepath.exists():
                downloaded.append(filepath)
                continue

            try:
                response = self.session.get(url, stream=True, timeout=30)
                response.raise_for_status()

                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                downloaded.append(filepath)
            except Exception as e:
                print(f"  Warning: Failed to download image {img_id[:8]}: {e}")

        return downloaded

    def download_observation_files(self, observation: dict, obs_dir: Path) -> list[Path]:
        """
        Download all file attachments for an observation to obs_dir/files/.

        Parameters
        ----------
        observation : dict
            Observation data from API.
        obs_dir : Path
            Directory for this observation.

        Returns
        -------
        list[Path]
            List of paths to downloaded files.
        """
        files = observation.get("files", [])
        if not files:
            return []

        files_dir = obs_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)

        downloaded = []
        for file in files:
            file_id = file.get("id", "unknown")
            url = file.get("url", "")
            name = file.get("name", f"{file_id}.pdf")
            if not url:
                continue

            filepath = files_dir / name

            if filepath.exists():
                downloaded.append(filepath)
                continue

            try:
                response = self.session.get(url, stream=True, timeout=60)
                response.raise_for_status()

                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                downloaded.append(filepath)
            except Exception as e:
                print(f"  Warning: Failed to download file {name}: {e}")

        return downloaded

    def download_observation_videos(self, observation: dict, obs_dir: Path) -> list[Path]:
        """
        Download all videos for an observation to obs_dir/videos/.

        Parameters
        ----------
        observation : dict
            Observation data from API.
        obs_dir : Path
            Directory for this observation.

        Returns
        -------
        list[Path]
            List of paths to downloaded videos.
        """
        videos = observation.get("videos", [])
        if not videos:
            return []

        videos_dir = obs_dir / "videos"
        videos_dir.mkdir(parents=True, exist_ok=True)

        downloaded = []
        for video in videos:
            video_id = video.get("id", "unknown")
            url = video.get("videoUrl", "")
            if not url:
                continue

            filename = f"{video_id[:8]}.mp4"
            filepath = videos_dir / filename

            if filepath.exists():
                downloaded.append(filepath)
                continue

            try:
                response = self.session.get(url, stream=True, timeout=120)
                response.raise_for_status()

                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                downloaded.append(filepath)
            except Exception as e:
                print(f"  Warning: Failed to download video {video_id[:8]}: {e}")

        return downloaded

    def download_message_images(self, conversation: dict, conv_dir: Path) -> dict[str, list[Path]]:
        """
        Download all images from messages in a conversation.

        Parameters
        ----------
        conversation : dict
            Full conversation data with messages array.
        conv_dir : Path
            Directory for this conversation.

        Returns
        -------
        dict[str, list[Path]]
            Map of messageId to list of downloaded image paths.
        """
        images_dir = conv_dir / "images"
        message_images: dict[str, list[Path]] = {}

        messages = conversation.get("messages", [])
        for msg in messages:
            msg_id = msg.get("messageId", "")
            images = msg.get("images", [])
            if not images:
                continue

            images_dir.mkdir(parents=True, exist_ok=True)
            downloaded = []

            for img in images:
                img_id = img.get("imageId", "unknown")
                prefix = img.get("prefix", "")
                key = img.get("key", "")

                if not prefix or not key:
                    continue

                url = f"{prefix}/{key}"
                filename = f"{img_id[:8]}.jpg"
                filepath = images_dir / filename

                if filepath.exists():
                    downloaded.append(filepath)
                    continue

                try:
                    response = self.session.get(url, stream=True, timeout=60)
                    response.raise_for_status()

                    with open(filepath, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    downloaded.append(filepath)
                except Exception as e:
                    print(f"  Warning: Failed to download message image {img_id[:8]}: {e}")

            if downloaded:
                message_images[msg_id] = downloaded

        return message_images

    def _get_image_url(self, image: dict) -> str:
        """
        Get the best available URL for an image.

        Parameters
        ----------
        image : dict
            Image metadata from API.

        Returns
        -------
        str
            URL to download.
        """
        if self.download_big and "big" in image and image["big"]:
            return image["big"]["url"]
        elif self.download_big and "url_big" in image:
            return image["url_big"]
        elif "thumbnail" in image and image["thumbnail"]:
            return image["thumbnail"]["url"]
        return image.get("url", "")

    def _generate_filename(self, image: dict) -> str:
        """
        Generate a filename for the image based on creation date and ID.

        Parameters
        ----------
        image : dict
            Image metadata from API.

        Returns
        -------
        str
            Generated filename.
        """
        image_id = image.get("imageId", "unknown")
        created_at = image.get("createdAt", "")

        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace("+00:00", "+0000"))
                date_str = dt.strftime("%Y-%m-%d_%H%M%S")
            except ValueError:
                date_str = "unknown_date"
        else:
            date_str = "unknown_date"

        short_id = image_id[:8] if len(image_id) >= 8 else image_id
        return f"{date_str}_{short_id}.jpg"

    def download_image(self, image: dict) -> tuple[bool, str]:
        """
        Download a single image.

        Parameters
        ----------
        image : dict
            Image metadata from API.

        Returns
        -------
        tuple[bool, str]
            Success status and filename or error message.
        """
        url = self._get_image_url(image)
        if not url:
            return False, "No URL available"

        filename = self._generate_filename(image)
        filepath = self.output_dir / filename

        if filepath.exists():
            return True, f"{filename} (skipped, exists)"

        try:
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return True, filename
        except Exception as e:
            return False, str(e)

    def download_all(self, images: list) -> dict:
        """
        Download all images with parallel execution.

        Parameters
        ----------
        images : list
            List of image metadata dictionaries.

        Returns
        -------
        dict
            Statistics about the download operation.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        stats = {"success": 0, "failed": 0, "skipped": 0}
        failed_images = []

        print(f"\nDownloading {len(images)} images to {self.output_dir}")
        print(f"Using {self.max_workers} parallel workers\n")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.download_image, img): img for img in images}

            with tqdm(total=len(images), unit="image") as pbar:
                for future in as_completed(futures):
                    success, result = future.result()

                    if success:
                        if "skipped" in result:
                            stats["skipped"] += 1
                        else:
                            stats["success"] += 1
                    else:
                        stats["failed"] += 1
                        failed_images.append((futures[future], result))

                    pbar.update(1)

        print("\n" + "=" * 50)
        print("Download complete!")
        print(f"  Successfully downloaded: {stats['success']}")
        print(f"  Skipped (already exist): {stats['skipped']}")
        print(f"  Failed: {stats['failed']}")

        if failed_images:
            print("\nFailed downloads:")
            for img, error in failed_images[:10]:
                print(f"  - {img.get('imageId', 'unknown')}: {error}")
            if len(failed_images) > 10:
                print(f"  ... and {len(failed_images) - 10} more")

        return stats


def select_child(children: list) -> dict:
    """
    Let user select a child if multiple are available.

    Parameters
    ----------
    children : list
        List of child dictionaries with 'id' and 'name'.

    Returns
    -------
    dict
        Selected child dictionary.
    """
    if not children:
        return None

    if len(children) == 1:
        return children[0]

    print("\nMultiple children found. Please select one:")
    for i, child in enumerate(children, 1):
        print(f"  {i}. {child['name']} ({child['id'][:8]}...)")

    while True:
        try:
            choice = input("\nEnter number (or 'all' for all children): ").strip()
            if choice.lower() == "all":
                return children
            idx = int(choice) - 1
            if 0 <= idx < len(children):
                return children[idx]
        except (ValueError, KeyboardInterrupt):
            pass
        print("Invalid choice. Please try again.")


def main():
    parser = argparse.ArgumentParser(
        description="Download all photos of your child from Famly.co",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Interactive login (recommended):
    %(prog)s --login

    # Manual credentials:
    %(prog)s --child-id "abc123..." --access-token "xyz789..."
    %(prog)s -c "abc123..." -t "xyz789..." --output ./photos

How to get credentials manually:
    1. Log into https://app.famly.co in your browser
    2. Open DevTools (F12) and go to the Network tab
    3. Navigate to your child's photos/activity page
    4. Look for requests to 'images/tagged' endpoint
    5. From the request headers, copy:
       - childId from the URL parameters
       - x-famly-accesstoken from the headers
        """,
    )

    parser.add_argument(
        "--login",
        "-l",
        action="store_true",
        help="Open browser for interactive login (recommended)",
    )
    parser.add_argument(
        "--child-id",
        "-c",
        default=os.environ.get("FAMLY_CHILD_ID", ""),
        help="Your child's UUID (or set FAMLY_CHILD_ID env var)",
    )
    parser.add_argument(
        "--access-token",
        "-t",
        default=os.environ.get("FAMLY_ACCESS_TOKEN", ""),
        help="Your Famly access token (or set FAMLY_ACCESS_TOKEN env var)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=DEFAULT_CONFIG["output_dir"],
        help="Output directory for downloaded photos",
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=DEFAULT_CONFIG["max_workers"],
        help="Number of parallel download workers",
    )
    parser.add_argument(
        "--thumbnail-only",
        action="store_true",
        help="Download thumbnail versions instead of full resolution",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Fetch all images, ignoring last sync timestamp",
    )
    parser.add_argument("--dry-run", action="store_true", help="List images without downloading")
    parser.add_argument(
        "--observations",
        action="store_true",
        help="Download observations in addition to photos",
    )
    parser.add_argument(
        "--observations-only",
        action="store_true",
        help="Only download observations, skip standalone photos",
    )
    parser.add_argument(
        "--messages",
        action="store_true",
        help="Download messages/conversations",
    )
    parser.add_argument(
        "--gallery",
        action="store_true",
        help="Generate photo gallery (organized by month/year)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=list(FORMATTERS.keys()),
        default="html",
        help="Output format for observations and gallery (default: html)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  Famly Photo Downloader")
    print("=" * 60)

    output_dir = Path(args.output)
    access_token = args.access_token
    child_id = args.child_id
    children_to_download = []
    children = []

    # Try to load cached credentials if not doing fresh login and no manual creds
    if not args.login and not access_token and not child_id:
        cached = load_cached_credentials(output_dir)
        if cached:
            print("\n✓ Using cached credentials")
            access_token = cached["access_token"]
            children = cached["children"]
            print(f"✓ Found {len(children)} cached child(ren)")

    if args.login:
        credentials = FamlyBrowserAuth.get_credentials_from_browser()

        if not credentials.get("access_token"):
            print("\nError: Could not obtain access token from browser.")
            print("Please try again or use manual credentials.")
            sys.exit(1)

        access_token = credentials["access_token"]
        children = credentials.get("children", [])

        print("\n✓ Successfully obtained access token")
        print(f"✓ Found {len(children)} child(ren)")

        # Cache credentials for future runs
        if children:
            save_cached_credentials(output_dir, access_token, children)

    if children:
        selected = select_child(children)
        if isinstance(selected, list):
            children_to_download = selected
        else:
            children_to_download = [selected] if selected else []

    if not children_to_download:
        if args.login or (not access_token and not child_id):
            print("\nNo children found. Please provide --child-id manually.")
            print("You can find the child ID in the URL when viewing their profile:")
            print("  https://app.famly.co/#/account/childProfile/CHILD_ID_HERE/activity")
            child_id = input("\nEnter child ID: ").strip()
            if child_id:
                children_to_download = [{"id": child_id, "name": "Unknown"}]
        elif child_id and access_token:
            children_to_download = [{"id": child_id, "name": "Unknown"}]
        else:
            print(
                "\nNo credentials found. Run with --login or provide --child-id and --access-token"
            )
            print("Run with --help for more information")
            sys.exit(1)

    if not children_to_download:
        print("\nNo child selected. Exiting.")
        sys.exit(1)

    # Load last sync timestamps from cache
    last_sync = {}
    cached = load_cached_credentials(output_dir)
    if cached:
        last_sync = cached.get("last_sync", {})

    for child in children_to_download:
        child_id = child["id"]
        child_name = child.get("name", "Unknown")

        if len(children_to_download) > 1:
            child_output_dir = Path(args.output) / child_name.replace(" ", "_")
        else:
            child_output_dir = Path(args.output)

        print(f"\n{'=' * 60}")
        print(f"Processing: {child_name}")
        print(f"Child ID: {child_id[:8]}...{child_id[-4:]}")
        print(f"Output: {child_output_dir}")
        print("=" * 60)

        downloader = FamlyDownloader(
            child_id=child_id,
            access_token=access_token,
            output_dir=str(child_output_dir),
            download_big=not args.thumbnail_only,
            max_workers=args.workers,
        )

        # Get last sync timestamp for this child (skip if --login or --full)
        stop_at = last_sync.get(child_id) if not (args.login or args.full) else None

        # Track counts for index page
        observations = []
        photos = []

        try:
            # Download photos (unless --observations-only)
            if not args.observations_only:
                print(f"\nResolution: {'Thumbnail' if args.thumbnail_only else 'Full'}")
                images = downloader.fetch_all_images(stop_at=stop_at)

                if not images:
                    print("No new images found for this child.")
                elif args.dry_run:
                    print(f"\nDry run - would download {len(images)} images:")
                    for img in images[:5]:
                        print(f"  - {downloader._generate_filename(img)}")
                    if len(images) > 5:
                        print(f"  ... and {len(images) - 5} more")
                else:
                    downloader.download_all(images)

                    # Update last sync timestamp with newest image
                    if images:
                        newest_timestamp = images[0].get("createdAt")
                        if newest_timestamp:
                            update_last_sync(output_dir, child_id, newest_timestamp)

            # Download observations (if --observations or --observations-only)
            if args.observations or args.observations_only:
                print("\n" + "-" * 40)
                observations = downloader.fetch_all_observations()

                if observations:
                    formatter = get_formatter(args.format)
                    ext = formatter.file_extension
                    obs_dir = child_output_dir / "observations"
                    obs_dir.mkdir(parents=True, exist_ok=True)

                    print(
                        f"\nProcessing {len(observations)} observations (format: {args.format})..."
                    )
                    with tqdm(total=len(observations), unit="obs") as pbar:
                        for obs in observations:
                            # Create observation directory
                            obs_name = downloader._get_observation_dir_name(obs)
                            obs_path = obs_dir / obs_name
                            obs_path.mkdir(parents=True, exist_ok=True)

                            # Download images for this observation
                            image_paths = downloader.download_observation_images(obs, obs_path)

                            # Download file attachments for this observation
                            file_paths = downloader.download_observation_files(obs, obs_path)

                            # Download videos for this observation
                            video_paths = downloader.download_observation_videos(obs, obs_path)

                            # Generate observation output
                            output = formatter.format_observation(
                                obs,
                                image_paths,
                                downloader._get_observation_dir_name,
                                file_paths=file_paths,
                                video_paths=video_paths,
                            )
                            output_file = obs_path / f"index.{ext}"
                            with open(output_file, "w", encoding="utf-8") as f:
                                f.write(output)

                            pbar.update(1)

                    # Generate observations feed index
                    feed_output = formatter.format_observations_feed(
                        observations, downloader._get_observation_dir_name
                    )
                    feed_file = obs_dir / f"index.{ext}"
                    with open(feed_file, "w", encoding="utf-8") as f:
                        f.write(feed_output)

                    print(f"Generated observations feed: {feed_file}")
                else:
                    print("No observations found for this child.")

            # Generate photo gallery (if --gallery)
            photos = []
            if args.gallery:
                print("\n" + "-" * 40)
                print(f"Generating photo gallery (format: {args.format})...")
                formatter = get_formatter(args.format)
                ext = formatter.file_extension
                photos = get_photos_from_directory(child_output_dir)
                if photos:
                    gallery_output = formatter.format_photo_gallery(photos)
                    gallery_file = child_output_dir / f"gallery.{ext}"
                    with open(gallery_file, "w", encoding="utf-8") as f:
                        f.write(gallery_output)
                    print(f"Generated photo gallery: {gallery_file}")
                else:
                    print("No photos found for gallery.")

            # Download messages (if --messages)
            conversations = []
            if args.messages:
                print("\n" + "-" * 40)
                print("Fetching conversations...")
                conversation_summaries = downloader.fetch_conversations()
                print(f"Found {len(conversation_summaries)} conversations")

                if conversation_summaries:
                    formatter = get_formatter(args.format)
                    ext = formatter.file_extension
                    messages_dir = child_output_dir / "messages"
                    messages_dir.mkdir(parents=True, exist_ok=True)

                    print(f"Processing {len(conversation_summaries)} conversations...")
                    for conv_summary in tqdm(
                        conversation_summaries, desc="Conversations", unit="conv"
                    ):
                        conv_id = conv_summary.get("conversationId", "")
                        conv_dir_name = conv_id[:8]
                        conv_dir = messages_dir / conv_dir_name
                        conv_dir.mkdir(parents=True, exist_ok=True)

                        # Fetch full conversation with messages
                        conversation = downloader.fetch_conversation_messages(conv_id)
                        conversations.append(conversation)

                        # Download images from messages
                        message_images = downloader.download_message_images(conversation, conv_dir)

                        # Generate conversation page
                        conv_output = formatter.format_conversation(conversation, message_images)
                        conv_file = conv_dir / f"index.{ext}"
                        with open(conv_file, "w", encoding="utf-8") as f:
                            f.write(conv_output)

                    # Generate conversations index
                    index_output = formatter.format_conversations_index(conversations)
                    index_file = messages_dir / f"index.{ext}"
                    with open(index_file, "w", encoding="utf-8") as f:
                        f.write(index_output)
                    print(f"Generated messages index: {index_file}")

            # Generate main index page
            formatter = get_formatter(args.format)
            ext = formatter.file_extension
            obs_count = len(observations) if observations else 0
            conv_count = len(conversations) if conversations else 0
            if not photos:
                photos = get_photos_from_directory(child_output_dir)
            index_output = formatter.format_index(obs_count, len(photos), conv_count, child_name)
            index_file = child_output_dir / f"index.{ext}"
            with open(index_file, "w", encoding="utf-8") as f:
                f.write(index_output)
            print(f"\nGenerated main index: {index_file}")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("\nError: Authentication failed (401)")
                print("Your access token may have expired. Please run with --login again.")
            elif e.response.status_code == 403:
                print("\nError: Access forbidden (403)")
                print("You may not have permission to access these photos.")
            else:
                print(f"\nHTTP Error: {e}")
        except requests.exceptions.RequestException as e:
            print(f"\nNetwork error: {e}")

    print("\n" + "=" * 60)
    print("All done!")
    print("=" * 60)


if __name__ == "__main__":
    main()

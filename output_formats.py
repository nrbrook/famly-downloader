"""
Output formatters for Famly data.

This module provides different output format implementations for observations
and photo galleries. New formats can be added by subclassing OutputFormatter.
"""

from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Protocol


class ObservationData(Protocol):
    """Protocol for observation data structure from the API."""

    def get(self, key: str, default=None): ...


# Famly-inspired CSS styles for HTML output
FAMLY_CSS = """
:root {
    --famly-purple: #6B4FAA;
    --famly-purple-light: #8B6FCF;
    --famly-purple-dark: #5A3F8F;
    --famly-gray: #f5f5f5;
    --famly-border: #e0e0e0;
    --famly-text: #333;
    --famly-text-light: #666;
}

* {
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    margin: 0;
    padding: 0;
    background: var(--famly-gray);
    color: var(--famly-text);
    line-height: 1.6;
}

.container {
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}

header {
    background: var(--famly-purple);
    color: white;
    padding: 20px;
    margin-bottom: 20px;
}

header h1 {
    margin: 0;
    font-size: 1.5rem;
}

header a {
    color: white;
    text-decoration: none;
}

header a:hover {
    text-decoration: underline;
}

.nav-links {
    margin-top: 10px;
    font-size: 0.9rem;
}

.nav-links a {
    margin-right: 15px;
}

/* Observation card styles */
.observation-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 20px;
    overflow: hidden;
}

.observation-header {
    padding: 15px 20px;
    border-bottom: 1px solid var(--famly-border);
    display: flex;
    align-items: center;
    gap: 12px;
}

.avatar {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    object-fit: cover;
    background: var(--famly-purple-light);
}

.author-info {
    flex: 1;
}

.author-name {
    font-weight: 600;
    color: var(--famly-text);
}

.observation-meta {
    font-size: 0.85rem;
    color: var(--famly-text-light);
}

.observation-body {
    padding: 20px;
}

.observation-body p {
    margin: 0 0 1em 0;
}

.observation-body p:last-child {
    margin-bottom: 0;
}

/* Image gallery in observation */
.observation-images {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 10px;
    padding: 0 20px 20px;
}

.observation-images.single {
    grid-template-columns: 1fr;
}

.observation-images img {
    width: 100%;
    height: auto;
    border-radius: 8px;
    cursor: pointer;
    transition: transform 0.2s;
}

.observation-images img:hover {
    transform: scale(1.02);
}

.observation-images a {
    display: block;
}

.observation-footer {
    padding: 15px 20px;
    border-top: 1px solid var(--famly-border);
    display: flex;
    gap: 20px;
    font-size: 0.9rem;
    color: var(--famly-text-light);
}

.stat {
    display: flex;
    align-items: center;
    gap: 5px;
    position: relative;
    cursor: default;
}

.stat.has-tooltip:hover .tooltip {
    display: block;
}

.tooltip {
    display: none;
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    background: #333;
    color: white;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 0.8rem;
    white-space: nowrap;
    margin-bottom: 8px;
    z-index: 100;
}

.tooltip::after {
    content: '';
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    border: 6px solid transparent;
    border-top-color: #333;
}

/* Videos section */
.videos-section {
    padding: 15px 20px;
}

.video-container {
    margin-bottom: 15px;
}

.video-container:last-child {
    margin-bottom: 0;
}

.video-container video {
    width: 100%;
    max-height: 500px;
    border-radius: 8px;
    background: #000;
}

/* Behaviors/milestones tags */
.behaviors-section {
    padding: 10px 20px 5px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.behavior-tag {
    display: inline-block;
    padding: 4px 12px;
    background: linear-gradient(135deg, var(--famly-purple-light), var(--famly-purple));
    color: white;
    border-radius: 16px;
    font-size: 0.8rem;
    font-weight: 500;
}

/* File attachments */
.files-section {
    padding: 15px 20px;
    border-top: 1px solid var(--famly-border);
}

.files-section h3 {
    font-size: 0.9rem;
    color: var(--famly-text-light);
    margin: 0 0 10px 0;
}

.file-attachment {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: var(--famly-gray);
    border-radius: 8px;
    text-decoration: none;
    color: var(--famly-text);
    font-size: 0.9rem;
    margin-right: 8px;
    margin-bottom: 8px;
    transition: background 0.2s;
}

.file-attachment:hover {
    background: var(--famly-border);
}

.file-icon {
    font-size: 1.2rem;
}

.file-name {
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* Conversations/Messages */
.conversation-header {
    padding: 20px;
    border-bottom: 1px solid var(--famly-border);
    background: var(--famly-bg);
}

.conversation-participants {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}

.participant-chip {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: white;
    border-radius: 20px;
    border: 1px solid var(--famly-border);
}

.participant-chip img {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    object-fit: cover;
}

.conversation-meta {
    margin-top: 10px;
    font-size: 0.85rem;
    color: #666;
}

.messages-list {
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.message {
    display: flex;
    gap: 12px;
    max-width: 85%;
}

.message.from-me {
    align-self: flex-end;
    flex-direction: row-reverse;
}

.message-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
}

.message-content {
    background: white;
    border-radius: 16px;
    padding: 12px 16px;
    border: 1px solid var(--famly-border);
}

.message.from-me .message-content {
    background: var(--famly-purple-light);
    border-color: var(--famly-purple);
}

.message-author {
    font-weight: 600;
    font-size: 0.85rem;
    margin-bottom: 4px;
    color: var(--famly-purple);
}

.message-body {
    line-height: 1.5;
    white-space: pre-wrap;
}

.message-images {
    margin-top: 10px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.message-images img {
    max-width: 200px;
    max-height: 200px;
    border-radius: 8px;
    cursor: pointer;
}

.message-time {
    font-size: 0.75rem;
    color: #888;
    margin-top: 6px;
}

.conversations-list {
    padding: 20px;
}

.conversation-preview {
    display: flex;
    gap: 15px;
    padding: 15px;
    background: white;
    border-radius: 12px;
    border: 1px solid var(--famly-border);
    margin-bottom: 12px;
    text-decoration: none;
    color: inherit;
    transition: transform 0.2s, box-shadow 0.2s;
}

.conversation-preview:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.conversation-preview-avatar {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
}

.conversation-preview-content {
    flex: 1;
    min-width: 0;
}

.conversation-preview-title {
    font-weight: 600;
    margin-bottom: 4px;
}

.conversation-preview-snippet {
    font-size: 0.9rem;
    color: #666;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.conversation-preview-meta {
    font-size: 0.8rem;
    color: #888;
    margin-top: 4px;
}

/* Comments section */
.comments-section {
    padding: 0 20px 20px;
}

.comments-section h3 {
    font-size: 0.95rem;
    color: var(--famly-text-light);
    margin: 0 0 15px 0;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--famly-border);
}

.comment {
    display: flex;
    gap: 12px;
    margin-bottom: 15px;
}

.comment:last-child {
    margin-bottom: 0;
}

.comment .avatar {
    width: 36px;
    height: 36px;
    flex-shrink: 0;
}

.comment-content {
    flex: 1;
    min-width: 0;
}

.comment-header {
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin-bottom: 4px;
}

.comment-author {
    font-weight: 600;
    font-size: 0.9rem;
}

.comment-date {
    font-size: 0.8rem;
    color: var(--famly-text-light);
}

.comment-body {
    font-size: 0.9rem;
    line-height: 1.5;
}

/* Feed index styles */
.feed-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 15px;
    overflow: hidden;
    display: flex;
    text-decoration: none;
    color: inherit;
    transition: box-shadow 0.2s;
}

.feed-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
}

.feed-thumbnail {
    width: 120px;
    height: 120px;
    object-fit: cover;
    flex-shrink: 0;
    background: var(--famly-gray);
}

.feed-content {
    padding: 15px;
    flex: 1;
    min-width: 0;
}

.feed-title {
    font-weight: 600;
    margin-bottom: 5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.feed-preview {
    font-size: 0.9rem;
    color: var(--famly-text-light);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.feed-meta {
    font-size: 0.8rem;
    color: var(--famly-text-light);
    margin-top: 8px;
}

/* Photo gallery styles */
.month-section {
    margin-bottom: 30px;
}

.month-section h2 {
    color: var(--famly-purple);
    border-bottom: 2px solid var(--famly-purple);
    padding-bottom: 10px;
    margin-bottom: 15px;
}

.photo-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 10px;
}

.photo-grid a {
    display: block;
    aspect-ratio: 1;
    overflow: hidden;
    border-radius: 8px;
}

.photo-grid img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.2s;
}

.photo-grid img:hover {
    transform: scale(1.05);
}

/* Gallery with timeline layout */
.gallery-layout {
    display: flex;
    gap: 20px;
}

.gallery-content {
    flex: 1;
    min-width: 0;
}

/* Time Machine-style timeline navigation */
.timeline-nav {
    position: fixed;
    right: 20px;
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
    padding: 10px 0;
    z-index: 100;
}

.timeline-item {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    cursor: pointer;
    padding: 3px 8px;
    border-radius: 4px;
    transition: all 0.15s ease-out;
    transform-origin: right center;
    background: transparent;
}

.timeline-item:hover {
    background: rgba(107, 79, 170, 0.1);
}

.timeline-tick {
    width: 8px;
    height: 2px;
    background: var(--famly-purple);
    opacity: 0.4;
    transition: all 0.15s ease-out;
    border-radius: 1px;
}

.timeline-label {
    font-size: 0;
    opacity: 0;
    margin-right: 8px;
    white-space: nowrap;
    color: var(--famly-purple);
    font-weight: 500;
    transition: all 0.15s ease-out;
}

.timeline-item.active .timeline-tick {
    width: 20px;
    height: 3px;
    opacity: 1;
    background: var(--famly-purple);
}

.timeline-item.active .timeline-label {
    font-size: 0.75rem;
    opacity: 1;
}

/* Time Machine hover expansion effect */
.timeline-nav:hover .timeline-item .timeline-tick {
    width: 12px;
    opacity: 0.6;
}

.timeline-nav:hover .timeline-item .timeline-label {
    font-size: 0.65rem;
    opacity: 0.5;
}

.timeline-nav:hover .timeline-item:hover .timeline-tick {
    width: 24px;
    height: 3px;
    opacity: 1;
}

.timeline-nav:hover .timeline-item:hover .timeline-label {
    font-size: 0.85rem;
    opacity: 1;
}

/* Neighbors of hovered item get medium size */
.timeline-nav:hover .timeline-item.neighbor .timeline-tick {
    width: 16px;
    opacity: 0.8;
}

.timeline-nav:hover .timeline-item.neighbor .timeline-label {
    font-size: 0.7rem;
    opacity: 0.7;
}

/* Second-degree neighbors */
.timeline-nav:hover .timeline-item.neighbor-2 .timeline-tick {
    width: 14px;
    opacity: 0.7;
}

.timeline-nav:hover .timeline-item.neighbor-2 .timeline-label {
    font-size: 0.65rem;
    opacity: 0.6;
}

/* Active item always stays prominent */
.timeline-nav:hover .timeline-item.active .timeline-tick {
    width: 20px;
    opacity: 1;
}

.timeline-nav:hover .timeline-item.active .timeline-label {
    font-size: 0.75rem;
    opacity: 1;
}

/* Year separator in timeline */
.timeline-year {
    font-size: 0.6rem;
    color: var(--famly-text-light);
    padding: 4px 8px;
    margin: 4px 0;
    opacity: 0.6;
}

/* Footer */
.site-footer {
    margin-top: 60px;
    padding: 30px 20px;
    text-align: center;
    color: var(--famly-text-light);
    font-size: 0.85rem;
    border-top: 1px solid var(--famly-border);
}

.site-footer a {
    color: var(--famly-purple);
    text-decoration: none;
}

.site-footer a:hover {
    text-decoration: underline;
}

.site-footer .heart {
    color: #e25555;
}

/* Responsive */
@media (max-width: 600px) {
    .container {
        padding: 10px;
    }

    .feed-card {
        flex-direction: column;
    }

    .feed-thumbnail {
        width: 100%;
        height: 200px;
    }

    .photo-grid {
        grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
    }

    .timeline-nav {
        display: none;
    }
}
"""

FOOTER_HTML = """
    <footer class="site-footer">
        Created with <span class="heart">♥</span> by <a href="https://github.com/nrbrook" target="_blank">Nick Brook</a>
        using <a href="https://github.com/nrbrook/famly-downloader" target="_blank">Famly Downloader</a>
    </footer>
"""


class OutputFormatter(ABC):
    """
    Abstract base class for output formatters.

    Subclass this to implement different output formats (HTML, JSON, etc.).
    """

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """File extension for this format (e.g., 'html', 'json')."""
        ...

    @abstractmethod
    def format_observation(
        self,
        observation: dict,
        image_paths: list[Path],
        dir_name_func: callable,
        file_paths: list[Path] | None = None,
        video_paths: list[Path] | None = None,
    ) -> str:
        """
        Format a single observation.

        Parameters
        ----------
        observation : dict
            Observation data from API.
        image_paths : list[Path]
            List of local paths to downloaded images.
        dir_name_func : callable
            Function to generate directory names for observations.
        file_paths : list[Path] | None
            List of local paths to downloaded file attachments.
        video_paths : list[Path] | None
            List of local paths to downloaded videos.

        Returns
        -------
        str
            Formatted output string.
        """
        ...

    @abstractmethod
    def format_observations_feed(
        self,
        observations: list[dict],
        dir_name_func: callable,
    ) -> str:
        """
        Format the observations feed/index.

        Parameters
        ----------
        observations : list[dict]
            List of observation dictionaries.
        dir_name_func : callable
            Function to generate directory names for observations.

        Returns
        -------
        str
            Formatted output string.
        """
        ...

    @abstractmethod
    def format_photo_gallery(
        self,
        photos: list[Path],
    ) -> str:
        """
        Format the photo gallery.

        Parameters
        ----------
        photos : list[Path]
            List of photo file paths.

        Returns
        -------
        str
            Formatted output string.
        """
        ...

    @abstractmethod
    def format_conversation(
        self,
        conversation: dict,
        message_images: dict[str, list[Path]],
    ) -> str:
        """
        Format a single conversation page.

        Parameters
        ----------
        conversation : dict
            Full conversation data with messages.
        message_images : dict[str, list[Path]]
            Map of messageId to downloaded image paths.

        Returns
        -------
        str
            Formatted output string.
        """
        ...

    @abstractmethod
    def format_conversations_index(
        self,
        conversations: list[dict],
    ) -> str:
        """
        Format the conversations index page.

        Parameters
        ----------
        conversations : list[dict]
            List of conversation summaries.

        Returns
        -------
        str
            Formatted output string.
        """
        ...

    @abstractmethod
    def format_index(
        self,
        observations_count: int,
        photos_count: int,
        conversations_count: int,
        child_name: str = "",
    ) -> str:
        """
        Format the main index page.

        Parameters
        ----------
        observations_count : int
            Total number of observations.
        photos_count : int
            Total number of photos.
        conversations_count : int
            Total number of conversations.
        child_name : str
            Name of the child (for title).

        Returns
        -------
        str
            Formatted output string.
        """
        ...


class HTMLFormatter(OutputFormatter):
    """HTML output formatter with Famly-inspired styling."""

    @property
    def file_extension(self) -> str:
        return "html"

    def format_observation(
        self,
        observation: dict,
        image_paths: list[Path],
        dir_name_func: callable,
        file_paths: list[Path] | None = None,
        video_paths: list[Path] | None = None,
    ) -> str:
        """Generate HTML for a single observation page."""
        remark = observation.get("remark", {})
        date = remark.get("date", "Unknown date")

        # Format date for title
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            formatted_date = dt.strftime("%d %B %Y")
        except ValueError:
            formatted_date = date

        card_html = self._build_observation_card(
            observation,
            dir_name_func,
            image_paths=image_paths,
            file_paths=file_paths,
            video_paths=video_paths,
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Observation - {formatted_date}</title>
    <style>{FAMLY_CSS}</style>
</head>
<body>
    <header>
        <div class="container">
            <h1><a href="../../index.html">Famly Archive</a></h1>
            <div class="nav-links">
                <a href="../../index.html">← Home</a>
                <a href="../index.html">Observations</a>
                <a href="../../gallery.html">Photo Gallery</a>
            </div>
        </div>
    </header>
    <div class="container">
        {card_html}
    </div>{FOOTER_HTML}
</body>
</html>"""

    def _build_observation_card(
        self,
        observation: dict,
        dir_name_func: callable,
        image_paths: list[Path] | None = None,
        file_paths: list[Path] | None = None,
        video_paths: list[Path] | None = None,
        base_path: str = "",
    ) -> str:
        """
        Build HTML for a single observation card.

        Parameters
        ----------
        observation : dict
            Observation data from API.
        dir_name_func : callable
            Function to generate directory names.
        image_paths : list[Path] | None
            If provided, use these actual downloaded image paths. Otherwise,
            construct paths from observation's images metadata.
        file_paths : list[Path] | None
            If provided, use these downloaded file attachment paths. Otherwise,
            construct paths from observation's files metadata.
        video_paths : list[Path] | None
            If provided, use these downloaded video paths. Otherwise,
            construct paths from observation's videos metadata.
        base_path : str
            Base path prefix for URLs when paths are None.

        Returns
        -------
        str
            HTML string for the observation card.
        """
        created_by = observation.get("createdBy") or {}
        author_name = (created_by.get("name") or {}).get("fullName", "Unknown")
        profile_image = created_by.get("profileImage") or {}
        author_image = profile_image.get("url", "")
        remark = observation.get("remark", {})
        date = remark.get("date", "Unknown date")
        body_html = remark.get("richTextBody", "") or remark.get("body", "").replace("\n", "<br>")
        children = observation.get("children", [])
        child_names = ", ".join(c.get("name", "") for c in children)
        images = observation.get("images", [])
        files = observation.get("files", [])
        videos = observation.get("videos", [])
        behaviors = observation.get("behaviors", [])

        # Get likes data
        likes_data = observation.get("likes", {})
        likes_count = likes_data.get("count", 0)
        likes_list = likes_data.get("likes", [])

        # Get comments data
        comments_data = observation.get("comments", {})
        comments_count = comments_data.get("count", 0)
        comments_list = comments_data.get("results", [])

        # Format date nicely
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            formatted_date = dt.strftime("%d %B %Y")
        except ValueError:
            formatted_date = date

        # Build image gallery HTML
        images_html = ""
        if image_paths:
            # Use actual downloaded image paths
            single_class = "single" if len(image_paths) == 1 else ""
            images_html = f'<div class="observation-images {single_class}">'
            for img_path in image_paths:
                rel_path = f"img/{img_path.name}"
                images_html += f'<a href="{rel_path}" target="_blank"><img src="{rel_path}" alt="Observation image"></a>'
            images_html += "</div>"
        elif images:
            # Construct paths from observation metadata
            dir_name = dir_name_func(observation)
            single_class = "single" if len(images) == 1 else ""
            images_html = f'<div class="observation-images {single_class}">'
            for img in images:
                img_id = img.get("id", "")[:8]
                path = img.get("secret", {}).get("path", "")
                ext = Path(path).suffix if path else ".jpg"
                rel_path = f"{base_path}{dir_name}/img/{img_id}{ext}"
                images_html += f'<a href="{rel_path}" target="_blank"><img src="{rel_path}" alt="Observation image"></a>'
            images_html += "</div>"

        # Build files section HTML
        files_html = ""
        if file_paths:
            # Use actual downloaded file paths
            files_html = '<div class="files-section"><h3>Attachments</h3>'
            for fp in file_paths:
                rel_path = f"files/{fp.name}"
                icon = "📄" if fp.suffix.lower() == ".pdf" else "📎"
                files_html += f'<a class="file-attachment" href="{rel_path}" target="_blank"><span class="file-icon">{icon}</span><span class="file-name">{fp.name}</span></a>'
            files_html += "</div>"
        elif files:
            # Construct paths from observation metadata
            dir_name = dir_name_func(observation)
            files_html = '<div class="files-section"><h3>Attachments</h3>'
            for f in files:
                name = f.get("name", "file")
                ext = Path(name).suffix.lower()
                icon = "📄" if ext == ".pdf" else "📎"
                rel_path = f"{base_path}{dir_name}/files/{name}"
                files_html += f'<a class="file-attachment" href="{rel_path}" target="_blank"><span class="file-icon">{icon}</span><span class="file-name">{name}</span></a>'
            files_html += "</div>"

        # Build videos section HTML
        videos_html = ""
        if video_paths:
            videos_html = '<div class="videos-section">'
            for vp in video_paths:
                rel_path = f"videos/{vp.name}"
                videos_html += f"""
            <div class="video-container">
                <video controls preload="metadata">
                    <source src="{rel_path}" type="video/mp4">
                    Your browser does not support video playback.
                </video>
            </div>"""
            videos_html += "</div>"
        elif videos:
            dir_name = dir_name_func(observation)
            videos_html = '<div class="videos-section">'
            for v in videos:
                video_id = v.get("id", "")[:8]
                rel_path = f"{base_path}{dir_name}/videos/{video_id}.mp4"
                videos_html += f"""
            <div class="video-container">
                <video controls preload="metadata">
                    <source src="{rel_path}" type="video/mp4">
                    Your browser does not support video playback.
                </video>
            </div>"""
            videos_html += "</div>"

        # Build behaviors/milestones section HTML
        behaviors_html = ""
        if behaviors:
            behavior_ids = [b.get("behaviorId", "") for b in behaviors if b.get("behaviorId")]
            if behavior_ids:
                behaviors_html = '<div class="behaviors-section">'
                for bid in behavior_ids:
                    behaviors_html += f'<span class="behavior-tag">{bid}</span>'
                behaviors_html += "</div>"

        # Avatar HTML
        avatar_html = (
            f'<img class="avatar" src="{author_image}" alt="">'
            if author_image
            else '<div class="avatar"></div>'
        )

        # Build likes tooltip HTML
        likes_tooltip = ""
        if likes_list:
            likers = []
            for like in likes_list:
                liker_name = (like.get("likedBy") or {}).get("name", {}).get("fullName", "Someone")
                reaction = like.get("reaction", "💜")
                likers.append(f"{reaction} {liker_name}")
            likes_tooltip = f'<span class="tooltip">{", ".join(likers)}</span>'

        has_tooltip_class = "has-tooltip" if likes_list else ""

        # Build comments section HTML
        comments_html = ""
        if comments_list:
            comments_html = '<div class="comments-section"><h3>Comments</h3>'
            for comment in comments_list:
                comment_author = (
                    (comment.get("sentBy") or {}).get("name", {}).get("fullName", "Unknown")
                )
                comment_avatar_url = ((comment.get("sentBy") or {}).get("profileImage") or {}).get(
                    "url", ""
                )
                comment_body = comment.get("body", "")
                comment_date = comment.get("sentAt", "")

                # Format comment date
                try:
                    comment_dt = datetime.fromisoformat(comment_date.replace("Z", "+00:00"))
                    comment_date_formatted = comment_dt.strftime("%d %b %Y, %H:%M")
                except (ValueError, AttributeError):
                    comment_date_formatted = ""

                comment_avatar = (
                    f'<img class="avatar" src="{comment_avatar_url}" alt="">'
                    if comment_avatar_url
                    else '<div class="avatar"></div>'
                )

                comments_html += f"""
            <div class="comment">
                {comment_avatar}
                <div class="comment-content">
                    <div class="comment-header">
                        <span class="comment-author">{comment_author}</span>
                        <span class="comment-date">{comment_date_formatted}</span>
                    </div>
                    <div class="comment-body">{comment_body}</div>
                </div>
            </div>"""
            comments_html += "</div>"

        return f"""
        <div class="observation-card">
            <div class="observation-header">
                {avatar_html}
                <div class="author-info">
                    <div class="author-name">{author_name}</div>
                    <div class="observation-meta">{formatted_date} · For {child_names}</div>
                </div>
            </div>
            <div class="observation-body">
                {body_html}
            </div>
            {behaviors_html}
            {images_html}
            {videos_html}
            {files_html}
            {comments_html}
            <div class="observation-footer">
                <span class="stat {has_tooltip_class}">💜 {likes_count} like{"s" if likes_count != 1 else ""}{likes_tooltip}</span>
                <span class="stat">💬 {comments_count} comment{"s" if comments_count != 1 else ""}</span>
            </div>
        </div>"""

    def format_observations_feed(
        self,
        observations: list[dict],
        dir_name_func: callable,
    ) -> str:
        """Generate HTML for the observations feed/index page."""
        # Group observations by month
        obs_by_month: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for obs in observations:
            remark = obs.get("remark", {})
            date = remark.get("date", "")
            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
                month_key = dt.strftime("%Y-%m")
                month_label = dt.strftime("%B %Y")
                obs_by_month[(month_key, month_label)].append(obs)
            except ValueError:
                obs_by_month[("0000-00", "Other")].append(obs)

        # Sort months descending (newest first)
        sorted_months = sorted(obs_by_month.keys(), reverse=True)

        # Build sections HTML and timeline nav
        sections_html = ""
        timeline_html = ""
        prev_year = None

        for month_key, month_label in sorted_months:
            month_observations = obs_by_month[(month_key, month_label)]

            # Build cards for this month
            cards_html = ""
            for obs in month_observations:
                cards_html += self._build_observation_card(obs, dir_name_func, base_path="")

            sections_html += f"""
        <div class="month-section" id="month-{month_key}" data-month="{month_key}">
            <h2>{month_label}</h2>
            {cards_html}
        </div>"""

            # Timeline navigation item
            year = month_key.split("-")[0]
            short_month = month_label.split()[0][:3]

            if prev_year is not None and year != prev_year:
                timeline_html += f'<div class="timeline-year">{prev_year}</div>'
            prev_year = year

            timeline_html += f"""
            <div class="timeline-item" data-target="month-{month_key}">
                <span class="timeline-label">{short_month} {year}</span>
                <span class="timeline-tick"></span>
            </div>"""

        if prev_year:
            timeline_html += f'<div class="timeline-year">{prev_year}</div>'

        timeline_js = """
<script>
(function() {
    const items = document.querySelectorAll('.timeline-item');
    const sections = document.querySelectorAll('.month-section');

    // Click to scroll
    items.forEach(item => {
        item.addEventListener('click', () => {
            const target = document.getElementById(item.dataset.target);
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // Hover neighbor effect
    items.forEach((item, index) => {
        item.addEventListener('mouseenter', () => {
            items.forEach((other, otherIndex) => {
                other.classList.remove('neighbor', 'neighbor-2');
                const distance = Math.abs(otherIndex - index);
                if (distance === 1) other.classList.add('neighbor');
                else if (distance === 2) other.classList.add('neighbor-2');
            });
        });
        item.addEventListener('mouseleave', () => {
            items.forEach(other => other.classList.remove('neighbor', 'neighbor-2'));
        });
    });

    // Scroll tracking
    function updateActiveMonth() {
        const windowHeight = window.innerHeight;
        let activeSection = null;

        sections.forEach(section => {
            const rect = section.getBoundingClientRect();
            if (rect.top <= windowHeight / 3 && rect.bottom > 0) {
                activeSection = section;
            }
        });

        items.forEach(item => {
            item.classList.remove('active');
            if (activeSection && item.dataset.target === activeSection.id) {
                item.classList.add('active');
            }
        });
    }

    window.addEventListener('scroll', updateActiveMonth, { passive: true });
    updateActiveMonth();
})();
</script>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Observations Feed</title>
    <style>{FAMLY_CSS}</style>
</head>
<body>
    <header>
        <div class="container">
            <h1><a href="../index.html">Famly Archive</a></h1>
            <div class="nav-links">
                <a href="../index.html">← Home</a>
                <a href="../gallery.html">Photo Gallery</a>
            </div>
        </div>
    </header>
    <nav class="timeline-nav">
        {timeline_html}
    </nav>
    <div class="container">
        {sections_html}
    </div>{FOOTER_HTML}
    {timeline_js}
</body>
</html>"""

    def format_photo_gallery(self, photos: list[Path]) -> str:
        """Generate HTML for the photo gallery organized by month/year."""
        if not photos:
            return ""

        # Group photos by month/year based on filename (YYYY-MM-DD_HHMMSS_id.jpg)
        photos_by_month: dict[tuple[str, str], list[Path]] = defaultdict(list)
        for photo in photos:
            name = photo.stem
            try:
                date_part = name.split("_")[0]
                dt = datetime.strptime(date_part, "%Y-%m-%d")
                month_key = dt.strftime("%Y-%m")
                month_label = dt.strftime("%B %Y")
                photos_by_month[(month_key, month_label)].append(photo)
            except (ValueError, IndexError):
                photos_by_month[("0000-00", "Other")].append(photo)

        # Sort months descending (newest first)
        sorted_months = sorted(photos_by_month.keys(), reverse=True)

        # Build sections HTML and timeline nav items
        sections_html = ""
        timeline_html = ""
        prev_year = None

        for month_key, month_label in sorted_months:
            month_photos = sorted(photos_by_month[(month_key, month_label)], reverse=True)
            photos_html = ""
            for photo in month_photos:
                photos_html += f"""
                <a href="{photo.name}" target="_blank">
                    <img src="{photo.name}" alt="{photo.stem}" loading="lazy">
                </a>"""

            # Use month_key as section ID
            sections_html += f"""
        <div class="month-section" id="month-{month_key}" data-month="{month_key}">
            <h2>{month_label}</h2>
            <div class="photo-grid">
                {photos_html}
            </div>
        </div>"""

            # Extract year and short month for timeline
            year = month_key.split("-")[0]
            short_month = month_label.split()[0][:3]  # "January" -> "Jan"

            # Add year separator if year changed
            if prev_year is not None and year != prev_year:
                timeline_html += f'<div class="timeline-year">{prev_year}</div>'
            prev_year = year

            timeline_html += f"""
            <div class="timeline-item" data-target="month-{month_key}">
                <span class="timeline-label">{short_month} {year}</span>
                <span class="timeline-tick"></span>
            </div>"""

        # Add final year label
        if prev_year:
            timeline_html += f'<div class="timeline-year">{prev_year}</div>'

        timeline_js = """
<script>
(function() {
    const nav = document.querySelector('.timeline-nav');
    const items = document.querySelectorAll('.timeline-item');
    const sections = document.querySelectorAll('.month-section');

    // Click to scroll
    items.forEach(item => {
        item.addEventListener('click', () => {
            const targetId = item.dataset.target;
            const target = document.getElementById(targetId);
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // Hover neighbor effect
    items.forEach((item, index) => {
        item.addEventListener('mouseenter', () => {
            items.forEach((other, otherIndex) => {
                other.classList.remove('neighbor', 'neighbor-2');
                const distance = Math.abs(otherIndex - index);
                if (distance === 1) other.classList.add('neighbor');
                else if (distance === 2) other.classList.add('neighbor-2');
            });
        });
        item.addEventListener('mouseleave', () => {
            items.forEach(other => other.classList.remove('neighbor', 'neighbor-2'));
        });
    });

    // Scroll tracking
    function updateActiveMonth() {
        const scrollTop = window.scrollY;
        const windowHeight = window.innerHeight;
        let activeSection = null;

        sections.forEach(section => {
            const rect = section.getBoundingClientRect();
            // Section is active if it's in the top half of the viewport
            if (rect.top <= windowHeight / 3 && rect.bottom > 0) {
                activeSection = section;
            }
        });

        items.forEach(item => {
            item.classList.remove('active');
            if (activeSection && item.dataset.target === activeSection.id) {
                item.classList.add('active');
            }
        });
    }

    window.addEventListener('scroll', updateActiveMonth, { passive: true });
    updateActiveMonth();
})();
</script>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Photo Gallery</title>
    <style>{FAMLY_CSS}</style>
</head>
<body>
    <header>
        <div class="container">
            <h1><a href="index.html">Famly Archive</a></h1>
            <div class="nav-links">
                <a href="index.html">← Home</a>
                <a href="observations/index.html">Observations</a>
            </div>
        </div>
    </header>
    <nav class="timeline-nav">
        {timeline_html}
    </nav>
    <div class="container">
        {sections_html}
    </div>{FOOTER_HTML}
    {timeline_js}
</body>
</html>"""

    def format_conversation(
        self,
        conversation: dict,
        message_images: dict[str, list[Path]],
    ) -> str:
        """Generate HTML for a single conversation page."""
        participants = conversation.get("participants", [])
        messages = conversation.get("messages", [])
        title = conversation.get("title") or " & ".join(
            p.get("title", "Unknown") for p in participants[:2]
        )

        # Build participants chips
        participants_html = ""
        for p in participants:
            img = p.get("image", "")
            name = p.get("title", "Unknown")
            img_html = f'<img src="{img}" alt="">' if img else ""
            participants_html += f'<span class="participant-chip">{img_html}{name}</span>'

        # Build messages HTML
        messages_html = ""
        for msg in messages:
            msg_id = msg.get("messageId", "")
            body = msg.get("body", "")
            author = msg.get("author", {})
            author_name = author.get("title", "Unknown")
            author_img = author.get("image", "")
            is_me = author.get("me", False)
            sent_at = msg.get("createdAt", "")

            # Format timestamp
            try:
                from datetime import datetime

                dt = datetime.fromisoformat(sent_at.replace("+00:00", "+00:00"))
                time_str = dt.strftime("%d %b %Y, %H:%M")
            except (ValueError, AttributeError):
                time_str = sent_at

            # Avatar
            avatar_html = (
                f'<img class="message-avatar" src="{author_img}" alt="">'
                if author_img
                else '<div class="message-avatar"></div>'
            )

            # Images attached to this message
            images_html = ""
            if msg_id in message_images:
                images_html = '<div class="message-images">'
                for img_path in message_images[msg_id]:
                    images_html += f'<img src="images/{img_path.name}" alt="Attached image">'
                images_html += "</div>"

            me_class = " from-me" if is_me else ""
            messages_html += f"""
            <div class="message{me_class}">
                {avatar_html}
                <div class="message-content">
                    <div class="message-author">{author_name}</div>
                    <div class="message-body">{body}</div>
                    {images_html}
                    <div class="message-time">{time_str}</div>
                </div>
            </div>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Messages</title>
    <style>{FAMLY_CSS}</style>
</head>
<body>
    <header>
        <a href="../index.html" class="back-link">← Home</a>
        <a href="index.html" class="back-link">Messages</a>
    </header>
    <div class="container">
        <div class="observation-card">
            <div class="conversation-header">
                <div class="conversation-participants">
                    {participants_html}
                </div>
                <div class="conversation-meta">
                    {len(messages)} messages
                </div>
            </div>
            <div class="messages-list">
                {messages_html}
            </div>
        </div>
    </div>{FOOTER_HTML}
</body>
</html>"""

    def format_conversations_index(
        self,
        conversations: list[dict],
    ) -> str:
        """Generate HTML for the conversations index page."""
        # Build conversation previews
        previews_html = ""
        for conv in conversations:
            conv_id = conv.get("conversationId", "")[:8]
            participants = conv.get("participants", [])
            title = conv.get("title") or " & ".join(
                p.get("title", "Unknown") for p in participants[:2]
            )
            last_msg = conv.get("lastMessage", {})
            preview = last_msg.get("body", "")[:80]
            if len(last_msg.get("body", "")) > 80:
                preview += "..."
            last_activity = conv.get("lastActivityAt", "")

            # Format date
            try:
                from datetime import datetime

                dt = datetime.fromisoformat(last_activity.replace("+00:00", "+00:00"))
                date_str = dt.strftime("%d %b %Y")
            except (ValueError, AttributeError):
                date_str = last_activity

            # Get avatar from first participant
            avatar = ""
            if participants:
                avatar = participants[0].get("image", "")
            avatar_html = (
                f'<img class="conversation-preview-avatar" src="{avatar}" alt="">'
                if avatar
                else '<div class="conversation-preview-avatar"></div>'
            )

            previews_html += f"""
            <a href="{conv_id}/index.html" class="conversation-preview">
                {avatar_html}
                <div class="conversation-preview-content">
                    <div class="conversation-preview-title">{title}</div>
                    <div class="conversation-preview-snippet">{preview}</div>
                    <div class="conversation-preview-meta">{date_str}</div>
                </div>
            </a>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Messages</title>
    <style>{FAMLY_CSS}</style>
</head>
<body>
    <header>
        <a href="../index.html" class="back-link">← Home</a>
        <span class="header-title">Messages</span>
    </header>
    <div class="container">
        <div class="conversations-list">
            {previews_html}
        </div>
    </div>{FOOTER_HTML}
</body>
</html>"""

    def format_index(
        self,
        observations_count: int,
        photos_count: int,
        conversations_count: int,
        child_name: str = "",
    ) -> str:
        """Generate HTML for the main index page."""
        title = f"{child_name}'s Famly Archive" if child_name else "Famly Archive"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>{FAMLY_CSS}
    .index-hero {{
        text-align: center;
        padding: 60px 20px;
        background: linear-gradient(135deg, var(--famly-purple) 0%, var(--famly-purple-light) 100%);
        color: white;
        margin: -20px -20px 30px -20px;
        border-radius: 0 0 20px 20px;
    }}
    .index-hero h1 {{
        font-size: 2.5rem;
        margin: 0 0 10px 0;
    }}
    .index-hero p {{
        font-size: 1.1rem;
        opacity: 0.9;
        margin: 0;
    }}
    .index-cards {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 20px;
        margin-top: 20px;
    }}
    .index-card {{
        background: white;
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        padding: 30px;
        text-decoration: none;
        color: inherit;
        transition: transform 0.2s, box-shadow 0.2s;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
    }}
    .index-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    }}
    .index-card-icon {{
        font-size: 3rem;
        margin-bottom: 15px;
    }}
    .index-card-title {{
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 8px;
        color: var(--famly-purple);
    }}
    .index-card-count {{
        font-size: 2rem;
        font-weight: 700;
        color: var(--famly-purple);
        margin-bottom: 5px;
    }}
    .index-card-label {{
        font-size: 0.9rem;
        color: var(--famly-text-light);
    }}
    </style>
</head>
<body>
    <div class="container">
        <div class="index-hero">
            <h1>{title}</h1>
            <p>Photos and observations from nursery</p>
        </div>
        <div class="index-cards">
            <a class="index-card" href="observations/index.html">
                <span class="index-card-icon">📝</span>
                <span class="index-card-title">Observations</span>
                <span class="index-card-count">{observations_count}</span>
                <span class="index-card-label">observations</span>
            </a>
            <a class="index-card" href="gallery.html">
                <span class="index-card-icon">📷</span>
                <span class="index-card-title">Photo Gallery</span>
                <span class="index-card-count">{photos_count}</span>
                <span class="index-card-label">photos</span>
            </a>
            <a class="index-card" href="messages/index.html">
                <span class="index-card-icon">💬</span>
                <span class="index-card-title">Messages</span>
                <span class="index-card-count">{conversations_count}</span>
                <span class="index-card-label">conversations</span>
            </a>
        </div>
    </div>{FOOTER_HTML}
</body>
</html>"""


class JSONFormatter(OutputFormatter):
    """JSON output formatter for structured data export."""

    @property
    def file_extension(self) -> str:
        return "json"

    def format_observation(
        self,
        observation: dict,
        image_paths: list[Path],
        dir_name_func: callable,
        file_paths: list[Path] | None = None,
        video_paths: list[Path] | None = None,
    ) -> str:
        """Generate JSON for a single observation."""
        import json

        created_by = observation.get("createdBy") or {}
        remark = observation.get("remark", {})
        children = observation.get("children", [])
        likes_data = observation.get("likes", {})
        comments_data = observation.get("comments", {})
        files_data = observation.get("files", [])
        videos_data = observation.get("videos", [])
        behaviors_data = observation.get("behaviors", [])
        file_paths = file_paths or []
        video_paths = video_paths or []

        data = {
            "id": observation.get("id"),
            "date": remark.get("date"),
            "author": {
                "name": (created_by.get("name") or {}).get("fullName", "Unknown"),
                "profileImage": (created_by.get("profileImage") or {}).get("url"),
            },
            "children": [{"id": c.get("id"), "name": c.get("name")} for c in children],
            "content": {
                "body": remark.get("body", ""),
                "richTextBody": remark.get("richTextBody"),
            },
            "behaviors": [b.get("behaviorId") for b in behaviors_data if b.get("behaviorId")],
            "images": [
                {
                    "id": img.get("id"),
                    "localPath": f"img/{Path(p).name}" if p else None,
                    "width": img.get("width"),
                    "height": img.get("height"),
                }
                for img, p in zip(
                    observation.get("images", []),
                    [*image_paths, *[None] * 100],
                    strict=False,  # Pad with None for undownloaded
                )
            ][: len(observation.get("images", []))],
            "videos": [
                {
                    "id": v.get("id"),
                    "localPath": f"videos/{Path(p).name}" if p else None,
                    "duration": v.get("duration"),
                    "width": v.get("width"),
                    "height": v.get("height"),
                }
                for v, p in zip(
                    videos_data,
                    [*video_paths, *[None] * 100],
                    strict=False,
                )
            ][: len(videos_data)],
            "files": [
                {
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "localPath": f"files/{Path(p).name}" if p else None,
                }
                for f, p in zip(
                    files_data,
                    [*file_paths, *[None] * 100],
                    strict=False,
                )
            ][: len(files_data)],
            "likes": {
                "count": likes_data.get("count", 0),
                "likers": [
                    {
                        "name": (like.get("likedBy") or {})
                        .get("name", {})
                        .get("fullName", "Unknown"),
                        "reaction": like.get("reaction"),
                    }
                    for like in likes_data.get("likes", [])
                ],
            },
            "comments": {
                "count": comments_data.get("count", 0),
                "items": [
                    {
                        "id": c.get("id"),
                        "body": c.get("body", ""),
                        "author": (c.get("sentBy") or {})
                        .get("name", {})
                        .get("fullName", "Unknown"),
                        "authorImage": ((c.get("sentBy") or {}).get("profileImage") or {}).get(
                            "url"
                        ),
                        "sentAt": c.get("sentAt"),
                    }
                    for c in comments_data.get("results", [])
                ],
            },
        }

        return json.dumps(data, indent=2, ensure_ascii=False)

    def format_observations_feed(
        self,
        observations: list[dict],
        dir_name_func: callable,
    ) -> str:
        """Generate JSON for the observations feed/index."""
        import json

        feed_data = {
            "type": "observations_feed",
            "count": len(observations),
            "observations": [],
        }

        for obs in observations:
            created_by = obs.get("createdBy") or {}
            remark = obs.get("remark", {})
            children = obs.get("children", [])
            images = obs.get("images", [])

            obs_data = {
                "id": obs.get("id"),
                "date": remark.get("date"),
                "author": (created_by.get("name") or {}).get("fullName", "Unknown"),
                "children": [c.get("name") for c in children],
                "preview": remark.get("body", "")[:150],
                "imageCount": len(images),
                "likes": obs.get("likes", {}).get("count", 0),
                "comments": obs.get("comments", {}).get("count", 0),
                "directory": dir_name_func(obs),
            }
            feed_data["observations"].append(obs_data)

        return json.dumps(feed_data, indent=2, ensure_ascii=False)

    def format_photo_gallery(self, photos: list[Path]) -> str:
        """Generate JSON for the photo gallery."""
        import json

        if not photos:
            return json.dumps({"type": "photo_gallery", "count": 0, "months": []})

        # Group photos by month/year
        photos_by_month: dict[tuple[str, str], list[Path]] = defaultdict(list)
        for photo in photos:
            name = photo.stem
            try:
                date_part = name.split("_")[0]
                dt = datetime.strptime(date_part, "%Y-%m-%d")
                month_key = dt.strftime("%Y-%m")
                month_label = dt.strftime("%B %Y")
                photos_by_month[(month_key, month_label)].append(photo)
            except (ValueError, IndexError):
                photos_by_month[("0000-00", "Other")].append(photo)

        # Sort months descending
        sorted_months = sorted(photos_by_month.keys(), reverse=True)

        gallery_data = {
            "type": "photo_gallery",
            "count": len(photos),
            "months": [],
        }

        for month_key, month_label in sorted_months:
            month_photos = sorted(photos_by_month[(month_key, month_label)], reverse=True)
            month_data = {
                "key": month_key,
                "label": month_label,
                "count": len(month_photos),
                "photos": [
                    {
                        "filename": p.name,
                        "date": p.stem.split("_")[0] if "_" in p.stem else None,
                    }
                    for p in month_photos
                ],
            }
            gallery_data["months"].append(month_data)

        return json.dumps(gallery_data, indent=2, ensure_ascii=False)

    def format_conversation(
        self,
        conversation: dict,
        message_images: dict[str, list[Path]],
    ) -> str:
        """Generate JSON for a single conversation."""
        import json

        participants = conversation.get("participants", [])
        messages = conversation.get("messages", [])

        data = {
            "type": "conversation",
            "id": conversation.get("conversationId"),
            "title": conversation.get("title"),
            "createdAt": conversation.get("createdAt"),
            "lastActivityAt": conversation.get("lastActivityAt"),
            "participants": [
                {
                    "id": p.get("id"),
                    "title": p.get("title"),
                    "subtitle": p.get("subtitle"),
                    "image": p.get("image"),
                }
                for p in participants
            ],
            "messages": [
                {
                    "id": msg.get("messageId"),
                    "body": msg.get("body"),
                    "author": {
                        "id": msg.get("author", {}).get("id"),
                        "name": msg.get("author", {}).get("title"),
                        "subtitle": msg.get("author", {}).get("subtitle"),
                        "isMe": msg.get("author", {}).get("me", False),
                    },
                    "sentAt": msg.get("createdAt"),
                    "images": [
                        f"images/{img_path.name}"
                        for img_path in message_images.get(msg.get("messageId"), [])
                    ],
                }
                for msg in messages
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def format_conversations_index(
        self,
        conversations: list[dict],
    ) -> str:
        """Generate JSON for the conversations index."""
        import json

        data = {
            "type": "conversations_index",
            "count": len(conversations),
            "conversations": [
                {
                    "id": conv.get("conversationId"),
                    "title": conv.get("title"),
                    "participants": [p.get("title") for p in conv.get("participants", [])],
                    "lastActivityAt": conv.get("lastActivityAt"),
                    "preview": conv.get("lastMessage", {}).get("body", "")[:100],
                    "path": f"{conv.get('conversationId', '')[:8]}/index.json",
                }
                for conv in conversations
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def format_index(
        self,
        observations_count: int,
        photos_count: int,
        conversations_count: int,
        child_name: str = "",
    ) -> str:
        """Generate JSON for the main index page."""
        import json

        data = {
            "type": "index",
            "childName": child_name,
            "observations": {
                "count": observations_count,
                "path": "observations/index.json",
            },
            "photos": {
                "count": photos_count,
                "path": "gallery.json",
            },
            "conversations": {
                "count": conversations_count,
                "path": "messages/index.json",
            },
        }
        return json.dumps(data, indent=2, ensure_ascii=False)


# Registry of available formatters
FORMATTERS: dict[str, type[OutputFormatter]] = {
    "html": HTMLFormatter,
    "json": JSONFormatter,
}


def get_formatter(format_type: str) -> OutputFormatter:
    """
    Get a formatter instance by type name.

    Parameters
    ----------
    format_type : str
        Format type ('html', 'json').

    Returns
    -------
    OutputFormatter
        Formatter instance.

    Raises
    ------
    ValueError
        If format type is not recognized.
    """
    if format_type not in FORMATTERS:
        available = ", ".join(FORMATTERS.keys())
        raise ValueError(f"Unknown format '{format_type}'. Available: {available}")
    return FORMATTERS[format_type]()


def get_photos_from_directory(output_dir: Path) -> list[Path]:
    """
    Get all photo files from a directory (excluding observations).

    Parameters
    ----------
    output_dir : Path
        Directory to scan for photos.

    Returns
    -------
    list[Path]
        List of photo file paths.
    """
    if not output_dir.exists():
        return []
    photos = []
    for f in output_dir.iterdir():
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png"):
            photos.append(f)
    return photos

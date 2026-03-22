"""
[File Purpose] Remove noise elements from HTML before content extraction.
[Main Flow] Raw HTML string -> BeautifulSoup parse -> remove noise tags -> return cleaned soup.
[External Connections] Called by cli.py, output consumed by extractor.py.
[Modification Notes] Adding new noise selectors: append to NOISE_TAGS or NOISE_SELECTORS.
"""

from __future__ import annotations

import re
from bs4 import BeautifulSoup, Comment, NavigableString, Tag

# -------------------------------------------------------------------
# Tags that are always noise (entire subtree removed)
# -------------------------------------------------------------------
NOISE_TAGS: set[str] = {
    "script", "style", "noscript", "iframe", "svg", "canvas",
    "video", "audio", "source", "track", "embed", "object",
    "applet", "map", "area",
}

# -------------------------------------------------------------------
# Semantic tags whose *role* is navigation/chrome, not content
# -------------------------------------------------------------------
SEMANTIC_NOISE_TAGS: set[str] = {
    "nav", "footer", "header",
}

# -------------------------------------------------------------------
# CSS selectors for common ad / utility containers
# -------------------------------------------------------------------
NOISE_SELECTORS: list[str] = [
    "[role='banner']",
    "[role='navigation']",
    "[role='complementary']",
    "[role='contentinfo']",
    "[aria-hidden='true']",
]

# -------------------------------------------------------------------
# class/id patterns that strongly indicate non-content
# -------------------------------------------------------------------
NOISE_CLASS_ID_PATTERNS: list[re.Pattern] = [
    re.compile(r"(^|\b)(ad|ads|advert|advertisement|banner|sidebar|widget|popup|modal|cookie|consent|newsletter|social|share|sharing|comment|disqus|footer|header|nav|menu|breadcrumb|pagination|pager|related|recommended|promo|sponsor|tracking|analytics)(\b|$)", re.IGNORECASE),
]


def _matches_noise_pattern(tag: Tag) -> bool:
    """
    [Purpose] Check if a tag's class or id matches known noise patterns.
    [Input] A BeautifulSoup Tag.
    [Output] True if the tag looks like noise based on class/id heuristics.
    """
    classes_raw = tag.get("class", []) if tag.attrs else []
    classes = " ".join(classes_raw) if classes_raw else ""
    tag_id = (tag.get("id", "") if tag.attrs else "") or ""
    combined = f"{classes} {tag_id}"
    if not combined.strip():
        return False
    return any(p.search(combined) for p in NOISE_CLASS_ID_PATTERNS)


def _is_hidden(tag: Tag) -> bool:
    """
    [Purpose] Detect elements hidden via inline style.
    """
    if not hasattr(tag, 'attrs') or tag.attrs is None:
        return False
    style = tag.get("style", "") or ""
    style_lower = style.lower()
    if "display:none" in style_lower.replace(" ", ""):
        return True
    if "visibility:hidden" in style_lower.replace(" ", ""):
        return True
    return False


def clean_html(html: str) -> BeautifulSoup:
    """
    [Purpose] Parse raw HTML and strip all noise, returning a clean BeautifulSoup tree.
    [Input] Raw HTML string (may be malformed).
    [Output] BeautifulSoup object with noise elements removed.
    [Notes] Uses lxml parser for speed and tolerance of malformed markup.
    """
    soup = BeautifulSoup(html, "lxml")

    # 1. Remove HTML comments
    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()

    # 2. Remove always-noise tags
    for tag_name in NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # 3. Remove semantic noise tags
    for tag_name in SEMANTIC_NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # 4. Remove by CSS selector (role, aria-hidden)
    for selector in NOISE_SELECTORS:
        for tag in soup.select(selector):
            tag.decompose()

    # 5. Remove hidden elements
    for tag in soup.find_all(style=True):
        if isinstance(tag, Tag) and _is_hidden(tag):
            tag.decompose()

    # 6. Remove elements matching noise class/id patterns
    #    Be conservative: only remove div/section/aside (not p, a, span etc.)
    removable_containers = {"div", "section", "aside", "span"}
    for tag in soup.find_all(removable_containers):
        if isinstance(tag, Tag) and _matches_noise_pattern(tag):
            tag.decompose()

    # 7. Strip all attributes except href on <a> and src/alt on <img>
    _strip_attributes(soup)

    return soup


def _strip_attributes(soup: BeautifulSoup) -> None:
    """
    [Purpose] Remove inline styles, classes, IDs, and other non-essential attributes.
    [Notes] Preserves href (links), src/alt (images), colspan/rowspan (tables).
    """
    KEEP_ATTRS = {
        "a": {"href"},
        "img": {"src", "alt"},
        "td": {"colspan", "rowspan"},
        "th": {"colspan", "rowspan"},
        "code": {"class"},  # preserve language-* classes for code blocks
    }
    for tag in soup.find_all(True):
        if not isinstance(tag, Tag):
            continue
        allowed = KEEP_ATTRS.get(tag.name, set())
        attrs_to_remove = [k for k in tag.attrs if k not in allowed]
        for attr in attrs_to_remove:
            del tag[attr]

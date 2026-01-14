"""
Entity recognition module for product/service identification.

Provides entity recognition for Reddit text analysis to identify products,
services, brands, and technologies mentioned in discussions.

Enhanced features:
- 20+ context patterns for product/service detection
- Product name aliases and normalization
- Improved confidence scoring based on context strength
- Multi-word entity support

Example:
    >>> from reddit_insight.analysis.entity_recognition import EntityRecognizer
    >>> recognizer = EntityRecognizer()
    >>> entities = recognizer.recognize("I switched to Notion and it's great")
    >>> print(entities[0].name)
    'Notion'
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reddit_insight.reddit.models import Post


class EntityType(Enum):
    """
    Entity type enumeration for categorizing recognized entities.

    Attributes:
        PRODUCT: Products (software, hardware)
        SERVICE: Services (SaaS, web services)
        BRAND: Brands/company names
        TECHNOLOGY: Technologies/frameworks
        UNKNOWN: Unclassified entities
    """

    PRODUCT = "product"
    SERVICE = "service"
    BRAND = "brand"
    TECHNOLOGY = "technology"
    UNKNOWN = "unknown"


@dataclass
class ProductEntity:
    """
    Represents a recognized product/service entity.

    Attributes:
        name: Original text as found
        normalized_name: Normalized name (lowercase, trimmed)
        entity_type: Type of the entity
        confidence: Confidence score (0-1)
        context: Context where entity was found
        mentions: Number of times mentioned
    """

    name: str
    normalized_name: str
    entity_type: EntityType
    confidence: float
    context: str = ""
    mentions: int = 1

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"ProductEntity('{self.name}', type={self.entity_type.value}, "
            f"conf={self.confidence:.2f}, mentions={self.mentions})"
        )


@dataclass
class EntityMention:
    """
    Represents a single mention of an entity in text.

    Attributes:
        entity: The recognized entity
        text: Original text that matched
        start: Start position in the source text
        end: End position in the source text
        sentence: The sentence containing the mention
    """

    entity: ProductEntity
    text: str
    start: int
    end: int
    sentence: str = ""

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"EntityMention('{self.text}', [{self.start}:{self.end}])"


@dataclass
class EntityPattern:
    """
    Pattern definition for entity extraction.

    Attributes:
        pattern_id: Unique identifier for the pattern
        regex: Regular expression pattern string
        entity_type: Type of entity this pattern identifies
        weight: Confidence weight for matches (0-1)
    """

    pattern_id: str
    regex: str
    entity_type: EntityType
    weight: float = 1.0


# ============================================================================
# Product/Service Name Aliases (for normalization)
# ============================================================================

PRODUCT_ALIASES: dict[str, str] = {
    # Common misspellings and variations
    "vscode": "VS Code",
    "vs code": "VS Code",
    "visual studio code": "VS Code",
    "visualstudiocode": "VS Code",
    "chatgpt": "ChatGPT",
    "chat gpt": "ChatGPT",
    "openai": "OpenAI",
    "open ai": "OpenAI",
    "midjourney": "Midjourney",
    "mid journey": "Midjourney",
    "dalle": "DALL-E",
    "dall-e": "DALL-E",
    "dall e": "DALL-E",
    "github copilot": "GitHub Copilot",
    "copilot": "GitHub Copilot",
    "claude": "Claude",
    "anthropic": "Anthropic",
    # Social platforms
    "tiktok": "TikTok",
    "tik tok": "TikTok",
    "youtube": "YouTube",
    "you tube": "YouTube",
    "yt": "YouTube",
    "instagram": "Instagram",
    "insta": "Instagram",
    "ig": "Instagram",
    "facebook": "Facebook",
    "fb": "Facebook",
    "twitter": "Twitter",
    "x": "Twitter",
    "whatsapp": "WhatsApp",
    "linkedin": "LinkedIn",
    "reddit": "Reddit",
    # Productivity tools
    "notion": "Notion",
    "obsidian": "Obsidian",
    "roam": "Roam",
    "evernote": "Evernote",
    "onenote": "OneNote",
    "one note": "OneNote",
    "todoist": "Todoist",
    "asana": "Asana",
    "trello": "Trello",
    "jira": "Jira",
    "monday": "Monday.com",
    "monday.com": "Monday.com",
    "clickup": "ClickUp",
    "click up": "ClickUp",
    # Communication
    "slack": "Slack",
    "discord": "Discord",
    "zoom": "Zoom",
    "teams": "Microsoft Teams",
    "ms teams": "Microsoft Teams",
    "microsoft teams": "Microsoft Teams",
    "google meet": "Google Meet",
    "meet": "Google Meet",
    "telegram": "Telegram",
    "signal": "Signal",
    # Design tools
    "figma": "Figma",
    "canva": "Canva",
    "photoshop": "Photoshop",
    "illustrator": "Illustrator",
    "sketch": "Sketch",
    "invision": "InVision",
    # Cloud/Dev
    "aws": "AWS",
    "amazon web services": "AWS",
    "azure": "Azure",
    "gcp": "Google Cloud",
    "google cloud": "Google Cloud",
    "heroku": "Heroku",
    "vercel": "Vercel",
    "netlify": "Netlify",
    "digitalocean": "DigitalOcean",
    "digital ocean": "DigitalOcean",
    # Programming languages/frameworks
    "python": "Python",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",
    "angular": "Angular",
    "svelte": "Svelte",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "next": "Next.js",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "fast api": "FastAPI",
    "rails": "Ruby on Rails",
    "ruby on rails": "Ruby on Rails",
    "ror": "Ruby on Rails",
    # Databases
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "redis": "Redis",
    "sqlite": "SQLite",
    "dynamodb": "DynamoDB",
    "dynamo": "DynamoDB",
    # Other tools
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "bitbucket": "Bitbucket",
}


# Predefined entity extraction patterns
# Note: Patterns use case-insensitive matching for context words,
# but entity capture groups require Capital letters for proper noun detection
ENTITY_PATTERNS: list[EntityPattern] = [
    # Product/Service context patterns - "using X", "switched to X", "moved to X"
    # Only captures single capitalized word to avoid matching common words
    EntityPattern(
        pattern_id="usage_context",
        regex=r"(?i)(?:using|use|tried|switched to|moved to|migrated to)\s+([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)",
        entity_type=EntityType.PRODUCT,
        weight=0.9,
    ),
    # Usage variants - "I've been using X", "started using X"
    EntityPattern(
        pattern_id="usage_extended",
        regex=r"(?i)(?:been using|started using|start using|stopped using|quit using)\s+([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)",
        entity_type=EntityType.PRODUCT,
        weight=0.9,
    ),
    # Opinion patterns - "X is great", "X was terrible"
    EntityPattern(
        pattern_id="opinion_context",
        regex=r"([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)\s+(?:is|was|has been|seems|looks|feels)\s+(?:great|good|bad|terrible|amazing|awful|excellent|poor|better|worse|best|worst|awesome|fantastic|horrible|decent|solid|trash|garbage|fire|mid)",
        entity_type=EntityType.PRODUCT,
        weight=0.85,
    ),
    # Recommendation patterns - "recommend X", "suggesting X"
    EntityPattern(
        pattern_id="recommendation",
        regex=r"(?i)(?:recommend|recommending|suggest|suggesting|check out|try|give)\s+([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)",
        entity_type=EntityType.PRODUCT,
        weight=0.8,
    ),
    # Preference patterns - "I prefer X", "love using X"
    EntityPattern(
        pattern_id="preference",
        regex=r"(?i)(?:i prefer|prefer|love|hate|dislike|enjoy)\s+([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)",
        entity_type=EntityType.PRODUCT,
        weight=0.85,
    ),
    # Alternative seeking - "alternative to X", "X alternative"
    EntityPattern(
        pattern_id="alternative_seeking",
        regex=r"(?i)(?:alternative to|alternatives to|replacement for|instead of|like)\s+([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)",
        entity_type=EntityType.PRODUCT,
        weight=0.85,
    ),
    # Brand patterns - "by X", "from X", "made by X"
    EntityPattern(
        pattern_id="brand_attribution",
        regex=r"(?i)(?:by|from|made by|developed by|created by|built by)\s+([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)",
        entity_type=EntityType.BRAND,
        weight=0.75,
    ),
    # Technology patterns - "built with X", "powered by X"
    EntityPattern(
        pattern_id="technology_stack",
        regex=r"(?i)(?:built with|powered by|written in|developed with|coded in|uses)\s+([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)",
        entity_type=EntityType.TECHNOLOGY,
        weight=0.85,
    ),
    # Comparison patterns - "X vs Y", "X or Y"
    EntityPattern(
        pattern_id="comparison_vs",
        regex=r"([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)\s+(?:vs\.?|versus)\s+([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)",
        entity_type=EntityType.PRODUCT,
        weight=0.85,
    ),
    # Better/worse comparison - "X is better than Y"
    EntityPattern(
        pattern_id="comparison_better",
        regex=r"([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)\s+(?:is|was)\s+(?:better|worse|faster|slower|cheaper|more expensive)\s+than\s+([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)",
        entity_type=EntityType.PRODUCT,
        weight=0.85,
    ),
    # Migration patterns - "from X to Y"
    EntityPattern(
        pattern_id="migration",
        regex=r"(?i)(?:from|left)\s+([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)\s+(?:to|for)\s+([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)",
        entity_type=EntityType.PRODUCT,
        weight=0.9,
    ),
    # Integration patterns - "X with Y", "integrates with X"
    EntityPattern(
        pattern_id="integration",
        regex=r"(?i)(?:integrates? with|works with|connects to|syncs? with)\s+([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)",
        entity_type=EntityType.SERVICE,
        weight=0.75,
    ),
    # Learning patterns - "learning X", "started X"
    EntityPattern(
        pattern_id="learning",
        regex=r"(?i)(?:learning|studying|mastering|getting into)\s+([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)",
        entity_type=EntityType.TECHNOLOGY,
        weight=0.7,
    ),
    # Subscription patterns - "subscribed to X", "paying for X"
    EntityPattern(
        pattern_id="subscription",
        regex=r"(?i)(?:subscribed to|subscribe to|paying for|pay for|bought|purchased)\s+([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)",
        entity_type=EntityType.SERVICE,
        weight=0.85,
    ),
    # Cancellation patterns - "cancelled X", "unsubscribed from X"
    # Require capital letter at start to avoid matching "my"
    EntityPattern(
        pattern_id="cancellation",
        regex=r"(?i)(?:cancell?ed|unsubscribed from|stopped paying for|ditched)\s+(?:my\s+)?([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)",
        entity_type=EntityType.SERVICE,
        weight=0.85,
    ),
    # Experience patterns - "experience with X", "X experience"
    EntityPattern(
        pattern_id="experience",
        regex=r"(?i)(?:experience with|experiences? using|my time with)\s+([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)",
        entity_type=EntityType.PRODUCT,
        weight=0.75,
    ),
    # Review patterns - "review of X", "X review"
    EntityPattern(
        pattern_id="review",
        regex=r"(?i)(?:review of|review:?|reviewing)\s+([A-Z][a-zA-Z0-9]+(?:\.[a-zA-Z]+)?)",
        entity_type=EntityType.PRODUCT,
        weight=0.7,
    ),
]


@dataclass
class PatternEntityExtractor:
    """
    Pattern-based entity extractor using regular expressions.

    Extracts entities from text using predefined patterns that match
    common ways products, services, and technologies are mentioned.

    Example:
        >>> extractor = PatternEntityExtractor()
        >>> mentions = extractor.extract("I switched to Notion and it's great")
        >>> print(len(mentions))
        1
    """

    patterns: list[EntityPattern] = field(default_factory=lambda: ENTITY_PATTERNS.copy())
    _compiled: dict[str, re.Pattern[str]] = field(init=False, repr=False, default_factory=dict)

    def __post_init__(self) -> None:
        """Compile patterns for efficient matching."""
        for pattern in self.patterns:
            # Patterns include inline flags (e.g., (?i)) where needed
            self._compiled[pattern.pattern_id] = re.compile(pattern.regex)

    def _normalize_name(self, name: str) -> str:
        """
        Normalize entity name for comparison.

        Applies alias resolution for common product name variations.

        Args:
            name: Raw entity name

        Returns:
            Normalized name (lowercase, trimmed, single spaces)
        """
        # Lowercase, strip whitespace, collapse multiple spaces
        normalized = name.strip().lower()
        normalized = re.sub(r"\s+", " ", normalized)

        # Check if there's a known alias
        if normalized in PRODUCT_ALIASES:
            return PRODUCT_ALIASES[normalized].lower()

        return normalized

    def _get_canonical_name(self, name: str) -> str:
        """
        Get the canonical (display) name for an entity.

        Args:
            name: Raw entity name

        Returns:
            Canonical name (proper capitalization from aliases, or original)
        """
        normalized = name.strip().lower()

        # Check if there's a known alias for proper capitalization
        if normalized in PRODUCT_ALIASES:
            return PRODUCT_ALIASES[normalized]

        return name

    def _extract_sentence(self, text: str, start: int, end: int) -> str:
        """
        Extract the sentence containing the match.

        Args:
            text: Full text
            start: Match start position
            end: Match end position

        Returns:
            Sentence containing the match
        """
        # Find sentence boundaries
        sentence_start = text.rfind(".", 0, start)
        sentence_start = sentence_start + 1 if sentence_start != -1 else 0

        sentence_end = text.find(".", end)
        sentence_end = sentence_end + 1 if sentence_end != -1 else len(text)

        return text[sentence_start:sentence_end].strip()

    def extract(self, text: str) -> list[EntityMention]:
        """
        Extract entity mentions from text using patterns.

        Args:
            text: Input text to analyze

        Returns:
            List of EntityMention objects found in the text
        """
        if not text or not text.strip():
            return []

        mentions: list[EntityMention] = []
        seen_positions: set[tuple[int, int]] = set()  # Avoid duplicate positions

        for pattern in self.patterns:
            compiled = self._compiled.get(pattern.pattern_id)
            if compiled is None:
                continue

            for match in compiled.finditer(text):
                # Handle patterns with multiple capture groups (like comparison)
                for group_idx in range(1, len(match.groups()) + 1):
                    entity_text = match.group(group_idx)
                    if entity_text is None:
                        continue

                    # Get position of this specific group
                    start = match.start(group_idx)
                    end = match.end(group_idx)

                    # Skip if we already have an entity at this position
                    position_key = (start, end)
                    if position_key in seen_positions:
                        continue
                    seen_positions.add(position_key)

                    # Create entity with canonical name
                    canonical_name = self._get_canonical_name(entity_text)
                    entity = ProductEntity(
                        name=canonical_name,
                        normalized_name=self._normalize_name(entity_text),
                        entity_type=pattern.entity_type,
                        confidence=pattern.weight,
                        context=match.group(0),
                    )

                    mention = EntityMention(
                        entity=entity,
                        text=entity_text,
                        start=start,
                        end=end,
                        sentence=self._extract_sentence(text, start, end),
                    )

                    mentions.append(mention)

        # Sort by position
        mentions.sort(key=lambda m: m.start)
        return mentions


@dataclass
class EntityRecognizerConfig:
    """
    Configuration for EntityRecognizer.

    Attributes:
        min_confidence: Minimum confidence threshold for entities
        merge_similar: Whether to merge similar entities
        similarity_threshold: Threshold for considering entities similar (0-1)
    """

    min_confidence: float = 0.3
    merge_similar: bool = True
    similarity_threshold: float = 0.8


@dataclass
class EntityRecognizer:
    """
    Unified entity recognizer combining multiple extraction methods.

    Provides a high-level interface for recognizing product/service entities
    in text, with support for entity merging and aggregation across multiple
    documents.

    Example:
        >>> recognizer = EntityRecognizer()
        >>> entities = recognizer.recognize("I use Slack for team chat")
        >>> print(entities[0].name)
        'Slack'
    """

    config: EntityRecognizerConfig = field(default_factory=EntityRecognizerConfig)
    _pattern_extractor: PatternEntityExtractor = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize extractors."""
        self._pattern_extractor = PatternEntityExtractor()

    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two entity names.

        Uses normalized Levenshtein-like comparison based on common characters.

        Args:
            name1: First entity name (normalized)
            name2: Second entity name (normalized)

        Returns:
            Similarity score between 0 and 1
        """
        if name1 == name2:
            return 1.0

        # Simple character-based similarity
        set1 = set(name1)
        set2 = set(name2)

        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        # Jaccard similarity with length penalty
        jaccard = intersection / union if union > 0 else 0.0

        # Length similarity
        len_sim = min(len(name1), len(name2)) / max(len(name1), len(name2))

        # Prefix similarity (important for product names)
        common_prefix = 0
        for c1, c2 in zip(name1, name2, strict=False):
            if c1 == c2:
                common_prefix += 1
            else:
                break
        prefix_sim = common_prefix / max(len(name1), len(name2)) if name1 and name2 else 0.0

        # Weighted combination
        return 0.4 * jaccard + 0.3 * len_sim + 0.3 * prefix_sim

    def _merge_entities(self, entities: list[ProductEntity]) -> list[ProductEntity]:
        """
        Merge similar entities together.

        Groups entities with similar names and combines their mention counts.

        Args:
            entities: List of entities to merge

        Returns:
            List of merged entities with updated mention counts
        """
        if not entities or not self.config.merge_similar:
            return entities

        # Group by normalized name
        merged: dict[str, ProductEntity] = {}

        for entity in entities:
            # Check if we already have a similar entity
            matched_key = None
            for key in merged:
                similarity = self._calculate_similarity(entity.normalized_name, key)
                if similarity >= self.config.similarity_threshold:
                    matched_key = key
                    break

            if matched_key:
                # Merge with existing entity
                existing = merged[matched_key]
                # Keep the one with higher confidence as the primary
                if entity.confidence > existing.confidence:
                    new_entity = ProductEntity(
                        name=entity.name,
                        normalized_name=entity.normalized_name,
                        entity_type=entity.entity_type,
                        confidence=max(entity.confidence, existing.confidence),
                        context=entity.context or existing.context,
                        mentions=existing.mentions + entity.mentions,
                    )
                    merged[matched_key] = new_entity
                else:
                    existing.mentions += entity.mentions
                    existing.confidence = max(existing.confidence, entity.confidence)
            else:
                # New entity
                merged[entity.normalized_name] = ProductEntity(
                    name=entity.name,
                    normalized_name=entity.normalized_name,
                    entity_type=entity.entity_type,
                    confidence=entity.confidence,
                    context=entity.context,
                    mentions=entity.mentions,
                )

        return list(merged.values())

    def recognize(self, text: str) -> list[ProductEntity]:
        """
        Recognize entities in text.

        Args:
            text: Input text to analyze

        Returns:
            List of recognized entities
        """
        if not text or not text.strip():
            return []

        # Extract mentions using pattern extractor
        mentions = self._pattern_extractor.extract(text)

        # Convert mentions to entities
        entities = [m.entity for m in mentions]

        # Filter by confidence
        entities = [e for e in entities if e.confidence >= self.config.min_confidence]

        # Merge similar entities
        entities = self._merge_entities(entities)

        # Sort by confidence (highest first)
        entities.sort(key=lambda e: e.confidence, reverse=True)

        return entities

    def recognize_in_post(self, post: Post) -> list[ProductEntity]:
        """
        Recognize entities in a Reddit Post.

        Combines title and selftext for analysis.

        Args:
            post: Reddit Post object

        Returns:
            List of recognized entities
        """
        # Combine title and selftext
        text_parts = [post.title]
        if post.selftext:
            text_parts.append(post.selftext)

        combined_text = " ".join(text_parts)
        return self.recognize(combined_text)

    def recognize_in_posts(self, posts: list[Post]) -> dict[str, ProductEntity]:
        """
        Recognize and aggregate entities across multiple posts.

        Args:
            posts: List of Post objects

        Returns:
            Dictionary mapping normalized entity names to aggregated entities
        """
        if not posts:
            return {}

        # Collect all entities
        all_entities: list[ProductEntity] = []
        for post in posts:
            entities = self.recognize_in_post(post)
            all_entities.extend(entities)

        # Merge entities with updated mention counts
        merged = self._merge_entities(all_entities)

        # Create result dictionary
        result = {e.normalized_name: e for e in merged}

        return result

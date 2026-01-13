"""
Entity recognition module for product/service identification.

Provides entity recognition for Reddit text analysis to identify products,
services, brands, and technologies mentioned in discussions.

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

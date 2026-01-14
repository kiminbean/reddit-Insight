"""페이지네이션 유틸리티 모듈.

대시보드 API 엔드포인트에서 공통으로 사용되는 페이지네이션 기능을 제공한다.
"""

import math
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class PaginationMeta:
    """페이지네이션 메타데이터.

    Attributes:
        total: 전체 항목 수
        page: 현재 페이지 번호 (1-indexed)
        per_page: 페이지당 항목 수
        pages: 전체 페이지 수
    """

    total: int
    page: int
    per_page: int
    pages: int

    def to_dict(self) -> dict[str, int]:
        """딕셔너리로 변환한다."""
        return {
            "total": self.total,
            "page": self.page,
            "per_page": self.per_page,
            "pages": self.pages,
        }


@dataclass
class PaginatedResponse(Generic[T]):
    """페이지네이션 응답.

    Attributes:
        items: 페이지의 항목 목록
        meta: 페이지네이션 메타데이터
    """

    items: list[T]
    meta: PaginationMeta

    def to_dict(self, item_converter: callable = None) -> dict[str, Any]:
        """딕셔너리로 변환한다.

        Args:
            item_converter: 항목을 딕셔너리로 변환하는 함수 (None이면 그대로 사용)

        Returns:
            페이지네이션 응답 딕셔너리
        """
        if item_converter:
            items = [item_converter(item) for item in self.items]
        else:
            items = self.items

        return {
            "items": items,
            "meta": self.meta.to_dict(),
        }


def paginate(
    items: list[T],
    page: int = 1,
    per_page: int = 20,
    max_per_page: int = 100,
) -> PaginatedResponse[T]:
    """리스트에 페이지네이션을 적용한다.

    Args:
        items: 전체 항목 목록
        page: 요청 페이지 번호 (1-indexed)
        per_page: 페이지당 항목 수
        max_per_page: 최대 페이지당 항목 수

    Returns:
        페이지네이션이 적용된 응답
    """
    # 파라미터 정규화
    page = max(1, page)
    per_page = min(max(1, per_page), max_per_page)

    total = len(items)
    pages = max(1, math.ceil(total / per_page))

    # 요청 페이지가 범위를 벗어나면 마지막 페이지로 조정
    page = min(page, pages)

    # 슬라이스 계산
    start = (page - 1) * per_page
    end = start + per_page
    page_items = items[start:end]

    meta = PaginationMeta(
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )

    return PaginatedResponse(items=page_items, meta=meta)


def get_pagination_params(
    page: int = 1,
    per_page: int = 20,
    max_per_page: int = 100,
) -> tuple[int, int]:
    """페이지네이션 파라미터를 정규화한다.

    Args:
        page: 요청 페이지 번호
        per_page: 페이지당 항목 수
        max_per_page: 최대 페이지당 항목 수

    Returns:
        정규화된 (page, per_page) 튜플
    """
    page = max(1, page)
    per_page = min(max(1, per_page), max_per_page)
    return page, per_page

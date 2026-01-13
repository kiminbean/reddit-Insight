"""
Demand detection engine module.

텍스트에서 수요 패턴을 자동으로 탐지하고 추출하는 엔진.

Example:
    >>> from reddit_insight.analysis.demand_detector import DemandDetector
    >>> detector = DemandDetector()
    >>> matches = detector.detect("I wish there was a better way to organize notes")
    >>> for match in matches:
    ...     print(f"{match.pattern.category}: {match.matched_text}")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from reddit_insight.analysis.demand_patterns import (
    DemandCategory,
    DemandMatch,
    DemandPattern,
    DemandPatternLibrary,
)

if TYPE_CHECKING:
    from reddit_insight.reddit.models import Post


@dataclass
class DemandDetectorConfig:
    """
    수요 탐지기 설정.

    Attributes:
        context_window: 매칭 전후 추출할 문자 수 (기본값: 100)
        min_confidence: 최소 신뢰도 임계값 (기본값: 0.5)
        case_sensitive: 대소문자 구분 여부 (기본값: False)
        languages: 탐지할 언어 목록 (기본값: ["en"])

    Example:
        >>> config = DemandDetectorConfig(context_window=150, min_confidence=0.6)
        >>> detector = DemandDetector(config=config)
    """

    context_window: int = 100
    min_confidence: float = 0.5
    case_sensitive: bool = False
    languages: list[str] = field(default_factory=lambda: ["en"])


@dataclass
class DemandSummary:
    """
    수요 탐지 요약 결과.

    여러 텍스트에서 탐지된 수요 패턴의 요약 정보.

    Attributes:
        total_matches: 총 매칭 수
        by_category: 카테고리별 매칭 수
        top_demands: 신뢰도 기준 상위 수요 목록
        analyzed_texts: 분석한 텍스트 수

    Example:
        >>> summary = detector.summarize(matches)
        >>> print(f"Total: {summary.total_matches}, Top: {summary.top_demands[0]}")
    """

    total_matches: int
    by_category: dict[DemandCategory, int]
    top_demands: list[DemandMatch]
    analyzed_texts: int

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"DemandSummary(total={self.total_matches}, "
            f"categories={len(self.by_category)}, "
            f"analyzed={self.analyzed_texts})"
        )


class DemandDetector:
    """
    수요 패턴 탐지 엔진.

    텍스트에서 미충족 수요를 나타내는 패턴을 자동으로 탐지한다.
    정규식 기반 1차 필터링과 컨텍스트 추출, 신뢰도 계산을 수행한다.

    Attributes:
        _library: 패턴 라이브러리
        _config: 탐지기 설정

    Example:
        >>> detector = DemandDetector()
        >>> matches = detector.detect("I wish there was a better tool for this")
        >>> print(f"Found {len(matches)} demand expressions")
    """

    def __init__(
        self,
        pattern_library: DemandPatternLibrary | None = None,
        config: DemandDetectorConfig | None = None,
    ) -> None:
        """
        수요 탐지기 초기화.

        Args:
            pattern_library: 패턴 라이브러리 (None이면 기본 영어 라이브러리 사용)
            config: 탐지기 설정 (None이면 기본 설정 사용)
        """
        self._config = config or DemandDetectorConfig()

        # 라이브러리 설정
        if pattern_library is not None:
            self._library = pattern_library
        else:
            # 언어에 따라 적절한 라이브러리 생성
            if len(self._config.languages) > 1 or "multi" in self._config.languages:
                self._library = DemandPatternLibrary.create_multilingual_library()
            elif "ko" in self._config.languages:
                self._library = DemandPatternLibrary.create_korean_library()
            else:
                self._library = DemandPatternLibrary.create_english_library()

    @property
    def config(self) -> DemandDetectorConfig:
        """Get the detector configuration."""
        return self._config

    @property
    def library(self) -> DemandPatternLibrary:
        """Get the pattern library."""
        return self._library

    def _extract_context(
        self,
        text: str,
        match_start: int,
        match_end: int,
        window: int | None = None,
    ) -> str:
        """
        매칭 주변 컨텍스트 추출.

        문장 경계(마침표, 느낌표, 물음표, 줄바꿈)를 고려하여
        매칭 전후 텍스트를 추출한다.

        Args:
            text: 원본 텍스트
            match_start: 매칭 시작 위치
            match_end: 매칭 끝 위치
            window: 추출할 문자 수 (None이면 설정값 사용)

        Returns:
            매칭 주변 컨텍스트 문자열
        """
        if window is None:
            window = self._config.context_window

        # 기본 윈도우 범위 계산
        context_start = max(0, match_start - window)
        context_end = min(len(text), match_end + window)

        # 문장 경계 찾기 (앞쪽)
        sentence_boundaries = ".!?\n"
        for i in range(context_start, match_start):
            if text[i] in sentence_boundaries:
                # 경계 다음 문자부터 시작 (공백 건너뜀)
                context_start = i + 1
                while context_start < match_start and text[context_start].isspace():
                    context_start += 1
                break

        # 문장 경계 찾기 (뒤쪽)
        for i in range(match_end, context_end):
            if text[i] in sentence_boundaries:
                context_end = i + 1
                break

        return text[context_start:context_end].strip()

    def _calculate_confidence(
        self,
        text: str,
        pattern: DemandPattern,
        match: re.Match[str],
    ) -> float:
        """
        매칭 신뢰도 계산.

        패턴 가중치, 키워드 존재 여부, 문맥 품질을 고려하여
        0-1 범위의 신뢰도 점수를 계산한다.

        Args:
            text: 원본 텍스트
            pattern: 매칭된 패턴
            match: 정규식 매칭 객체

        Returns:
            신뢰도 점수 (0-1)
        """
        # 기본 점수는 패턴 가중치 (0.5-1.3 범위를 0-1로 정규화)
        base_score = min(pattern.weight / 1.3, 1.0)

        # 키워드 보너스: 키워드가 많이 포함될수록 신뢰도 증가
        keyword_bonus = 0.0
        if pattern.keywords:
            text_lower = text.lower()
            matched_keywords = sum(
                1 for kw in pattern.keywords if kw.lower() in text_lower
            )
            keyword_bonus = min(matched_keywords * 0.1, 0.2)

        # 문맥 품질 보너스: 매칭된 텍스트 길이에 따른 보너스
        matched_text = match.group(0)
        length_bonus = min(len(matched_text) / 50, 0.1)

        # 위치 보너스: 문장 시작 부분에서 매칭되면 신뢰도 증가
        position_bonus = 0.0
        if match.start() == 0 or text[match.start() - 1] in ".!?\n ":
            position_bonus = 0.05

        # 최종 신뢰도 계산 (0-1 범위로 제한)
        confidence = base_score + keyword_bonus + length_bonus + position_bonus
        return min(max(confidence, 0.0), 1.0)

    def _deduplicate_matches(
        self,
        matches: list[DemandMatch],
    ) -> list[DemandMatch]:
        """
        중복 매칭 제거.

        겹치는 span을 가진 매칭 중 가장 높은 신뢰도를 가진 것만 유지한다.

        Args:
            matches: 중복 가능성이 있는 매칭 목록

        Returns:
            중복이 제거된 매칭 목록
        """
        if not matches:
            return []

        # 신뢰도 기준 내림차순 정렬
        sorted_matches = sorted(matches, key=lambda m: m.confidence, reverse=True)

        # 이미 처리된 span 범위 추적
        used_ranges: list[tuple[int, int]] = []
        deduplicated: list[DemandMatch] = []

        for match in sorted_matches:
            start, end = match.matched_span

            # 기존 범위와 겹치는지 확인
            overlaps = False
            for used_start, used_end in used_ranges:
                # 범위가 겹치는 경우
                if not (end <= used_start or start >= used_end):
                    overlaps = True
                    break

            if not overlaps:
                deduplicated.append(match)
                used_ranges.append((start, end))

        # 원래 텍스트 순서대로 정렬
        deduplicated.sort(key=lambda m: m.matched_span[0])
        return deduplicated

    def _match_pattern(
        self,
        text: str,
        pattern: DemandPattern,
    ) -> list[DemandMatch]:
        """
        단일 패턴 매칭 수행.

        주어진 패턴으로 텍스트를 검색하고 매칭 결과를 반환한다.

        Args:
            text: 검색할 텍스트
            pattern: 적용할 패턴

        Returns:
            매칭 결과 목록
        """
        matches: list[DemandMatch] = []

        # 컴파일된 패턴 가져오기
        compiled = self._library.get_compiled_pattern(pattern.pattern_id)
        if compiled is None:
            return matches

        # 대소문자 구분 설정에 따라 패턴 재컴파일
        if self._config.case_sensitive:
            try:
                compiled = re.compile(pattern.regex_pattern)
            except re.error:
                return matches

        # 모든 매칭 찾기
        for match in compiled.finditer(text):
            confidence = self._calculate_confidence(text, pattern, match)

            # 최소 신뢰도 이하면 건너뜀
            if confidence < self._config.min_confidence:
                continue

            context = self._extract_context(
                text, match.start(), match.end()
            )

            demand_match = DemandMatch(
                pattern=pattern,
                text=text,
                matched_span=(match.start(), match.end()),
                context=context,
                confidence=confidence,
            )
            matches.append(demand_match)

        return matches

    def detect(self, text: str) -> list[DemandMatch]:
        """
        텍스트에서 수요 패턴 탐지.

        등록된 모든 패턴을 사용하여 텍스트에서 수요 표현을 찾고,
        중복을 제거한 결과를 반환한다.

        Args:
            text: 분석할 텍스트

        Returns:
            탐지된 수요 매칭 목록 (중복 제거됨)

        Example:
            >>> detector = DemandDetector()
            >>> matches = detector.detect("I wish there was a better tool")
            >>> for m in matches:
            ...     print(f"{m.category}: {m.matched_text}")
        """
        if not text or not text.strip():
            return []

        all_matches: list[DemandMatch] = []

        # 모든 패턴에 대해 매칭 수행
        for pattern in self._library.get_patterns():
            pattern_matches = self._match_pattern(text, pattern)
            all_matches.extend(pattern_matches)

        # 중복 제거 후 반환
        return self._deduplicate_matches(all_matches)

    def detect_in_post(self, post: Post) -> list[DemandMatch]:
        """
        Post 객체에서 수요 패턴 탐지.

        게시물의 제목과 본문을 결합하여 분석한다.

        Args:
            post: Reddit Post 객체

        Returns:
            탐지된 수요 매칭 목록

        Example:
            >>> from reddit_insight.reddit.models import Post
            >>> post = Post(title="I wish there was...", selftext="...", ...)
            >>> matches = detector.detect_in_post(post)
        """
        # 제목과 본문 결합 (줄바꿈으로 구분)
        combined_text = post.title
        if post.selftext:
            combined_text = f"{post.title}\n\n{post.selftext}"

        return self.detect(combined_text)

    def detect_in_posts(self, posts: list[Post]) -> list[DemandMatch]:
        """
        여러 게시물에서 수요 패턴 일괄 탐지.

        Args:
            posts: Reddit Post 객체 목록

        Returns:
            모든 게시물에서 탐지된 수요 매칭 목록

        Example:
            >>> posts = [post1, post2, post3]
            >>> all_matches = detector.detect_in_posts(posts)
            >>> print(f"Found {len(all_matches)} total demands")
        """
        all_matches: list[DemandMatch] = []

        for post in posts:
            matches = self.detect_in_post(post)
            all_matches.extend(matches)

        return all_matches

    def detect_by_category(
        self,
        text: str,
        category: DemandCategory,
    ) -> list[DemandMatch]:
        """
        특정 카테고리의 수요 패턴만 탐지.

        Args:
            text: 분석할 텍스트
            category: 탐지할 수요 카테고리

        Returns:
            해당 카테고리의 수요 매칭 목록

        Example:
            >>> matches = detector.detect_by_category(text, DemandCategory.PAIN_POINT)
        """
        if not text or not text.strip():
            return []

        all_matches: list[DemandMatch] = []

        # 해당 카테고리 패턴만 사용
        for pattern in self._library.get_patterns(category):
            pattern_matches = self._match_pattern(text, pattern)
            all_matches.extend(pattern_matches)

        return self._deduplicate_matches(all_matches)

    def get_category_stats(
        self,
        matches: list[DemandMatch],
    ) -> dict[DemandCategory, int]:
        """
        카테고리별 매칭 수 집계.

        Args:
            matches: 수요 매칭 목록

        Returns:
            카테고리별 매칭 수 딕셔너리

        Example:
            >>> stats = detector.get_category_stats(matches)
            >>> print(f"Pain points: {stats.get(DemandCategory.PAIN_POINT, 0)}")
        """
        stats: dict[DemandCategory, int] = {}

        for match in matches:
            category = match.category
            stats[category] = stats.get(category, 0) + 1

        return stats

    def get_top_demands(
        self,
        matches: list[DemandMatch],
        top_n: int = 10,
    ) -> list[DemandMatch]:
        """
        신뢰도 기준 상위 수요 추출.

        Args:
            matches: 수요 매칭 목록
            top_n: 반환할 최대 수요 개수 (기본값: 10)

        Returns:
            신뢰도 기준 상위 N개 수요 목록

        Example:
            >>> top = detector.get_top_demands(matches, top_n=5)
            >>> for demand in top:
            ...     print(f"{demand.confidence:.2f}: {demand.matched_text}")
        """
        sorted_matches = sorted(
            matches, key=lambda m: m.confidence, reverse=True
        )
        return sorted_matches[:top_n]

    def summarize(
        self,
        matches: list[DemandMatch],
        analyzed_texts: int = 1,
    ) -> DemandSummary:
        """
        수요 탐지 결과 요약 생성.

        Args:
            matches: 수요 매칭 목록
            analyzed_texts: 분석한 텍스트 수

        Returns:
            수요 탐지 요약

        Example:
            >>> summary = detector.summarize(matches, analyzed_texts=100)
            >>> print(f"Found {summary.total_matches} demands in {summary.analyzed_texts} texts")
        """
        return DemandSummary(
            total_matches=len(matches),
            by_category=self.get_category_stats(matches),
            top_demands=self.get_top_demands(matches),
            analyzed_texts=analyzed_texts,
        )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"DemandDetector(library={self._library!r}, "
            f"config={self._config!r})"
        )

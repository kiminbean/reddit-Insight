"""LLM 기반 분석기.

LLM을 사용하여 Reddit 게시물을 분석하는 기능을 제공한다:
- 게시물 요약
- 카테고리 분류
- 심층 감성 분석
- 인사이트 생성
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from reddit_insight.llm.prompts import get_template

if TYPE_CHECKING:
    from reddit_insight.llm.client import LLMClient

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class CategoryResult:
    """카테고리 분류 결과.

    Attributes:
        text: 원본 텍스트
        category: 주요 카테고리
        confidence: 신뢰도 (0-100)
        reason: 분류 이유
        secondary_categories: 2순위 이하 카테고리 목록
    """

    text: str
    category: str
    confidence: float
    reason: str = ""
    secondary_categories: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SentimentAspect:
    """감성 분석의 세부 측면.

    Attributes:
        aspect: 분석 대상 (예: 가격, 품질)
        sentiment: 해당 측면의 감성 (positive/negative/neutral)
        reason: 판단 근거
    """

    aspect: str
    sentiment: str
    reason: str = ""


@dataclass
class DeepSentimentResult:
    """심층 감성 분석 결과.

    Attributes:
        overall_sentiment: 전체 감성 (positive/neutral/negative)
        sentiment_score: 감성 점수 (-1.0 ~ +1.0)
        factors: 감성에 영향을 준 세부 요인들
        emotions: 감지된 감정 목록
        is_opinion: 의견인지 사실인지 여부
        user_needs: 사용자 니즈 목록
        pain_points: 불만 사항 목록
    """

    overall_sentiment: str
    sentiment_score: float
    factors: list[SentimentAspect] = field(default_factory=list)
    emotions: list[str] = field(default_factory=list)
    is_opinion: bool = True
    user_needs: list[str] = field(default_factory=list)
    pain_points: list[str] = field(default_factory=list)


@dataclass
class Insight:
    """비즈니스 인사이트.

    Attributes:
        title: 인사이트 제목
        finding: 발견 내용
        meaning: 비즈니스적 의미
        recommendation: 권장 조치
        priority: 우선순위 (high/medium/low)
    """

    title: str
    finding: str
    meaning: str
    recommendation: str
    priority: str = "medium"


# =============================================================================
# LLM ANALYZER
# =============================================================================


class LLMAnalyzer:
    """LLM 기반 분석기.

    LLM 클라이언트를 사용하여 텍스트 분석 작업을 수행한다.
    프롬프트 템플릿 시스템과 연동하여 일관된 분석 결과를 생성한다.

    Attributes:
        client: LLM 클라이언트 인스턴스
        max_retries: API 호출 실패 시 재시도 횟수
    """

    DEFAULT_CATEGORIES = [
        "Feature Request",
        "Bug Report",
        "Question",
        "Discussion",
        "Review",
        "Complaint",
        "Suggestion",
        "Comparison",
        "Tutorial",
        "News",
    ]

    def __init__(
        self,
        client: LLMClient,
        max_retries: int = 3,
    ) -> None:
        """LLMAnalyzer를 초기화한다.

        Args:
            client: LLM 클라이언트 인스턴스
            max_retries: API 호출 실패 시 재시도 횟수
        """
        self.client = client
        self.max_retries = max_retries

    # =========================================================================
    # POST SUMMARIZATION
    # =========================================================================

    async def summarize_posts(
        self,
        posts: list[dict[str, Any]],
        max_posts: int = 50,
        temperature: float = 0.5,
    ) -> str:
        """게시물 목록을 요약하여 핵심 논의 주제를 추출한다.

        Args:
            posts: 게시물 목록 (각 게시물은 title, body, score 등 포함)
            max_posts: 분석할 최대 게시물 수
            temperature: 창의성 조절 (낮을수록 일관적)

        Returns:
            요약 텍스트 (마크다운 형식)

        Raises:
            LLMError: API 호출 실패 시
        """
        if not posts:
            return "분석할 게시물이 없습니다."

        # 게시물을 텍스트로 포맷팅
        posts_text = self._format_posts_for_prompt(posts[:max_posts])

        # 프롬프트 생성
        template = get_template("summarize_posts")
        prompt = template.format(posts=posts_text)

        # LLM 호출
        result = await self.client.complete_with_retry(
            prompt=prompt,
            max_retries=self.max_retries,
            temperature=temperature,
            max_tokens=2048,
        )

        logger.info("게시물 %d개 요약 완료", len(posts[:max_posts]))
        return result

    # =========================================================================
    # CONTENT CATEGORIZATION
    # =========================================================================

    async def categorize_content(
        self,
        texts: list[str],
        categories: list[str] | None = None,
        temperature: float = 0.3,
    ) -> list[CategoryResult]:
        """텍스트를 카테고리로 분류한다.

        Args:
            texts: 분류할 텍스트 목록
            categories: 사용할 카테고리 목록 (None이면 기본 카테고리 사용)
            temperature: 창의성 조절 (낮을수록 일관적)

        Returns:
            CategoryResult 목록

        Raises:
            LLMError: API 호출 실패 시
        """
        if not texts:
            return []

        if categories is None:
            categories = self.DEFAULT_CATEGORIES

        categories_text = "\n".join(f"- {cat}" for cat in categories)
        results: list[CategoryResult] = []

        for text in texts:
            try:
                template = get_template("categorize_content")
                prompt = template.format(text=text, categories=categories_text)

                response = await self.client.complete_with_retry(
                    prompt=prompt,
                    max_retries=self.max_retries,
                    temperature=temperature,
                    max_tokens=512,
                )

                # JSON 파싱
                parsed = self._parse_json_response(response)

                result = CategoryResult(
                    text=text[:200],  # 원본 텍스트 (축약)
                    category=parsed.get("primary_category", "Unknown"),
                    confidence=float(parsed.get("confidence", 50)),
                    reason=parsed.get("reason", ""),
                    secondary_categories=parsed.get("secondary_categories", []),
                )
                results.append(result)

            except Exception as e:
                logger.warning("텍스트 분류 실패: %s", e)
                # 실패 시 기본값으로 처리
                results.append(
                    CategoryResult(
                        text=text[:200],
                        category="Unknown",
                        confidence=0,
                        reason=f"분류 실패: {e}",
                    )
                )

        logger.info("텍스트 %d개 카테고리 분류 완료", len(results))
        return results

    async def categorize_single(
        self,
        text: str,
        categories: list[str] | None = None,
        temperature: float = 0.3,
    ) -> CategoryResult:
        """단일 텍스트를 카테고리로 분류한다.

        Args:
            text: 분류할 텍스트
            categories: 사용할 카테고리 목록
            temperature: 창의성 조절

        Returns:
            CategoryResult
        """
        results = await self.categorize_content([text], categories, temperature)
        return results[0] if results else CategoryResult(
            text=text[:200], category="Unknown", confidence=0
        )

    # =========================================================================
    # DEEP SENTIMENT ANALYSIS
    # =========================================================================

    async def analyze_sentiment_deep(
        self,
        text: str,
        temperature: float = 0.4,
    ) -> DeepSentimentResult:
        """텍스트의 감성을 심층 분석한다.

        Args:
            text: 분석할 텍스트
            temperature: 창의성 조절

        Returns:
            DeepSentimentResult

        Raises:
            LLMError: API 호출 실패 시
        """
        if not text.strip():
            return DeepSentimentResult(
                overall_sentiment="neutral",
                sentiment_score=0.0,
            )

        template = get_template("sentiment_analysis")
        prompt = template.format(text=text)

        try:
            response = await self.client.complete_with_retry(
                prompt=prompt,
                max_retries=self.max_retries,
                temperature=temperature,
                max_tokens=1024,
            )

            parsed = self._parse_json_response(response)

            # 세부 요인 파싱
            factors = [
                SentimentAspect(
                    aspect=f.get("aspect", ""),
                    sentiment=f.get("sentiment", "neutral"),
                    reason=f.get("reason", ""),
                )
                for f in parsed.get("factors", [])
            ]

            result = DeepSentimentResult(
                overall_sentiment=parsed.get("overall_sentiment", "neutral"),
                sentiment_score=float(parsed.get("sentiment_score", 0.0)),
                factors=factors,
                emotions=parsed.get("emotions", []),
                is_opinion=parsed.get("is_opinion", True),
                user_needs=parsed.get("user_needs", []),
                pain_points=parsed.get("pain_points", []),
            )

            logger.debug(
                "감성 분석 완료: %s (score=%.2f)",
                result.overall_sentiment,
                result.sentiment_score,
            )
            return result

        except Exception as e:
            logger.warning("감성 분석 실패: %s", e)
            return DeepSentimentResult(
                overall_sentiment="neutral",
                sentiment_score=0.0,
            )

    # =========================================================================
    # INSIGHT GENERATION
    # =========================================================================

    async def generate_insights(
        self,
        analysis_data: dict[str, Any],
        subreddit: str = "unknown",
        period: str = "last 7 days",
        temperature: float = 0.6,
    ) -> list[Insight]:
        """분석 결과에서 비즈니스 인사이트를 생성한다.

        Args:
            analysis_data: 분석 결과 데이터 (트렌드, 수요, 감성 등)
            subreddit: 분석 대상 서브레딧
            period: 분석 기간
            temperature: 창의성 조절

        Returns:
            Insight 목록

        Raises:
            LLMError: API 호출 실패 시
        """
        if not analysis_data:
            return []

        # 분석 데이터를 텍스트로 포맷팅
        data_text = self._format_analysis_data(analysis_data)

        template = get_template("extract_insights")
        prompt = template.format(
            analysis_data=data_text,
            subreddit=subreddit,
            period=period,
        )

        try:
            response = await self.client.complete_with_retry(
                prompt=prompt,
                max_retries=self.max_retries,
                temperature=temperature,
                max_tokens=2048,
            )

            # 마크다운 형식의 응답을 파싱
            insights = self._parse_insights_response(response)

            logger.info("인사이트 %d개 생성 완료", len(insights))
            return insights

        except Exception as e:
            logger.warning("인사이트 생성 실패: %s", e)
            return []

    # =========================================================================
    # TREND INTERPRETATION
    # =========================================================================

    async def interpret_trends(
        self,
        trend_data: dict[str, Any],
        rising_keywords: list[str],
        declining_keywords: list[str],
        target: str = "subreddit",
        comparison_period: str = "week over week",
        temperature: float = 0.5,
    ) -> str:
        """트렌드 데이터를 해석하고 인사이트를 제공한다.

        Args:
            trend_data: 트렌드 데이터 (시계열, 통계 등)
            rising_keywords: 상승 키워드 목록
            declining_keywords: 하락 키워드 목록
            target: 분석 대상
            comparison_period: 비교 기간
            temperature: 창의성 조절

        Returns:
            트렌드 해석 텍스트 (마크다운 형식)
        """
        template = get_template("trend_interpretation")
        prompt = template.format(
            trend_data=json.dumps(trend_data, indent=2, default=str),
            rising_keywords=", ".join(rising_keywords[:10]) or "없음",
            declining_keywords=", ".join(declining_keywords[:10]) or "없음",
            target=target,
            comparison_period=comparison_period,
        )

        try:
            response = await self.client.complete_with_retry(
                prompt=prompt,
                max_retries=self.max_retries,
                temperature=temperature,
                max_tokens=2048,
            )
            return response

        except Exception as e:
            logger.warning("트렌드 해석 실패: %s", e)
            return f"트렌드 해석 중 오류가 발생했습니다: {e}"

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _format_posts_for_prompt(self, posts: list[dict[str, Any]]) -> str:
        """게시물 목록을 프롬프트용 텍스트로 포맷팅한다."""
        formatted = []

        for i, post in enumerate(posts, 1):
            title = post.get("title", "제목 없음")
            body = post.get("body", post.get("selftext", ""))
            score = post.get("score", 0)
            comments = post.get("num_comments", post.get("comments", 0))

            # 본문이 너무 길면 축약
            if body and len(body) > 500:
                body = body[:500] + "..."

            formatted.append(
                f"### 게시물 {i}\n"
                f"**제목**: {title}\n"
                f"**점수**: {score} | **댓글**: {comments}\n"
                f"**내용**: {body or '(내용 없음)'}\n"
            )

        return "\n".join(formatted)

    def _format_analysis_data(self, data: dict[str, Any]) -> str:
        """분석 데이터를 프롬프트용 텍스트로 포맷팅한다."""
        sections = []

        if "trends" in data:
            sections.append(f"## 트렌드 분석\n{json.dumps(data['trends'], indent=2, default=str)}")

        if "demands" in data:
            sections.append(f"## 수요 분석\n{json.dumps(data['demands'], indent=2, default=str)}")

        if "sentiment" in data:
            sections.append(f"## 감성 분석\n{json.dumps(data['sentiment'], indent=2, default=str)}")

        if "competition" in data:
            sections.append(f"## 경쟁 분석\n{json.dumps(data['competition'], indent=2, default=str)}")

        return "\n\n".join(sections) if sections else json.dumps(data, indent=2, default=str)

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """LLM 응답에서 JSON을 추출하고 파싱한다."""
        # JSON 블록 추출 시도
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # 중괄호로 둘러싸인 부분 찾기
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning("JSON 파싱 실패: %s", e)
            return {}

    def _parse_insights_response(self, response: str) -> list[Insight]:
        """마크다운 형식의 인사이트 응답을 파싱한다."""
        insights = []

        # 인사이트 섹션 패턴
        pattern = r"### 인사이트 \d+:\s*(.+?)(?=### 인사이트|\Z)"
        matches = re.findall(pattern, response, re.DOTALL)

        for match in matches:
            lines = match.strip().split("\n")
            title = lines[0].strip() if lines else ""

            # 각 필드 추출
            finding = ""
            meaning = ""
            recommendation = ""
            priority = "medium"

            for line in lines[1:]:
                line = line.strip()
                if line.startswith("- **발견**:"):
                    finding = line.replace("- **발견**:", "").strip()
                elif line.startswith("- **의미**:"):
                    meaning = line.replace("- **의미**:", "").strip()
                elif line.startswith("- **권장 조치**:"):
                    recommendation = line.replace("- **권장 조치**:", "").strip()
                elif line.startswith("- **우선순위**:"):
                    priority_text = line.replace("- **우선순위**:", "").strip().lower()
                    if "높음" in priority_text or "high" in priority_text:
                        priority = "high"
                    elif "낮음" in priority_text or "low" in priority_text:
                        priority = "low"

            if title or finding:
                insights.append(
                    Insight(
                        title=title,
                        finding=finding,
                        meaning=meaning,
                        recommendation=recommendation,
                        priority=priority,
                    )
                )

        return insights

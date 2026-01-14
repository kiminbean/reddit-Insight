"""프롬프트 템플릿 시스템.

LLM 분석에 사용되는 프롬프트 템플릿을 관리한다.
버전 관리와 A/B 테스트를 지원한다.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PromptCategory(Enum):
    """프롬프트 카테고리."""

    SUMMARIZATION = "summarization"
    CATEGORIZATION = "categorization"
    EXTRACTION = "extraction"
    SENTIMENT = "sentiment"
    TREND = "trend"
    GENERAL = "general"


@dataclass
class PromptTemplate:
    """프롬프트 템플릿.

    LLM에 전달할 프롬프트를 관리하고 포맷팅한다.

    Attributes:
        template: 프롬프트 템플릿 문자열 ({변수} 형태의 플레이스홀더 포함)
        version: 템플릿 버전 (A/B 테스트용)
        category: 템플릿 카테고리
        description: 템플릿 설명
        required_vars: 필수 변수 목록 (자동 추출)
    """

    template: str
    version: str = "1.0"
    category: PromptCategory = PromptCategory.GENERAL
    description: str = ""
    required_vars: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """필수 변수를 자동으로 추출한다."""
        if not self.required_vars:
            # {변수명} 패턴 추출
            self.required_vars = re.findall(r"\{(\w+)\}", self.template)

    def format(self, **kwargs: str) -> str:
        """템플릿에 변수를 대입한다.

        Args:
            **kwargs: 템플릿 변수

        Returns:
            포맷된 프롬프트 문자열

        Raises:
            ValueError: 필수 변수가 누락된 경우
        """
        missing = set(self.required_vars) - set(kwargs.keys())
        if missing:
            raise ValueError(f"필수 변수 누락: {missing}")

        return self.template.format(**kwargs)

    def estimate_tokens(self, **kwargs: str) -> int:
        """포맷된 프롬프트의 토큰 수를 추정한다.

        Args:
            **kwargs: 템플릿 변수

        Returns:
            추정 토큰 수
        """
        formatted = self.format(**kwargs)
        # 약 3글자 = 1토큰 (보수적 추정)
        return max(1, len(formatted) // 3)

    def get_hash(self) -> str:
        """템플릿의 해시 값을 반환한다 (버전 관리용).

        Returns:
            SHA256 해시의 처음 16자
        """
        content = f"{self.template}:{self.version}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def __repr__(self) -> str:
        return (
            f"PromptTemplate(category={self.category.value}, "
            f"version={self.version}, vars={self.required_vars})"
        )


# =============================================================================
# 분석용 프롬프트 템플릿
# =============================================================================

SUMMARIZE_POSTS = PromptTemplate(
    template="""다음 Reddit 게시물들을 분석하고 요약해주세요.

## 게시물 목록
{posts}

## 요구사항
1. 주요 주제 3-5개를 식별하세요
2. 각 주제에 대해 핵심 논의 내용을 1-2문장으로 요약하세요
3. 전반적인 커뮤니티 의견 동향을 파악하세요
4. 주목할 만한 특이점이나 인사이트가 있다면 언급하세요

## 출력 형식
### 주요 주제
1. [주제1]: [요약]
2. [주제2]: [요약]
...

### 커뮤니티 동향
[전반적인 의견 동향 설명]

### 인사이트
[주목할 만한 점들]""",
    version="1.0",
    category=PromptCategory.SUMMARIZATION,
    description="여러 Reddit 게시물을 종합하여 주제별로 요약",
)


CATEGORIZE_CONTENT = PromptTemplate(
    template="""다음 텍스트를 분석하고 적절한 카테고리로 분류해주세요.

## 텍스트
{text}

## 사용 가능한 카테고리
{categories}

## 요구사항
1. 가장 적합한 카테고리 1개를 선택하세요
2. 선택 이유를 간단히 설명하세요
3. 해당 카테고리와의 관련성 점수(0-100)를 부여하세요
4. 다른 관련 카테고리가 있다면 2순위, 3순위도 언급하세요

## 출력 형식 (JSON)
{{
    "primary_category": "카테고리명",
    "confidence": 85,
    "reason": "선택 이유",
    "secondary_categories": [
        {{"category": "카테고리명", "confidence": 60}}
    ]
}}""",
    version="1.0",
    category=PromptCategory.CATEGORIZATION,
    description="텍스트를 주어진 카테고리 중 하나로 분류",
)


EXTRACT_INSIGHTS = PromptTemplate(
    template="""다음 분석 결과에서 비즈니스 인사이트를 추출해주세요.

## 분석 데이터
{analysis_data}

## 도메인 컨텍스트
서브레딧: {subreddit}
분석 기간: {period}

## 요구사항
1. 실행 가능한(actionable) 인사이트 3-5개를 도출하세요
2. 각 인사이트에 대해:
   - 발견 내용 (무엇이 관찰되었는가)
   - 의미 (왜 이것이 중요한가)
   - 권장 조치 (무엇을 해야 하는가)
   - 우선순위 (높음/중간/낮음)

## 출력 형식
### 인사이트 1: [제목]
- **발견**: [관찰된 패턴/트렌드]
- **의미**: [비즈니스적 중요성]
- **권장 조치**: [구체적인 액션 아이템]
- **우선순위**: [높음/중간/낮음]

### 인사이트 2: [제목]
...""",
    version="1.0",
    category=PromptCategory.EXTRACTION,
    description="분석 결과에서 실행 가능한 비즈니스 인사이트 추출",
)


SENTIMENT_ANALYSIS = PromptTemplate(
    template="""다음 텍스트의 감성을 심층 분석해주세요.

## 텍스트
{text}

## 요구사항
1. 전체적인 감성 판정 (긍정/중립/부정)
2. 감성 강도 점수 (-1.0 ~ +1.0)
3. 주요 감성 요인 3개 이상 식별
4. 텍스트에서 감지되는 감정 (분노, 기쁨, 슬픔, 불안, 흥분 등)
5. 의견인지 사실인지 구분
6. 잠재적인 사용자 니즈나 불만 파악

## 출력 형식 (JSON)
{{
    "overall_sentiment": "positive|neutral|negative",
    "sentiment_score": 0.75,
    "factors": [
        {{"aspect": "가격", "sentiment": "negative", "reason": "비싸다는 언급"}},
        {{"aspect": "품질", "sentiment": "positive", "reason": "만족한다는 표현"}}
    ],
    "emotions": ["frustration", "hope"],
    "is_opinion": true,
    "user_needs": ["더 저렴한 가격", "빠른 배송"],
    "pain_points": ["높은 가격", "느린 고객 서비스"]
}}""",
    version="1.0",
    category=PromptCategory.SENTIMENT,
    description="텍스트의 감성과 감정을 심층 분석",
)


TREND_INTERPRETATION = PromptTemplate(
    template="""다음 트렌드 데이터를 해석하고 인사이트를 제공해주세요.

## 트렌드 데이터
{trend_data}

## 키워드 정보
상승 키워드: {rising_keywords}
하락 키워드: {declining_keywords}

## 도메인 컨텍스트
분석 대상: {target}
비교 기간: {comparison_period}

## 요구사항
1. 주요 트렌드 변화 요약 (3-5개)
2. 각 트렌드의 원인 추론
3. 향후 예측 (다음 주/월 전망)
4. 비즈니스 기회 또는 위험 식별
5. 권장 대응 전략

## 출력 형식
### 트렌드 요약
1. [트렌드1]: [설명]
2. [트렌드2]: [설명]
...

### 원인 분석
- [트렌드1]의 원인: [추론]
- [트렌드2]의 원인: [추론]

### 향후 전망
[다음 기간 예측]

### 기회 & 위험
- 기회: [기회 설명]
- 위험: [위험 설명]

### 권장 전략
1. [전략1]
2. [전략2]""",
    version="1.0",
    category=PromptCategory.TREND,
    description="트렌드 데이터 해석 및 비즈니스 인사이트 도출",
)


# 템플릿 레지스트리
TEMPLATES: dict[str, PromptTemplate] = {
    "summarize_posts": SUMMARIZE_POSTS,
    "categorize_content": CATEGORIZE_CONTENT,
    "extract_insights": EXTRACT_INSIGHTS,
    "sentiment_analysis": SENTIMENT_ANALYSIS,
    "trend_interpretation": TREND_INTERPRETATION,
}


def get_template(name: str) -> PromptTemplate:
    """이름으로 템플릿을 조회한다.

    Args:
        name: 템플릿 이름

    Returns:
        PromptTemplate 인스턴스

    Raises:
        KeyError: 존재하지 않는 템플릿 이름
    """
    if name not in TEMPLATES:
        available = ", ".join(TEMPLATES.keys())
        raise KeyError(f"템플릿 '{name}'을 찾을 수 없습니다. 사용 가능: {available}")
    return TEMPLATES[name]


def list_templates() -> list[dict[str, str]]:
    """모든 템플릿 목록을 반환한다.

    Returns:
        템플릿 정보 목록
    """
    return [
        {
            "name": name,
            "category": tpl.category.value,
            "version": tpl.version,
            "description": tpl.description,
            "required_vars": tpl.required_vars,
        }
        for name, tpl in TEMPLATES.items()
    ]


def register_template(name: str, template: PromptTemplate) -> None:
    """새 템플릿을 등록한다.

    Args:
        name: 템플릿 이름
        template: PromptTemplate 인스턴스
    """
    if name in TEMPLATES:
        logger.warning("템플릿 '%s'를 덮어씁니다", name)
    TEMPLATES[name] = template
    logger.info("템플릿 '%s' 등록됨 (version=%s)", name, template.version)

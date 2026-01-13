"""
Report Templates Module.

마크다운 리포트 템플릿 시스템을 제공한다.
Jinja2 기반의 템플릿과 마크다운 유틸리티 함수를 포함한다.

Example:
    >>> from reddit_insight.reports import TemplateRegistry, ReportType
    >>> registry = TemplateRegistry()
    >>> registry.load_defaults()
    >>> template = registry.get("trend_report")
    >>> print(template.report_type)
    ReportType.TREND
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

try:
    from jinja2 import Environment, BaseLoader
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False


class ReportType(Enum):
    """리포트 유형 열거형.

    Attributes:
        TREND: 트렌드 분석 리포트
        DEMAND: 수요 분석 리포트
        COMPETITIVE: 경쟁 분석 리포트
        INSIGHT: 비즈니스 인사이트 리포트
        FULL: 종합 리포트
    """
    TREND = "trend"
    DEMAND = "demand"
    COMPETITIVE = "competitive"
    INSIGHT = "insight"
    FULL = "full"


@dataclass
class ReportTemplate:
    """리포트 템플릿 데이터 클래스.

    Attributes:
        name: 템플릿 이름 (고유 식별자)
        report_type: 리포트 유형
        template_string: Jinja2 템플릿 문자열
        description: 템플릿 설명
        variables: 필수 변수 목록
    """
    name: str
    report_type: ReportType
    template_string: str
    description: str = ""
    variables: list[str] = field(default_factory=list)

    def render(self, **context: Any) -> str:
        """템플릿을 렌더링한다.

        Args:
            **context: 템플릿 변수들

        Returns:
            렌더링된 마크다운 문자열

        Raises:
            ImportError: Jinja2가 설치되지 않은 경우
        """
        if not JINJA2_AVAILABLE:
            raise ImportError(
                "Jinja2 is required for template rendering. "
                "Install with: pip install jinja2"
            )

        env = Environment(loader=BaseLoader())
        # 헬퍼 함수를 템플릿 전역에 추가
        env.globals.update({
            'format_table': format_table,
            'format_list': format_list,
            'format_badge': format_badge,
            'format_percentage': format_percentage,
            'format_score': format_score,
            'format_date': format_date,
            'format_trend': format_trend,
            'text_bar': text_bar,
            'text_sparkline': text_sparkline,
        })

        template = env.from_string(self.template_string)
        return template.render(**context)


class TemplateRegistry:
    """템플릿 레지스트리.

    템플릿을 등록하고 관리하는 싱글톤 패턴 클래스.

    Example:
        >>> registry = TemplateRegistry()
        >>> registry.load_defaults()
        >>> template = registry.get("trend_report")
    """

    def __init__(self) -> None:
        """레지스트리를 초기화한다."""
        self._templates: dict[str, ReportTemplate] = {}

    def register(self, template: ReportTemplate) -> None:
        """템플릿을 등록한다.

        Args:
            template: 등록할 템플릿
        """
        self._templates[template.name] = template

    def get(self, name: str) -> ReportTemplate:
        """이름으로 템플릿을 가져온다.

        Args:
            name: 템플릿 이름

        Returns:
            해당 템플릿

        Raises:
            KeyError: 템플릿이 없는 경우
        """
        if name not in self._templates:
            raise KeyError(f"Template not found: {name}")
        return self._templates[name]

    def list_templates(self) -> list[ReportTemplate]:
        """등록된 모든 템플릿을 반환한다.

        Returns:
            템플릿 리스트
        """
        return list(self._templates.values())

    def list_by_type(self, report_type: ReportType) -> list[ReportTemplate]:
        """특정 유형의 템플릿만 반환한다.

        Args:
            report_type: 리포트 유형

        Returns:
            해당 유형의 템플릿 리스트
        """
        return [t for t in self._templates.values() if t.report_type == report_type]

    def load_defaults(self) -> None:
        """기본 템플릿들을 로드한다."""
        for template in DEFAULT_TEMPLATES:
            self.register(template)


# =============================================================================
# Markdown Helper Functions
# =============================================================================

def format_table(headers: list[str], rows: list[list[str]]) -> str:
    """마크다운 테이블을 생성한다.

    Args:
        headers: 헤더 리스트
        rows: 행 데이터 리스트

    Returns:
        마크다운 테이블 문자열

    Example:
        >>> print(format_table(["Name", "Score"], [["A", "90"], ["B", "85"]]))
        | Name | Score |
        |------|-------|
        | A | 90 |
        | B | 85 |
    """
    if not headers:
        return ""

    # 헤더 행
    header_row = "| " + " | ".join(str(h) for h in headers) + " |"

    # 구분선 (각 열의 최소 너비 3)
    separator = "| " + " | ".join("-" * max(3, len(str(h))) for h in headers) + " |"

    # 데이터 행
    data_rows = []
    for row in rows:
        # 행의 길이가 헤더보다 짧으면 빈 문자열로 채움
        padded = list(row) + [""] * (len(headers) - len(row))
        data_rows.append("| " + " | ".join(str(cell) for cell in padded[:len(headers)]) + " |")

    return "\n".join([header_row, separator] + data_rows)


def format_list(items: list[str], ordered: bool = False) -> str:
    """마크다운 리스트를 생성한다.

    Args:
        items: 항목 리스트
        ordered: 순서 있는 리스트 여부

    Returns:
        마크다운 리스트 문자열

    Example:
        >>> print(format_list(["First", "Second"], ordered=True))
        1. First
        2. Second
    """
    if not items:
        return ""

    if ordered:
        return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
    else:
        return "\n".join(f"- {item}" for item in items)


def format_badge(text: str, color: str = "blue") -> str:
    """마크다운 뱃지를 생성한다.

    GitHub/shields.io 스타일 뱃지를 생성한다.

    Args:
        text: 뱃지 텍스트
        color: 뱃지 색상

    Returns:
        뱃지 마크다운 (이미지 링크)

    Example:
        >>> print(format_badge("v1.0", "green"))
        ![v1.0](https://img.shields.io/badge/v1.0-green)
    """
    # 공백을 %20으로 인코딩
    encoded_text = text.replace(" ", "%20").replace("-", "--")
    return f"![{text}](https://img.shields.io/badge/{encoded_text}-{color})"


def format_percentage(value: float, decimals: int = 1) -> str:
    """퍼센트 형식으로 변환한다.

    Args:
        value: 0-1 사이의 값 또는 0-100 사이의 값
        decimals: 소수점 자릿수

    Returns:
        퍼센트 문자열

    Example:
        >>> format_percentage(0.854)
        '85.4%'
        >>> format_percentage(85.4)
        '85.4%'
    """
    # 1 이하면 비율로 간주, 아니면 이미 퍼센트
    if 0 <= value <= 1:
        value *= 100
    return f"{value:.{decimals}f}%"


def format_score(value: float, max_value: float = 100) -> str:
    """스코어를 형식화한다.

    Args:
        value: 스코어 값
        max_value: 최대 값

    Returns:
        형식화된 스코어 문자열

    Example:
        >>> format_score(85)
        '85/100'
        >>> format_score(4.2, 5)
        '4.2/5'
    """
    if max_value == int(max_value) and value == int(value):
        return f"{int(value)}/{int(max_value)}"
    return f"{value:.1f}/{max_value:.0f}"


def format_date(dt: datetime | None = None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """날짜를 형식화한다.

    Args:
        dt: datetime 객체 (None이면 현재 시각)
        fmt: 날짜 형식 문자열

    Returns:
        형식화된 날짜 문자열

    Example:
        >>> format_date(datetime(2025, 1, 13))
        '2025-01-13 00:00'
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)


def format_trend(direction: str) -> str:
    """트렌드 방향을 화살표로 변환한다.

    Args:
        direction: 트렌드 방향 ('up', 'down', 'stable', 'rising', 'falling')

    Returns:
        화살표 문자

    Example:
        >>> format_trend('up')
        '↑'
        >>> format_trend('down')
        '↓'
    """
    direction_lower = direction.lower()
    if direction_lower in ('up', 'rising', 'increase'):
        return '↑'
    elif direction_lower in ('down', 'falling', 'decrease'):
        return '↓'
    else:
        return '→'


def text_bar(value: float, width: int = 20, filled: str = '█', empty: str = '░') -> str:
    """텍스트 기반 막대 그래프를 생성한다.

    Args:
        value: 0-100 사이의 값 (또는 0-1)
        width: 막대 너비
        filled: 채워진 부분 문자
        empty: 빈 부분 문자

    Returns:
        텍스트 막대 문자열

    Example:
        >>> text_bar(75)
        '███████████████░░░░░'
        >>> text_bar(0.5, width=10)
        '█████░░░░░'
    """
    # 0-1 범위면 100 곱하기
    if 0 <= value <= 1:
        value *= 100

    # 값 범위 제한
    value = max(0, min(100, value))

    filled_count = int(round(value / 100 * width))
    empty_count = width - filled_count

    return filled * filled_count + empty * empty_count


def text_sparkline(values: list[float], chars: str = '▁▂▃▄▅▆▇█') -> str:
    """텍스트 기반 스파크라인을 생성한다.

    Args:
        values: 숫자 리스트
        chars: 높이별 문자 (낮은 것부터 높은 것 순)

    Returns:
        스파크라인 문자열

    Example:
        >>> text_sparkline([1, 3, 7, 2, 5])
        '▁▃█▂▅'
    """
    if not values:
        return ""

    min_val = min(values)
    max_val = max(values)

    # 모든 값이 같으면 중간 문자 반환
    if max_val == min_val:
        mid_char = chars[len(chars) // 2]
        return mid_char * len(values)

    result = []
    for v in values:
        # 0-1로 정규화
        normalized = (v - min_val) / (max_val - min_val)
        # 인덱스 계산 (0 ~ len(chars)-1)
        idx = int(normalized * (len(chars) - 1))
        idx = max(0, min(len(chars) - 1, idx))
        result.append(chars[idx])

    return "".join(result)


# =============================================================================
# Default Templates
# =============================================================================

TREND_REPORT_TEMPLATE = ReportTemplate(
    name="trend_report",
    report_type=ReportType.TREND,
    description="트렌드 분석 리포트 - 키워드 트렌드와 상승 키워드를 보여줍니다.",
    variables=["title", "summary", "top_keywords", "rising_keywords", "period"],
    template_string="""# {{ title }}

> 생성일: {{ format_date() }}
> 분석 기간: {{ period.start if period else 'N/A' }} ~ {{ period.end if period else 'N/A' }}

## 요약

{{ summary }}

## 상위 키워드

{% if top_keywords %}
| 순위 | 키워드 | 점수 | 트렌드 |
|------|--------|------|--------|
{% for kw in top_keywords[:10] %}
| {{ loop.index }} | {{ kw.keyword }} | {{ "%.2f"|format(kw.score) }} | {{ format_trend(kw.trend_direction) if kw.trend_direction else '→' }} |
{% endfor %}
{% else %}
분석된 키워드가 없습니다.
{% endif %}

## 상승 키워드 (Rising)

{% if rising_keywords %}
{% for kw in rising_keywords[:10] %}
### {{ loop.index }}. {{ kw.keyword }}

- **점수**: {{ text_bar(kw.score) }} {{ "%.1f"|format(kw.score) }}
- **트렌드**: {{ format_trend(kw.trend_direction) if kw.trend_direction else '→' }}
{% if kw.context %}
- **맥락**: {{ kw.context }}
{% endif %}

{% endfor %}
{% else %}
상승 중인 키워드가 없습니다.
{% endif %}

## 트렌드 변화 요약

{% if trend_changes %}
{{ format_list(trend_changes) }}
{% else %}
주목할 만한 트렌드 변화가 없습니다.
{% endif %}

---
*이 리포트는 Reddit Insight에 의해 자동 생성되었습니다.*
"""
)

DEMAND_REPORT_TEMPLATE = ReportTemplate(
    name="demand_report",
    report_type=ReportType.DEMAND,
    description="수요 분석 리포트 - 사용자 수요 패턴과 우선순위를 분석합니다.",
    variables=["title", "total_demands", "categories", "top_demands", "priority_analysis"],
    template_string="""# {{ title }}

> 생성일: {{ format_date() }}

## 수요 요약 통계

| 지표 | 값 |
|------|-----|
| 총 수요 | {{ total_demands }} |
| 카테고리 수 | {{ categories | length if categories else 0 }} |
| 분석 포스트 수 | {{ analyzed_posts if analyzed_posts else 'N/A' }} |

## 카테고리별 분포

{% if categories %}
{% for cat, count in categories.items() %}
- **{{ cat }}**: {{ count }} ({{ format_percentage(count / total_demands if total_demands > 0 else 0) }})
  {{ text_bar(count / total_demands * 100 if total_demands > 0 else 0, width=30) }}
{% endfor %}
{% else %}
카테고리 데이터가 없습니다.
{% endif %}

## 상위 수요 목록

{% if top_demands %}
{% for demand in top_demands[:15] %}
### {{ loop.index }}. {{ demand.title if demand.title else demand.description[:50] }}

- **카테고리**: {{ demand.category }}
- **빈도**: {{ demand.frequency if demand.frequency else 'N/A' }}
- **우선순위 점수**: {{ text_bar(demand.priority_score if demand.priority_score else 50) }} {{ demand.priority_score | round(1) if demand.priority_score else '-' }}
{% if demand.sample_text %}
> "{{ demand.sample_text[:200] }}..."
{% endif %}

{% endfor %}
{% else %}
분석된 수요가 없습니다.
{% endif %}

## 우선순위 분석

{% if priority_analysis %}
### 즉시 대응 필요 (High Priority)
{{ format_list(priority_analysis.high if priority_analysis.high else ['해당 없음']) }}

### 중간 우선순위 (Medium Priority)
{{ format_list(priority_analysis.medium if priority_analysis.medium else ['해당 없음']) }}

### 모니터링 (Low Priority)
{{ format_list(priority_analysis.low if priority_analysis.low else ['해당 없음']) }}
{% else %}
우선순위 분석 데이터가 없습니다.
{% endif %}

---
*이 리포트는 Reddit Insight에 의해 자동 생성되었습니다.*
"""
)

COMPETITIVE_REPORT_TEMPLATE = ReportTemplate(
    name="competitive_report",
    report_type=ReportType.COMPETITIVE,
    description="경쟁 분석 리포트 - 제품/서비스에 대한 감성과 불만을 분석합니다.",
    variables=["title", "entities", "sentiment_summary", "complaints", "alternatives"],
    template_string="""# {{ title }}

> 생성일: {{ format_date() }}

## 분석 대상 엔티티

{% if entities %}
{% for entity in entities %}
- **{{ entity.name }}** ({{ entity.type if entity.type else 'Product/Service' }})
  - 언급 수: {{ entity.mention_count if entity.mention_count else 'N/A' }}
  - 평균 감성: {{ format_percentage(entity.avg_sentiment if entity.avg_sentiment else 0.5) }}
{% endfor %}
{% else %}
분석된 엔티티가 없습니다.
{% endif %}

## 감성 분석 요약

{% if sentiment_summary %}
| 감성 | 비율 | 시각화 |
|------|------|--------|
| 긍정 | {{ format_percentage(sentiment_summary.positive if sentiment_summary.positive else 0) }} | {{ text_bar(sentiment_summary.positive * 100 if sentiment_summary.positive else 0, width=15) }} |
| 중립 | {{ format_percentage(sentiment_summary.neutral if sentiment_summary.neutral else 0) }} | {{ text_bar(sentiment_summary.neutral * 100 if sentiment_summary.neutral else 0, width=15) }} |
| 부정 | {{ format_percentage(sentiment_summary.negative if sentiment_summary.negative else 0) }} | {{ text_bar(sentiment_summary.negative * 100 if sentiment_summary.negative else 0, width=15) }} |
{% else %}
감성 분석 데이터가 없습니다.
{% endif %}

## 주요 불만 목록

{% if complaints %}
{% for complaint in complaints[:10] %}
### {{ loop.index }}. {{ complaint.type if complaint.type else 'General' }}

- **심각도**: {{ text_bar(complaint.severity * 100 if complaint.severity else 50, width=10) }}
- **빈도**: {{ complaint.frequency if complaint.frequency else 'N/A' }}
{% if complaint.examples %}
- **예시**:
{% for ex in complaint.examples[:3] %}
  > "{{ ex[:150] }}..."
{% endfor %}
{% endif %}

{% endfor %}
{% else %}
주요 불만 데이터가 없습니다.
{% endif %}

## 대안/전환 패턴

{% if alternatives %}
| 기존 제품 | 대안 | 전환 이유 | 빈도 |
|----------|------|----------|------|
{% for alt in alternatives[:10] %}
| {{ alt.from_product if alt.from_product else '-' }} | {{ alt.to_product if alt.to_product else '-' }} | {{ alt.reason if alt.reason else '-' }} | {{ alt.frequency if alt.frequency else '-' }} |
{% endfor %}
{% else %}
대안/전환 패턴 데이터가 없습니다.
{% endif %}

---
*이 리포트는 Reddit Insight에 의해 자동 생성되었습니다.*
"""
)

INSIGHT_REPORT_TEMPLATE = ReportTemplate(
    name="insight_report",
    report_type=ReportType.INSIGHT,
    description="비즈니스 인사이트 리포트 - 기회와 권장 액션을 제시합니다.",
    variables=["title", "insights", "opportunities", "recommendations", "feasibility"],
    template_string="""# {{ title }}

> 생성일: {{ format_date() }}

## 핵심 인사이트 요약

{% if insights %}
{% for insight in insights[:5] %}
### {{ insight.title if insight.title else 'Insight ' ~ loop.index }}

- **유형**: {{ insight.type if insight.type else 'General' }}
- **신뢰도**: {{ format_percentage(insight.confidence if insight.confidence else 0) }}
- **영향도**: {{ text_bar(insight.impact * 100 if insight.impact else 50, width=15) }}

{{ insight.description if insight.description else '' }}

{% if insight.evidence %}
**근거**:
{{ format_list(insight.evidence) }}
{% endif %}

{% endfor %}
{% else %}
도출된 인사이트가 없습니다.
{% endif %}

## 기회 랭킹

{% if opportunities %}
| 순위 | 기회 | 점수 | 등급 |
|------|-----|------|------|
{% for opp in opportunities[:10] %}
| {{ opp.rank if opp.rank else loop.index }} | {{ opp.title if opp.title else opp.insight.title if opp.insight else '-' }} | {{ format_score(opp.score.total if opp.score else opp.total_score if opp.total_score else 0) }} | {{ opp.grade if opp.grade else opp.score.grade if opp.score else '-' }} |
{% endfor %}
{% else %}
랭킹된 기회가 없습니다.
{% endif %}

## 추천 액션

{% if recommendations %}
{% for rec in recommendations %}
### {{ rec.title if rec.title else 'Action ' ~ loop.index }}

- **우선순위**: {{ rec.priority if rec.priority else 'Medium' }}
- **예상 효과**: {{ rec.expected_impact if rec.expected_impact else 'N/A' }}
- **필요 리소스**: {{ rec.resources if rec.resources else 'N/A' }}

{{ rec.description if rec.description else '' }}

{% if rec.steps %}
**실행 단계**:
{{ format_list(rec.steps, ordered=True) }}
{% endif %}

{% endfor %}
{% else %}
추천 액션이 없습니다.
{% endif %}

## 실행 가능성 분석

{% if feasibility %}
| 요소 | 평가 | 점수 |
|------|------|------|
{% for factor, assessment in feasibility.items() if feasibility is mapping %}
| {{ factor }} | {{ assessment.level if assessment.level else assessment }} | {{ text_bar(assessment.score * 100 if assessment.score else 50, width=10) }} |
{% endfor %}
{% else %}
실행 가능성 분석 데이터가 없습니다.
{% endif %}

---
*이 리포트는 Reddit Insight에 의해 자동 생성되었습니다.*
"""
)

FULL_REPORT_TEMPLATE = ReportTemplate(
    name="full_report",
    report_type=ReportType.FULL,
    description="종합 리포트 - 모든 분석 결과를 통합하여 제시합니다.",
    variables=["title", "executive_summary", "trend_section", "demand_section",
               "competitive_section", "insight_section", "conclusions"],
    template_string="""# {{ title }}

> 생성일: {{ format_date() }}
> 분석 유형: 종합 분석 리포트

---

## Executive Summary

{{ executive_summary if executive_summary else '요약 정보가 제공되지 않았습니다.' }}

---

## 1. 트렌드 분석

{% if trend_section %}
### 주요 발견

{{ trend_section.summary if trend_section.summary else '' }}

### 상위 키워드
{% if trend_section.top_keywords %}
| 키워드 | 점수 | 트렌드 |
|--------|------|--------|
{% for kw in trend_section.top_keywords[:5] %}
| {{ kw.keyword }} | {{ "%.2f"|format(kw.score) }} | {{ format_trend(kw.trend_direction if kw.trend_direction else 'stable') }} |
{% endfor %}
{% endif %}

### 주목할 상승 키워드
{% if trend_section.rising_keywords %}
{% for kw in trend_section.rising_keywords[:5] %}
- {{ kw.keyword }} ({{ format_trend('up') }} {{ "%.1f"|format(kw.score) }})
{% endfor %}
{% endif %}
{% else %}
트렌드 분석 데이터가 없습니다.
{% endif %}

---

## 2. 수요 분석

{% if demand_section %}
### 수요 개요

- 총 수요 수: {{ demand_section.total_demands if demand_section.total_demands else 'N/A' }}
- 주요 카테고리: {{ demand_section.top_category if demand_section.top_category else 'N/A' }}

### 상위 수요
{% if demand_section.top_demands %}
{% for demand in demand_section.top_demands[:5] %}
{{ loop.index }}. **{{ demand.title if demand.title else demand.description[:40] if demand.description else 'N/A' }}** ({{ demand.category if demand.category else 'N/A' }})
{% endfor %}
{% endif %}
{% else %}
수요 분석 데이터가 없습니다.
{% endif %}

---

## 3. 경쟁 분석

{% if competitive_section %}
### 감성 분포

{% if competitive_section.sentiment_summary %}
- 긍정: {{ format_percentage(competitive_section.sentiment_summary.positive if competitive_section.sentiment_summary.positive else 0) }}
- 부정: {{ format_percentage(competitive_section.sentiment_summary.negative if competitive_section.sentiment_summary.negative else 0) }}
{% endif %}

### 주요 불만
{% if competitive_section.top_complaints %}
{% for c in competitive_section.top_complaints[:5] %}
- {{ c.type }}: {{ c.description[:50] if c.description else '' }}
{% endfor %}
{% endif %}
{% else %}
경쟁 분석 데이터가 없습니다.
{% endif %}

---

## 4. 비즈니스 인사이트

{% if insight_section %}
### 핵심 인사이트
{% if insight_section.top_insights %}
{% for insight in insight_section.top_insights[:3] %}
- **{{ insight.title if insight.title else 'Insight ' ~ loop.index }}**: {{ insight.description[:100] if insight.description else '' }}...
{% endfor %}
{% endif %}

### 기회 순위
{% if insight_section.opportunities %}
| 순위 | 기회 | 점수 |
|------|------|------|
{% for opp in insight_section.opportunities[:5] %}
| {{ opp.rank if opp.rank else loop.index }} | {{ opp.title if opp.title else '-' }} | {{ format_score(opp.total_score if opp.total_score else 0) }} |
{% endfor %}
{% endif %}
{% else %}
비즈니스 인사이트 데이터가 없습니다.
{% endif %}

---

## 5. 결론 및 권장사항

{% if conclusions %}
### 주요 결론
{{ format_list(conclusions.key_findings if conclusions.key_findings else []) }}

### 권장 액션
{% if conclusions.recommendations %}
{% for rec in conclusions.recommendations %}
{{ loop.index }}. **{{ rec.title if rec.title else 'Action ' ~ loop.index }}** ({{ rec.priority if rec.priority else 'Medium' }})
   {{ rec.description if rec.description else '' }}
{% endfor %}
{% endif %}

### 다음 단계
{{ format_list(conclusions.next_steps if conclusions.next_steps else ['추가 분석 필요'], ordered=True) }}
{% else %}
결론 및 권장사항이 제공되지 않았습니다.
{% endif %}

---

## 부록

### 분석 방법론
- 데이터 소스: Reddit
- 분석 기간: {{ analysis_period if analysis_period else 'N/A' }}
- 분석 도구: Reddit Insight

### 한계점
- 이 분석은 Reddit 데이터에 기반하며, 전체 시장을 대표하지 않을 수 있습니다.
- 감성 분석은 자동화된 알고리즘에 기반하여 일부 오류가 있을 수 있습니다.

---
*이 리포트는 Reddit Insight에 의해 자동 생성되었습니다.*
"""
)

# 기본 템플릿 목록
DEFAULT_TEMPLATES: list[ReportTemplate] = [
    TREND_REPORT_TEMPLATE,
    DEMAND_REPORT_TEMPLATE,
    COMPETITIVE_REPORT_TEMPLATE,
    INSIGHT_REPORT_TEMPLATE,
    FULL_REPORT_TEMPLATE,
]

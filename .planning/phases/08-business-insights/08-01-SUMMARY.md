---
phase: 08-business-insights
plan: 01
status: completed
completed_at: 2026-01-13
---

# Plan 08-01 Summary: Insight Rules Engine

## Objective Achieved

인사이트 생성 규칙 엔진을 구현하여 수요 분석과 경쟁 분석 결과를 결합한 비즈니스 인사이트 자동 생성 기능을 완성했다.

## Implementation Details

### Task 1: Insight Data Structures

**Files Created**:
- `src/reddit_insight/insights/__init__.py`
- `src/reddit_insight/insights/rules_engine.py`

**Components**:

1. **InsightType (Enum)**: 5가지 인사이트 유형 정의
   - `MARKET_GAP`: 시장 공백 (수요 있으나 공급 부족)
   - `IMPROVEMENT_OPPORTUNITY`: 개선 기회 (불만 많은 기존 제품)
   - `EMERGING_TREND`: 떠오르는 트렌드 (급상승 키워드)
   - `COMPETITIVE_WEAKNESS`: 경쟁사 약점
   - `UNMET_NEED`: 미충족 수요

2. **InsightEvidence**: 인사이트 근거 데이터
   - `source_type`: 근거 출처 유형
   - `source_id`: 근거 식별자
   - `summary`: 근거 요약
   - `weight`: 근거 가중치

3. **Insight**: 비즈니스 인사이트 데이터 클래스
   - `insight_id`: 고유 식별자
   - `insight_type`: 인사이트 유형
   - `title`, `description`: 제목과 설명
   - `evidence`: 근거 목록
   - `confidence`, `priority`: 신뢰도와 우선순위
   - `related_entities`, `related_demands`: 관련 데이터

### Task 2: Insight Rules Definition

**Components**:

1. **InsightRule**: 조건-결론 패턴 규칙
   - `rule_id`, `name`: 규칙 식별 정보
   - `insight_type`: 생성되는 인사이트 유형
   - `condition`: 조건 함수 (AnalysisContext -> bool)
   - `generate`: 생성 함수 (AnalysisContext -> Insight)
   - `priority`: 규칙 우선순위

2. **AnalysisContext**: 분석 결과 통합 컨텍스트
   - `demands`: PrioritizedDemand 목록
   - `complaints`: Complaint 목록
   - `entity_sentiments`: 엔티티별 감성
   - `rising_keywords`: RisingScore 목록
   - `alternatives`: AlternativeComparison 목록

3. **DEFAULT_RULES**: 5가지 기본 규칙
   - Market Gap Rule: 높은 수요 + 낮은 공급 탐지
   - Improvement Opportunity Rule: 불만 + 대안 탐색 탐지
   - Emerging Trend Rule: 급상승 키워드 탐지
   - Competitive Weakness Rule: 부정 감성 + 대안 탐지
   - Unmet Need Rule: 구매 의향 신호 탐지

### Task 3: Rules Engine Implementation

**RulesEngine Class**:
- `__init__(rules)`: 규칙 목록으로 초기화
- `add_rule(rule)`: 규칙 추가
- `remove_rule(rule_id)`: 규칙 제거
- `get_rules()`: 규칙 목록 반환
- `load_default_rules()`: 기본 규칙 로드
- `evaluate_rule(rule, context)`: 단일 규칙 평가
- `generate_insights(context, max_insights)`: 인사이트 생성
- `build_context(demand_report, competitive_report, trend_report)`: 컨텍스트 구축
- `to_markdown(insights)`: 마크다운 변환
- `to_dict(insights)`: 딕셔너리 변환

### Task 4: Exports and Verification

**__init__.py Exports**:
```python
__all__ = [
    "InsightType",
    "Insight",
    "InsightEvidence",
    "InsightRule",
    "AnalysisContext",
    "DEFAULT_RULES",
    "RulesEngine",
]
```

## Verification Results

```
# Task 1 - Insight structures
>>> from reddit_insight.insights import InsightType, Insight
Insight structures OK

# Task 2 - InsightRule
>>> from reddit_insight.insights.rules_engine import InsightRule, AnalysisContext
InsightRule OK

# Task 3 - RulesEngine
>>> e = RulesEngine(); e.load_default_rules()
Loaded 5 rules

# Task 4 - All exports
>>> from reddit_insight.insights import RulesEngine, InsightType, Insight
All insight exports OK

# Integration test - generate insights
Rules loaded: 5
Insights generated: 2
  - unmet_need: Monetizable unmet need: offline (90%, 85.0)
  - emerging_trend: Emerging trend: 'offline' (65%, 65.0)
Markdown output length: 736 chars
```

## Usage Example

```python
from reddit_insight.insights import RulesEngine, AnalysisContext

# Create engine and load rules
engine = RulesEngine()
engine.load_default_rules()

# Build context from analysis reports
context = engine.build_context(
    demand_report=demand_report,
    competitive_report=competitive_report,
    trend_report=trend_report
)

# Generate insights
insights = engine.generate_insights(context)

# Output as markdown
print(engine.to_markdown(insights))
```

## Architecture

```
reddit_insight/insights/
├── __init__.py          # Package exports
└── rules_engine.py      # Core engine and data structures
    ├── InsightType      # Enum for insight types
    ├── InsightEvidence  # Evidence data class
    ├── Insight          # Main insight data class
    ├── AnalysisContext  # Unified analysis context
    ├── InsightRule      # Rule definition
    ├── DEFAULT_RULES    # Built-in rules
    └── RulesEngine      # Main engine class
```

## Dependencies

- `reddit_insight.analysis.demand_analyzer`: PrioritizedDemand, DemandReport
- `reddit_insight.analysis.demand_patterns`: DemandCategory
- `reddit_insight.analysis.competitive`: Complaint, AlternativeComparison, CompetitiveReport
- `reddit_insight.analysis.rising`: RisingScore, TrendReport
- `reddit_insight.analysis.sentiment`: EntitySentiment

## Next Steps

- Plan 08-02: 비즈니스 기회 스코어링
- Plan 08-03: 실행 가능성 분석

## Commits

1. `feat(08-01): insight data structures` - InsightType, Insight, InsightEvidence, InsightRule, AnalysisContext, RulesEngine 구현

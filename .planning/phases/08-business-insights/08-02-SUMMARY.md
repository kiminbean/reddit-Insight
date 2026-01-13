---
phase: 08-business-insights
plan: 02
status: completed
completed_at: 2026-01-13
---

# Plan 08-02 Summary: Business Opportunity Scoring System

## Objective Achieved

비즈니스 기회 스코어링 시스템을 구현하여 인사이트를 비즈니스 가치 기준으로 점수화하고 우선순위를 결정할 수 있게 되었다.

## Completed Tasks

### Task 1: Scoring Data Structures
- `ScoreDimension` 열거형: 5가지 평가 차원 정의
  - MARKET_SIZE: 시장 규모 (수요 빈도 기반)
  - COMPETITION: 경쟁 강도 (낮을수록 좋음)
  - URGENCY: 긴급성 (불만 강도, 대안 탐색 빈도)
  - TREND: 트렌드 방향 (상승/하락)
  - FEASIBILITY: 실현 가능성 (기술적 복잡도)
- `DimensionScore`: 차원별 점수 (0-100), 가중치, 근거
- `BusinessScore`: 종합 점수, 등급 (A/B/C/D/F), 추천 문구
- `ScoringConfig`: 차원별 가중치 설정 (합계 1.0 자동 정규화)

### Task 2: Dimension Calculators
- `DimensionCalculator` 프로토콜: 확장 가능한 계산기 인터페이스
- `MarketSizeCalculator`: 수요 빈도, 관련 수요 수, 증거 품질
- `CompetitionCalculator`: 경쟁사 수, 감성 점수, 대안 탐색 빈도
- `UrgencyCalculator`: 불만 심각도, WTP 신호, 인사이트 우선순위
- `TrendCalculator`: Rising Score, 트렌드 증거, 키워드 매칭
- `FeasibilityCalculator`: 기존 솔루션, 신뢰도, 증거 품질

### Task 3: Opportunity Scorer
- `OpportunityScorer` 클래스:
  - `score_insight()`: 단일 인사이트 스코어링
  - `score_insights()`: 여러 인사이트 스코어링 및 정렬
  - `rank_opportunities()`: 순위 부여된 기회 목록 생성
  - `to_markdown()`: 마크다운 리포트 생성
  - `to_dict()`: JSON 직렬화 지원
- `ScoredOpportunity` 데이터 클래스: 인사이트 + 점수 + 순위

### Task 4: Module Exports
- `__init__.py` 업데이트로 모든 스코어링 컴포넌트 export
- 모듈 docstring에 스코어링 사용 예시 추가

## Files Modified

| File | Changes |
|------|---------|
| `src/reddit_insight/insights/scoring.py` | New file - scoring system implementation |
| `src/reddit_insight/insights/__init__.py` | Added scoring exports |

## Verification Results

```
ScoreDimension count: 5 (expected 5)
ScoringConfig total weight: 1.00 (should be ~1.0)
OpportunityScorer initialized with 5 calculators
All verifications passed
```

## Usage Example

```python
from reddit_insight.insights import (
    RulesEngine,
    OpportunityScorer,
    ScoringConfig,
)

# Generate insights
engine = RulesEngine()
engine.load_default_rules()
context = engine.build_context(demand_report, competitive_report)
insights = engine.generate_insights(context)

# Score and rank opportunities
config = ScoringConfig(
    market_size_weight=0.30,  # Emphasize market size
    competition_weight=0.25,
)
scorer = OpportunityScorer(config)
opportunities = scorer.rank_opportunities(insights, context)

# Output results
for opp in opportunities[:5]:
    print(f"#{opp.rank} [{opp.score.grade}] {opp.insight.title}")
    print(f"   Score: {opp.score.total_score:.1f}")
    print(f"   {opp.score.recommendation}")
```

## Grade Interpretation

| Grade | Score Range | Interpretation |
|-------|-------------|----------------|
| A | 80+ | Excellent opportunity - high priority |
| B | 60-79 | Strong opportunity - worth pursuing |
| C | 40-59 | Moderate - requires validation |
| D | 20-39 | Weak - significant challenges |
| F | 0-19 | Poor - not recommended |

## Next Steps

- 08-03: Report generation and export functionality
- Integration with web dashboard for visualization
- Fine-tuning weights based on user feedback

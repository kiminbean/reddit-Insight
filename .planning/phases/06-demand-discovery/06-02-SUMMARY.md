# Plan 06-02 Summary: Pattern Matching Engine

## Overview

**Plan**: 06-02 (Demand Detector)
**Phase**: 06-demand-discovery
**Status**: Complete
**Completed**: 2026-01-13

## What Was Built

### DemandDetector Engine

텍스트에서 수요 패턴을 자동으로 탐지하고 추출하는 엔진을 구현했다.

**Core Components:**

1. **DemandDetectorConfig**
   - `context_window`: 매칭 전후 추출할 문자 수 (기본값: 100)
   - `min_confidence`: 최소 신뢰도 임계값 (기본값: 0.5)
   - `case_sensitive`: 대소문자 구분 여부 (기본값: False)
   - `languages`: 탐지할 언어 목록 (기본값: ["en"])

2. **DemandDetector Class**
   - `detect(text)`: 텍스트에서 모든 수요 패턴 탐지
   - `detect_in_post(post)`: Post 객체의 title + selftext 분석
   - `detect_in_posts(posts)`: 여러 게시물 일괄 분석
   - `detect_by_category(text, category)`: 특정 카테고리만 탐지

3. **Context Extraction & Confidence Scoring**
   - `_extract_context()`: 문장 경계를 고려한 컨텍스트 추출
   - `_calculate_confidence()`: 패턴 가중치, 키워드, 길이, 위치 기반 신뢰도 계산
   - `_deduplicate_matches()`: 겹치는 매칭 중 최고 신뢰도만 유지

4. **DemandSummary Dataclass**
   - `total_matches`: 총 매칭 수
   - `by_category`: 카테고리별 매칭 수
   - `top_demands`: 신뢰도 기준 상위 수요 목록
   - `analyzed_texts`: 분석한 텍스트 수

## Files Modified

| File | Change |
|------|--------|
| `src/reddit_insight/analysis/demand_detector.py` | Created - DemandDetector engine |
| `src/reddit_insight/analysis/__init__.py` | Updated - Export new classes |

## Verification Results

```
=== Integration Test ===
Text: "I wish there was a better way..."
  -> feature_request: "I wish there was" (conf: 1.00)
Text: "Looking for a good project management tool..."
  -> search_query: "Looking for a" (conf: 0.98)
Text: "I would pay good money for a working solution..."
  -> willingness_to_pay: "I would pay good money" (conf: 1.00)
Text: "So frustrated with this app..."
  -> pain_point: "So frustrated with" (conf: 0.94)
Text: "Is there an alternative to Notion?..."
  -> alternative_seeking: "alternative to" (conf: 1.00)

Summary:
  Total matches: 6
  Analyzed texts: 6
  Categories: feature_request: 1, search_query: 2, willingness_to_pay: 1,
              pain_point: 1, alternative_seeking: 1
```

## Usage Example

```python
from reddit_insight.analysis import DemandDetector, DemandCategory

# Create detector
detector = DemandDetector()

# Detect demands in text
matches = detector.detect("I wish there was a better tool for this")
for match in matches:
    print(f"{match.category}: {match.matched_text} ({match.confidence:.2f})")

# Detect specific category
pain_points = detector.detect_by_category(text, DemandCategory.PAIN_POINT)

# Get summary
summary = detector.summarize(matches, analyzed_texts=100)
print(f"Total: {summary.total_matches}, Top: {summary.top_demands[0]}")
```

## Commits

1. `ed6c723` - feat(06-02): pattern matching engine (DemandDetector, DemandDetectorConfig)
2. `ddb6cd5` - feat(06-02): export and integrate demand detector module

## Success Criteria Met

- [x] DemandDetector가 텍스트에서 패턴 탐지
- [x] 컨텍스트 추출 및 신뢰도 계산 동작
- [x] 카테고리별 분석 가능
- [x] DemandSummary 요약 생성
- [x] Post 객체 직접 분석 가능

## Next Steps

- Plan 06-03: 수요 분류 및 우선순위화
  - 수요 클러스터링
  - 비즈니스 가치 점수 계산
  - 우선순위 기반 정렬

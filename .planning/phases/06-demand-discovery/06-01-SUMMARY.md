# Plan 06-01: 수요 표현 패턴 정의 - Summary

## Overview

**Plan ID**: 06-01
**Phase**: 06-demand-discovery
**Status**: Complete
**Completed**: 2026-01-13

## What Was Built

### 1. 수요 카테고리 (DemandCategory)

5가지 수요 표현 유형을 열거형으로 정의:

| Category | Value | Description |
|----------|-------|-------------|
| FEATURE_REQUEST | feature_request | 기능 요청 ("I wish there was...") |
| PAIN_POINT | pain_point | 불만/문제점 ("Frustrated with...") |
| SEARCH_QUERY | search_query | 검색/탐색 ("Looking for...") |
| WILLINGNESS_TO_PAY | willingness_to_pay | 구매 의향 ("I'd pay for...") |
| ALTERNATIVE_SEEKING | alternative_seeking | 대안 탐색 ("Is there anything like...") |

### 2. 데이터 구조

- **DemandPattern**: 패턴 정의 (정규식, 키워드, 가중치, 예시)
- **DemandMatch**: 매칭 결과 (패턴, 텍스트, 위치, 신뢰도)

### 3. 영어 패턴 라이브러리 (ENGLISH_PATTERNS)

20개 영어 수요 표현 패턴:

| Category | Count | Weight Range |
|----------|-------|--------------|
| FEATURE_REQUEST | 4 | 0.9 - 1.0 |
| PAIN_POINT | 4 | 0.8 - 0.9 |
| SEARCH_QUERY | 5 | 0.9 - 0.95 |
| WILLINGNESS_TO_PAY | 3 | 1.2 - 1.3 |
| ALTERNATIVE_SEEKING | 4 | 0.95 - 1.0 |

**가중치 전략**: 구매 의향 > 기능 요청 > 대안 탐색 > 검색 > 불만

### 4. 한국어 패턴 라이브러리 (KOREAN_PATTERNS)

5개 한국어 수요 표현 패턴 (미래 확장용):
- 기능 요청: 2개
- 검색/탐색: 2개
- 불만/문제점: 1개

### 5. DemandPatternLibrary 클래스

패턴 관리 및 검색을 위한 라이브러리 클래스:

**메서드**:
- `add_pattern()`: 패턴 추가
- `get_patterns()`: 카테고리별 필터링
- `get_pattern_by_id()`: ID로 조회
- `get_compiled_pattern()`: 컴파일된 정규식 반환

**팩토리 메서드**:
- `create_english_library()`: 영어 라이브러리
- `create_korean_library()`: 한국어 라이브러리
- `create_multilingual_library()`: 다국어 라이브러리

## Files Modified

| File | Action | Lines |
|------|--------|-------|
| `src/reddit_insight/analysis/demand_patterns.py` | Created | 680 |
| `src/reddit_insight/analysis/__init__.py` | Modified | +15 |

## Commits

| Hash | Message |
|------|---------|
| 756b86e | feat(06-01): 수요 패턴 데이터 구조 |
| b9aec19 | feat(06-01): 영어 수요 표현 패턴 라이브러리 |
| cd3a20d | feat(06-01): DemandPatternLibrary 클래스 |
| 0c03327 | feat(06-01): 수요 패턴 모듈 export |

## Verification Results

```
✓ DemandCategory 5가지 정의됨
✓ DemandPattern, DemandMatch 데이터 구조 있음
✓ 영어 패턴 20개 정의됨 (15개+ 요구사항 충족)
✓ DemandPatternLibrary 팩토리 메서드 동작
✓ 20/20 패턴이 예시 문장과 정상 매칭됨
```

## Usage Example

```python
from reddit_insight.analysis import DemandPatternLibrary, DemandCategory

# Create library
library = DemandPatternLibrary.create_english_library()

# Get patterns by category
feature_patterns = library.get_patterns(DemandCategory.FEATURE_REQUEST)
print(f"Feature request patterns: {len(feature_patterns)}")

# Get compiled regex for matching
pattern = library.get_pattern_by_id("en_feature_wish")
compiled = library.get_compiled_pattern("en_feature_wish")

# Test matching
text = "I wish there was a better tool for this"
if compiled.search(text):
    print("Demand pattern detected!")
```

## Next Steps

- **06-02**: 패턴 매칭 엔진 구현 (DemandMatcher)
- **06-03**: 수요 분류 및 우선순위화

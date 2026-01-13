"""경쟁 분석 라우터.

경쟁사 분석, 감성 분석, 불만 추출 결과를 시각화하는 라우터.
"""

from dataclasses import dataclass
from hashlib import md5
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from reddit_insight.analysis.competitive import (
    CompetitiveAnalyzer,
    CompetitiveInsight,
    CompetitiveReport,
    Complaint,
)
from reddit_insight.analysis.sentiment import Sentiment

router = APIRouter(prefix="/dashboard/competition", tags=["competition"])


# =============================================================================
# VIEW MODELS
# =============================================================================


@dataclass
class EntityView:
    """엔티티 뷰 모델.

    Attributes:
        name: 엔티티 이름
        entity_type: 엔티티 유형 (product, service 등)
        mention_count: 언급 횟수
        sentiment_score: 감성 점수 (-1 ~ 1)
        sentiment_label: 감성 레이블 (positive/neutral/negative)
        complaint_count: 불만 수
    """

    name: str
    entity_type: str
    mention_count: int
    sentiment_score: float
    sentiment_label: str
    complaint_count: int = 0


@dataclass
class EntityDetail:
    """엔티티 상세 뷰 모델.

    Attributes:
        entity: 기본 엔티티 정보
        top_complaints: 주요 불만 목록
        switch_to: 이 제품에서 이동하는 대상 제품 목록
        switch_from: 이 제품으로 이동해 오는 소스 제품 목록
        alternatives_mentioned: 언급된 대안 제품 목록
    """

    entity: EntityView
    top_complaints: list["ComplaintView"]
    switch_to: list[str]
    switch_from: list[str]
    alternatives_mentioned: list[str]


@dataclass
class ComplaintView:
    """불만 뷰 모델.

    Attributes:
        id: 고유 식별자
        entity_name: 대상 엔티티 이름
        complaint_type: 불만 유형
        text: 불만 텍스트
        severity: 심각도 (0-1)
        keywords: 관련 키워드
    """

    id: str
    entity_name: str
    complaint_type: str
    text: str
    severity: float
    keywords: list[str]


# =============================================================================
# COMPETITION SERVICE
# =============================================================================


class CompetitionService:
    """경쟁 분석 서비스.

    CompetitiveAnalyzer를 래핑하여 대시보드에 필요한 데이터 형태로 변환한다.
    """

    def __init__(self, analyzer: CompetitiveAnalyzer | None = None) -> None:
        """CompetitionService를 초기화한다.

        Args:
            analyzer: 경쟁 분석기 (None이면 기본 인스턴스 생성)
        """
        self._analyzer = analyzer or CompetitiveAnalyzer()
        self._cached_report: CompetitiveReport | None = None

    def _generate_complaint_id(self, complaint: Complaint, index: int) -> str:
        """불만에서 고유 ID를 생성한다."""
        content = f"{complaint.entity.name}_{complaint.text[:20]}_{index}"
        return md5(content.encode()).hexdigest()[:12]

    def _sentiment_to_label(self, sentiment: Sentiment) -> str:
        """Sentiment enum을 레이블 문자열로 변환한다."""
        return sentiment.value

    def _insight_to_entity_view(self, insight: CompetitiveInsight) -> EntityView:
        """CompetitiveInsight를 EntityView로 변환한다."""
        return EntityView(
            name=insight.entity.name,
            entity_type=insight.entity.entity_type.value,
            mention_count=insight.entity.mention_count if hasattr(insight.entity, 'mention_count') else 1,
            sentiment_score=insight.overall_sentiment.compound,
            sentiment_label=self._sentiment_to_label(insight.overall_sentiment.sentiment),
            complaint_count=insight.complaint_count,
        )

    def _complaint_to_view(self, complaint: Complaint, index: int) -> ComplaintView:
        """Complaint을 ComplaintView로 변환한다."""
        return ComplaintView(
            id=self._generate_complaint_id(complaint, index),
            entity_name=complaint.entity.name,
            complaint_type=complaint.complaint_type.value,
            text=complaint.text,
            severity=complaint.severity,
            keywords=complaint.keywords,
        )

    def _insight_to_entity_detail(
        self, insight: CompetitiveInsight
    ) -> EntityDetail:
        """CompetitiveInsight를 EntityDetail로 변환한다."""
        entity_view = self._insight_to_entity_view(insight)

        complaint_views = [
            self._complaint_to_view(c, i)
            for i, c in enumerate(insight.top_complaints)
        ]

        return EntityDetail(
            entity=entity_view,
            top_complaints=complaint_views,
            switch_to=insight.switch_to,
            switch_from=insight.switch_from,
            alternatives_mentioned=insight.alternatives_mentioned,
        )

    def _run_demo_analysis(self) -> None:
        """데모 데이터로 분석을 실행한다."""
        # 데모용 가상 Post 객체 생성을 위한 클래스
        from dataclasses import dataclass as dc
        from datetime import datetime

        @dc
        class DemoPost:
            id: str
            title: str
            selftext: str = ""
            score: int = 1
            num_comments: int = 0
            created_utc: datetime = None
            subreddit: str = "demo"
            author: str = "demo_user"
            url: str = ""
            permalink: str = ""

            def __post_init__(self):
                if self.created_utc is None:
                    self.created_utc = datetime.now()

        demo_posts = [
            DemoPost(
                id="1",
                title="Slack is so slow and keeps crashing",
                selftext="Really frustrated with Slack lately. It's been slow and crashes constantly. Anyone have alternatives?",
            ),
            DemoPost(
                id="2",
                title="Switched from Evernote to Notion",
                selftext="Finally made the switch. Notion is so much better for organizing notes. Evernote was getting too expensive.",
            ),
            DemoPost(
                id="3",
                title="Trello vs Asana for small teams",
                selftext="Which one is better for a team of 5? Looking for something simple but effective.",
            ),
            DemoPost(
                id="4",
                title="Frustrated with Dropbox pricing",
                selftext="Dropbox is too expensive for what it offers. Google Drive is a better alternative.",
            ),
            DemoPost(
                id="5",
                title="Zoom alternative needed",
                selftext="Zoom has terrible audio quality. Microsoft Teams is better but has its own issues.",
            ),
            DemoPost(
                id="6",
                title="Discord vs Slack for communities",
                selftext="Discord is great for gaming communities but Slack is better for work.",
            ),
            DemoPost(
                id="7",
                title="Notion is confusing",
                selftext="Notion has a steep learning curve. It's confusing for beginners.",
            ),
            DemoPost(
                id="8",
                title="Recommend Obsidian over Notion",
                selftext="I recommend Obsidian over Notion for personal knowledge management.",
            ),
        ]

        self._cached_report = self._analyzer.analyze_posts(demo_posts)

    def get_entities(self, limit: int = 20) -> list[EntityView]:
        """엔티티 목록을 반환한다.

        Args:
            limit: 최대 반환 수

        Returns:
            EntityView 목록
        """
        if self._cached_report is None:
            self._run_demo_analysis()

        if self._cached_report is None:
            return []

        result: list[EntityView] = []

        for insight in self._cached_report.insights[:limit]:
            result.append(self._insight_to_entity_view(insight))

        return result

    def get_entity_detail(self, name: str) -> EntityDetail | None:
        """엔티티 상세 정보를 반환한다.

        Args:
            name: 엔티티 이름

        Returns:
            EntityDetail 또는 None (찾지 못한 경우)
        """
        if self._cached_report is None:
            self._run_demo_analysis()

        if self._cached_report is None:
            return None

        name_lower = name.lower()
        for insight in self._cached_report.insights:
            if insight.entity.name.lower() == name_lower:
                return self._insight_to_entity_detail(insight)
            if insight.entity.normalized_name == name_lower:
                return self._insight_to_entity_detail(insight)

        return None

    def get_top_complaints(self, limit: int = 10) -> list[ComplaintView]:
        """상위 불만 목록을 반환한다.

        Args:
            limit: 최대 반환 수

        Returns:
            ComplaintView 목록
        """
        if self._cached_report is None:
            self._run_demo_analysis()

        if self._cached_report is None:
            return []

        return [
            self._complaint_to_view(c, i)
            for i, c in enumerate(self._cached_report.top_complaints[:limit])
        ]

    def get_sentiment_distribution(self) -> dict[str, float]:
        """감성 분포를 반환한다.

        Returns:
            감성별 비율 딕셔너리 (positive, neutral, negative)
        """
        if self._cached_report is None:
            self._run_demo_analysis()

        if self._cached_report is None:
            return {"positive": 0.0, "neutral": 0.0, "negative": 0.0}

        total = len(self._cached_report.insights)
        if total == 0:
            return {"positive": 0.0, "neutral": 0.0, "negative": 0.0}

        counts = {"positive": 0, "neutral": 0, "negative": 0}
        for insight in self._cached_report.insights:
            label = self._sentiment_to_label(insight.overall_sentiment.sentiment)
            if label in counts:
                counts[label] += 1

        return {k: (v / total) * 100 for k, v in counts.items()}

    def get_popular_switches(self) -> list[dict[str, Any]]:
        """인기 제품 전환 목록을 반환한다.

        Returns:
            전환 정보 목록 (from, to, count)
        """
        if self._cached_report is None:
            self._run_demo_analysis()

        if self._cached_report is None:
            return []

        return [
            {"from": from_name, "to": to_name, "count": count}
            for from_name, to_name, count in self._cached_report.popular_switches
        ]

    def get_recommendations(self) -> list[str]:
        """분석 권장사항을 반환한다.

        Returns:
            권장사항 목록
        """
        if self._cached_report is None:
            return []

        return self._cached_report.recommendations


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_competition_service: CompetitionService | None = None


def get_competition_service() -> CompetitionService:
    """CompetitionService 싱글톤 인스턴스를 반환한다."""
    global _competition_service
    if _competition_service is None:
        _competition_service = CompetitionService()
    return _competition_service


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_templates(request: Request) -> Jinja2Templates:
    """Request에서 템플릿 인스턴스를 가져온다."""
    return request.app.state.templates


def entity_view_to_dict(view: EntityView) -> dict[str, Any]:
    """EntityView를 딕셔너리로 변환한다."""
    return {
        "name": view.name,
        "entity_type": view.entity_type,
        "mention_count": view.mention_count,
        "sentiment_score": view.sentiment_score,
        "sentiment_label": view.sentiment_label,
        "complaint_count": view.complaint_count,
    }


def complaint_view_to_dict(view: ComplaintView) -> dict[str, Any]:
    """ComplaintView를 딕셔너리로 변환한다."""
    return {
        "id": view.id,
        "entity_name": view.entity_name,
        "complaint_type": view.complaint_type,
        "text": view.text,
        "severity": view.severity,
        "keywords": view.keywords,
    }


def entity_detail_to_dict(detail: EntityDetail) -> dict[str, Any]:
    """EntityDetail을 딕셔너리로 변환한다."""
    return {
        "entity": entity_view_to_dict(detail.entity),
        "top_complaints": [complaint_view_to_dict(c) for c in detail.top_complaints],
        "switch_to": detail.switch_to,
        "switch_from": detail.switch_from,
        "alternatives_mentioned": detail.alternatives_mentioned,
    }


# =============================================================================
# ROUTES
# =============================================================================


@router.get("/", response_class=HTMLResponse)
async def competition_index(
    request: Request,
    service: CompetitionService = Depends(get_competition_service),
) -> HTMLResponse:
    """경쟁 분석 메인 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        service: CompetitionService 인스턴스

    Returns:
        HTMLResponse: 렌더링된 HTML 페이지
    """
    templates = get_templates(request)

    entities = service.get_entities(limit=20)
    complaints = service.get_top_complaints(limit=10)
    sentiment_dist = service.get_sentiment_distribution()
    popular_switches = service.get_popular_switches()
    recommendations = service.get_recommendations()

    context = {
        "request": request,
        "page_title": "Competition",
        "entities": [entity_view_to_dict(e) for e in entities],
        "complaints": [complaint_view_to_dict(c) for c in complaints],
        "sentiment_distribution": sentiment_dist,
        "popular_switches": popular_switches,
        "recommendations": recommendations,
        "total_entities": len(entities),
    }

    return templates.TemplateResponse(request, "competition/index.html", context)


@router.get("/entities", response_class=HTMLResponse)
async def entities_list(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="최대 반환 수"),
    service: CompetitionService = Depends(get_competition_service),
) -> HTMLResponse:
    """엔티티 목록을 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        limit: 최대 반환 수
        service: CompetitionService 인스턴스

    Returns:
        HTMLResponse: 엔티티 목록 HTML partial
    """
    templates = get_templates(request)

    entities = service.get_entities(limit=limit)

    context = {
        "request": request,
        "entities": [entity_view_to_dict(e) for e in entities],
    }

    return templates.TemplateResponse(request, "competition/partials/entity_list.html", context)


@router.get("/entity/{name}", response_class=HTMLResponse)
async def entity_detail(
    request: Request,
    name: str,
    service: CompetitionService = Depends(get_competition_service),
) -> HTMLResponse:
    """엔티티 상세 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        name: 엔티티 이름
        service: CompetitionService 인스턴스

    Returns:
        HTMLResponse: 엔티티 상세 HTML 페이지
    """
    templates = get_templates(request)

    detail = service.get_entity_detail(name)

    if detail is None:
        context = {
            "request": request,
            "page_title": "Entity Not Found",
            "error": f"Entity '{name}' not found.",
        }
        return templates.TemplateResponse(request, "competition/entity_detail.html", context, status_code=404)

    context = {
        "request": request,
        "page_title": f"Entity: {detail.entity.name}",
        "detail": entity_detail_to_dict(detail),
    }

    return templates.TemplateResponse(request, "competition/entity_detail.html", context)


@router.get("/sentiment-chart", response_class=JSONResponse)
async def sentiment_chart(
    service: CompetitionService = Depends(get_competition_service),
) -> JSONResponse:
    """감성 분포 차트 데이터를 JSON으로 반환한다.

    Args:
        service: CompetitionService 인스턴스

    Returns:
        JSONResponse: Chart.js용 데이터
    """
    dist = service.get_sentiment_distribution()

    # Chart.js 포맷으로 변환
    data = {
        "labels": ["Positive", "Neutral", "Negative"],
        "datasets": [{
            "data": [dist.get("positive", 0), dist.get("neutral", 0), dist.get("negative", 0)],
            "backgroundColor": ["#22c55e", "#6b7280", "#ef4444"],
            "borderColor": ["#16a34a", "#4b5563", "#dc2626"],
            "borderWidth": 1,
        }],
    }

    return JSONResponse(content=data)


@router.get("/complaints", response_class=HTMLResponse)
async def complaints_list(
    request: Request,
    limit: int = Query(10, ge=1, le=50, description="최대 반환 수"),
    service: CompetitionService = Depends(get_competition_service),
) -> HTMLResponse:
    """불만 목록을 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        limit: 최대 반환 수
        service: CompetitionService 인스턴스

    Returns:
        HTMLResponse: 불만 목록 HTML partial
    """
    templates = get_templates(request)

    complaints = service.get_top_complaints(limit=limit)

    context = {
        "request": request,
        "complaints": [complaint_view_to_dict(c) for c in complaints],
    }

    return templates.TemplateResponse(request, "competition/partials/complaint_list.html", context)


@router.get("/switches", response_class=JSONResponse)
async def switches_data(
    service: CompetitionService = Depends(get_competition_service),
) -> JSONResponse:
    """인기 제품 전환 데이터를 JSON으로 반환한다.

    Args:
        service: CompetitionService 인스턴스

    Returns:
        JSONResponse: 전환 데이터
    """
    switches = service.get_popular_switches()
    return JSONResponse(content=switches)

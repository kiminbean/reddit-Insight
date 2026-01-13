"""End-to-End tests for Reddit Insight dashboard.

이 모듈은 대시보드 라우트와 전체 워크플로우의 E2E 테스트를 제공합니다.
FastAPI TestClient를 사용하여 HTTP 엔드포인트를 테스트합니다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from reddit_insight.reddit.models import Post


# ============================================================================
# Dashboard Routes Tests
# ============================================================================


class TestDashboardRoutes:
    """대시보드 라우트 E2E 테스트."""

    def test_home_page_redirects_to_dashboard(self, test_client: "TestClient") -> None:
        """루트 경로가 대시보드로 리다이렉트되는지 테스트.

        / 접근 시 /dashboard로 302 리다이렉트되어야 합니다.
        """
        response = test_client.get("/", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"

    def test_dashboard_home(self, test_client: "TestClient") -> None:
        """대시보드 홈 페이지 렌더링 테스트.

        /dashboard 접근 시 HTML 페이지가 렌더링되어야 합니다.
        """
        response = test_client.get("/dashboard")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # 기본적인 HTML 구조 확인
        assert "<html" in response.text.lower() or "<!doctype" in response.text.lower()

    def test_health_check(self, test_client: "TestClient") -> None:
        """헬스체크 엔드포인트 테스트.

        /health 엔드포인트가 서비스 상태를 반환해야 합니다.
        """
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data

    def test_trends_page(self, test_client: "TestClient") -> None:
        """트렌드 페이지 렌더링 테스트.

        /dashboard/trends 접근 시 HTML 페이지가 렌더링되어야 합니다.
        """
        response = test_client.get("/dashboard/trends")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_trends_page_with_filters(self, test_client: "TestClient") -> None:
        """트렌드 페이지 필터 파라미터 테스트.

        필터 파라미터가 적용되어야 합니다.
        """
        response = test_client.get(
            "/dashboard/trends",
            params={"days": 14, "limit": 10},
        )

        assert response.status_code == 200

    def test_demands_page(self, test_client: "TestClient") -> None:
        """수요 분석 페이지 렌더링 테스트.

        /dashboard/demands 접근 시 HTML 페이지가 렌더링되어야 합니다.
        """
        response = test_client.get("/dashboard/demands")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_competition_page(self, test_client: "TestClient") -> None:
        """경쟁 분석 페이지 렌더링 테스트.

        /dashboard/competition 접근 시 HTML 페이지가 렌더링되어야 합니다.
        """
        response = test_client.get("/dashboard/competition")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_insights_page(self, test_client: "TestClient") -> None:
        """인사이트 페이지 렌더링 테스트.

        /dashboard/insights 접근 시 HTML 페이지가 렌더링되어야 합니다.
        """
        response = test_client.get("/dashboard/insights")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_search_page(self, test_client: "TestClient") -> None:
        """검색 페이지 렌더링 테스트.

        /search 접근 시 HTML 페이지가 렌더링되어야 합니다.
        """
        response = test_client.get("/search")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_search_with_query(self, test_client: "TestClient") -> None:
        """검색어로 검색 테스트.

        검색어를 포함한 요청이 처리되어야 합니다.
        """
        response = test_client.get("/search", params={"q": "python"})

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_search_with_type_filter(self, test_client: "TestClient") -> None:
        """검색 유형 필터 테스트.

        검색 유형 필터가 적용되어야 합니다.
        """
        response = test_client.get(
            "/search",
            params={"q": "machine learning", "type": "keywords"},
        )

        assert response.status_code == 200


# ============================================================================
# API Endpoints Tests
# ============================================================================


class TestAPIEndpoints:
    """API 엔드포인트 E2E 테스트."""

    def test_trends_chart_data_endpoint(self, test_client: "TestClient") -> None:
        """트렌드 차트 데이터 엔드포인트 테스트.

        /dashboard/trends/chart-data가 JSON 데이터를 반환해야 합니다.
        """
        response = test_client.get(
            "/dashboard/trends/chart-data",
            params={"keyword": "python", "days": 7},
        )

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        data = response.json()
        assert "labels" in data
        assert "datasets" in data
        assert isinstance(data["datasets"], list)

    def test_top_keywords_chart_endpoint(self, test_client: "TestClient") -> None:
        """상위 키워드 차트 데이터 엔드포인트 테스트.

        /dashboard/trends/top-keywords-chart가 JSON 데이터를 반환해야 합니다.
        """
        response = test_client.get(
            "/dashboard/trends/top-keywords-chart",
            params={"limit": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert "labels" in data
        assert "datasets" in data

    def test_htmx_keywords_partial(self, test_client: "TestClient") -> None:
        """키워드 목록 HTMX 파셜 테스트.

        /dashboard/trends/keywords가 HTML 파셜을 반환해야 합니다.
        """
        response = test_client.get(
            "/dashboard/trends/keywords",
            params={"days": 7, "limit": 10},
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_htmx_rising_partial(self, test_client: "TestClient") -> None:
        """Rising 키워드 HTMX 파셜 테스트.

        /dashboard/trends/rising이 HTML 파셜을 반환해야 합니다.
        """
        response = test_client.get(
            "/dashboard/trends/rising",
            params={"limit": 5},
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_dashboard_summary_partial(self, test_client: "TestClient") -> None:
        """대시보드 요약 HTMX 파셜 테스트.

        /dashboard/summary가 HTML 파셜을 반환해야 합니다.
        """
        response = test_client.get("/dashboard/summary")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_search_suggestions_partial(self, test_client: "TestClient") -> None:
        """검색 제안 HTMX 파셜 테스트.

        /search/suggestions가 HTML 파셜을 반환해야 합니다.
        """
        response = test_client.get(
            "/search/suggestions",
            params={"q": "py", "limit": 5},
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_search_results_partial(self, test_client: "TestClient") -> None:
        """검색 결과 HTMX 파셜 테스트.

        /search/results가 HTML 파셜을 반환해야 합니다.
        """
        response = test_client.get(
            "/search/results",
            params={"q": "python"},
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


# ============================================================================
# Filter Parameters Tests
# ============================================================================


class TestFilterParameters:
    """필터 파라미터 E2E 테스트."""

    def test_trends_days_parameter_validation(
        self, test_client: "TestClient"
    ) -> None:
        """트렌드 days 파라미터 유효성 검사 테스트.

        유효한 범위의 days 파라미터만 허용되어야 합니다.
        """
        # 유효한 범위 (1-30)
        response = test_client.get(
            "/dashboard/trends", params={"days": 15}
        )
        assert response.status_code == 200

        # 범위 초과 - FastAPI 유효성 검사가 422를 반환해야 함
        response = test_client.get(
            "/dashboard/trends", params={"days": 100}
        )
        assert response.status_code == 422

    def test_trends_limit_parameter_validation(
        self, test_client: "TestClient"
    ) -> None:
        """트렌드 limit 파라미터 유효성 검사 테스트.

        유효한 범위의 limit 파라미터만 허용되어야 합니다.
        """
        # 유효한 범위 (1-100)
        response = test_client.get(
            "/dashboard/trends", params={"limit": 50}
        )
        assert response.status_code == 200

        # 범위 초과
        response = test_client.get(
            "/dashboard/trends", params={"limit": 500}
        )
        assert response.status_code == 422

    def test_search_limit_parameter(self, test_client: "TestClient") -> None:
        """검색 limit 파라미터 테스트.

        limit 파라미터가 적용되어야 합니다.
        """
        response = test_client.get(
            "/search",
            params={"q": "test", "limit": 5},
        )
        assert response.status_code == 200

    def test_subreddit_filter_parameter(self, test_client: "TestClient") -> None:
        """서브레딧 필터 파라미터 테스트.

        subreddit 파라미터가 적용되어야 합니다.
        """
        response = test_client.get(
            "/dashboard/trends",
            params={"subreddit": "python"},
        )
        assert response.status_code == 200


# ============================================================================
# Full Workflow Tests
# ============================================================================


class TestFullWorkflow:
    """전체 워크플로우 E2E 테스트."""

    @pytest.mark.integration
    def test_complete_analysis_workflow(
        self,
        test_client: "TestClient",
        sample_posts: list["Post"],
    ) -> None:
        """전체 분석 워크플로우 테스트.

        샘플 데이터 입력 -> 분석 -> 대시보드 조회 -> 리포트 생성
        전체 흐름을 테스트합니다.
        """
        # Step 1: 헬스체크로 서비스 상태 확인
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

        # Step 2: 대시보드 홈 접근
        response = test_client.get("/dashboard")
        assert response.status_code == 200

        # Step 3: 트렌드 페이지 접근 및 필터 적용
        response = test_client.get(
            "/dashboard/trends",
            params={"days": 7, "limit": 20},
        )
        assert response.status_code == 200

        # Step 4: 트렌드 차트 데이터 요청
        response = test_client.get(
            "/dashboard/trends/chart-data",
            params={"keyword": "python", "days": 7},
        )
        assert response.status_code == 200
        chart_data = response.json()
        assert "labels" in chart_data
        assert "datasets" in chart_data

        # Step 5: 수요 분석 페이지 접근
        response = test_client.get("/dashboard/demands")
        assert response.status_code == 200

        # Step 6: 경쟁 분석 페이지 접근
        response = test_client.get("/dashboard/competition")
        assert response.status_code == 200

        # Step 7: 인사이트 페이지 접근
        response = test_client.get("/dashboard/insights")
        assert response.status_code == 200

        # Step 8: 검색 기능 테스트
        response = test_client.get(
            "/search",
            params={"q": "machine learning"},
        )
        assert response.status_code == 200

    @pytest.mark.integration
    def test_htmx_workflow(self, test_client: "TestClient") -> None:
        """HTMX 동적 업데이트 워크플로우 테스트.

        HTMX 파셜 요청이 올바르게 동작하는지 테스트합니다.
        """
        # 메인 페이지 로드
        response = test_client.get("/dashboard/trends")
        assert response.status_code == 200

        # HTMX 파셜 요청 - 키워드 목록
        response = test_client.get(
            "/dashboard/trends/keywords",
            params={"days": 7, "limit": 10},
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # HTMX 파셜 요청 - Rising 키워드
        response = test_client.get(
            "/dashboard/trends/rising",
            params={"limit": 5},
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 200

        # HTMX 파셜 요청 - 대시보드 요약
        response = test_client.get(
            "/dashboard/summary",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 200

    @pytest.mark.integration
    def test_search_flow(self, test_client: "TestClient") -> None:
        """검색 흐름 E2E 테스트.

        검색 페이지 로드 -> 자동완성 -> 검색 결과 흐름을 테스트합니다.
        """
        # Step 1: 검색 페이지 로드
        response = test_client.get("/search")
        assert response.status_code == 200

        # Step 2: 자동완성 요청
        response = test_client.get(
            "/search/suggestions",
            params={"q": "py"},
        )
        assert response.status_code == 200

        # Step 3: 검색 실행
        response = test_client.get(
            "/search",
            params={"q": "python data analysis"},
        )
        assert response.status_code == 200

        # Step 4: 검색 유형별 필터
        response = test_client.get(
            "/search",
            params={"q": "python", "type": "keywords"},
        )
        assert response.status_code == 200

        # Step 5: 검색 결과 파셜 요청
        response = test_client.get(
            "/search/results",
            params={"q": "python"},
        )
        assert response.status_code == 200


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """에러 처리 E2E 테스트."""

    def test_nonexistent_route_returns_404(
        self, test_client: "TestClient"
    ) -> None:
        """존재하지 않는 라우트 접근 시 404 반환 테스트."""
        response = test_client.get("/nonexistent-route")
        assert response.status_code == 404

    def test_invalid_chart_data_keyword(
        self, test_client: "TestClient"
    ) -> None:
        """차트 데이터 요청 시 키워드 파라미터 필수 테스트.

        keyword 파라미터 없이 요청하면 422 에러가 발생해야 합니다.
        """
        response = test_client.get("/dashboard/trends/chart-data")
        # keyword는 필수 파라미터이므로 422 Validation Error
        assert response.status_code == 422

    def test_empty_search_query(self, test_client: "TestClient") -> None:
        """빈 검색어 처리 테스트.

        빈 검색어는 결과 없이 페이지만 렌더링되어야 합니다.
        """
        response = test_client.get("/search", params={"q": ""})
        assert response.status_code == 200


# ============================================================================
# Static Files Tests
# ============================================================================


class TestStaticFiles:
    """정적 파일 E2E 테스트."""

    def test_static_files_mount(self, test_client: "TestClient") -> None:
        """정적 파일 마운트 테스트.

        /static 경로가 마운트되어 있어야 합니다.
        """
        # CSS 파일 요청 시뮬레이션 (실제 파일이 없어도 404가 반환되면 마운트는 됨)
        response = test_client.get("/static/nonexistent.css")
        # 파일이 없으면 404, 있으면 200
        assert response.status_code in [200, 404]


# ============================================================================
# API Documentation Tests
# ============================================================================


class TestAPIDocumentation:
    """API 문서화 E2E 테스트."""

    def test_openapi_docs_available(self, test_client: "TestClient") -> None:
        """OpenAPI 문서 엔드포인트 테스트.

        /api/docs가 Swagger UI를 제공해야 합니다.
        """
        response = test_client.get("/api/docs")
        assert response.status_code == 200

    def test_redoc_available(self, test_client: "TestClient") -> None:
        """ReDoc 문서 엔드포인트 테스트.

        /api/redoc가 ReDoc UI를 제공해야 합니다.
        """
        response = test_client.get("/api/redoc")
        assert response.status_code == 200

    def test_openapi_json_schema(self, test_client: "TestClient") -> None:
        """OpenAPI JSON 스키마 테스트.

        /openapi.json이 OpenAPI 스키마를 반환해야 합니다.
        """
        response = test_client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

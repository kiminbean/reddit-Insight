"""비즈니스 분석 보고서 생성 서비스.

인사이트 데이터를 기반으로 비즈니스 분석 보고서를 자동 생성한다.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from reddit_insight.dashboard.data_store import get_current_data


@dataclass
class BusinessItem:
    """비즈니스 아이템 도출 결과."""

    rank: int
    title: str
    category: str
    opportunity_score: float
    market_potential: str
    risk_level: str
    description: str
    target_audience: str
    key_features: list[str]
    competitive_advantage: str
    next_steps: list[str]
    evidence: list[str]


@dataclass
class ReportData:
    """보고서 데이터."""

    subreddit: str
    generated_at: datetime
    analysis_period: str
    total_posts_analyzed: int
    total_keywords: int
    total_insights: int
    executive_summary: str
    market_overview: dict[str, Any]
    business_items: list[BusinessItem]
    trend_analysis: dict[str, Any]
    demand_analysis: dict[str, Any]
    competition_analysis: dict[str, Any]
    recommendations: list[str]
    risk_factors: list[str]
    conclusion: str


class ReportService:
    """비즈니스 분석 보고서 생성 서비스."""

    def __init__(self) -> None:
        """서비스 초기화."""
        pass

    def generate_report(self, subreddit: str | None = None) -> ReportData | None:
        """비즈니스 분석 보고서를 생성한다.

        Args:
            subreddit: 서브레딧 이름 (None이면 현재 데이터 사용)

        Returns:
            ReportData 또는 None (데이터 없음)
        """
        data = get_current_data(subreddit)
        if not data:
            return None

        # 비즈니스 아이템 도출
        business_items = self._extract_business_items(data)

        # 트렌드 분석
        trend_analysis = self._analyze_trends(data)

        # 수요 분석
        demand_analysis = self._analyze_demands(data)

        # 경쟁 분석
        competition_analysis = self._analyze_competition(data)

        # Executive Summary 생성
        executive_summary = self._generate_executive_summary(
            data, business_items, trend_analysis
        )

        # 시장 개요
        market_overview = self._generate_market_overview(data, trend_analysis)

        # 추천 사항
        recommendations = self._generate_recommendations(
            business_items, demand_analysis, competition_analysis
        )

        # 리스크 요인
        risk_factors = self._identify_risk_factors(
            data, competition_analysis
        )

        # 결론
        conclusion = self._generate_conclusion(
            business_items, recommendations
        )

        return ReportData(
            subreddit=data.subreddit,
            generated_at=datetime.now(UTC),
            analysis_period="Last 7 days",
            total_posts_analyzed=data.post_count,
            total_keywords=len(data.keywords) if data.keywords else 0,
            total_insights=len(data.insights) if data.insights else 0,
            executive_summary=executive_summary,
            market_overview=market_overview,
            business_items=business_items,
            trend_analysis=trend_analysis,
            demand_analysis=demand_analysis,
            competition_analysis=competition_analysis,
            recommendations=recommendations,
            risk_factors=risk_factors,
            conclusion=conclusion,
        )

    def _extract_business_items(self, data: Any) -> list[BusinessItem]:
        """인사이트에서 비즈니스 아이템을 도출한다."""
        items = []
        rank = 1

        # 인사이트 기반 비즈니스 아이템 도출
        if data.insights:
            for insight in data.insights[:5]:  # 상위 5개
                title = insight.get("title", "")
                insight_type = insight.get("type", "emerging_trend")
                confidence = insight.get("confidence", 0.7)
                evidence = insight.get("evidence", [])
                description = insight.get("description", "")

                # 카테고리 매핑
                category_map = {
                    "market_gap": "신규 시장 진입",
                    "improvement_opportunity": "기존 제품 개선",
                    "emerging_trend": "트렌드 기반 서비스",
                    "competitive_weakness": "경쟁사 대응",
                    "unmet_need": "미충족 수요 해결",
                }
                category = category_map.get(insight_type, "기타")

                # 기회 점수 계산
                opportunity_score = confidence * 100

                # 시장 잠재력 평가
                if opportunity_score >= 80:
                    market_potential = "높음"
                elif opportunity_score >= 60:
                    market_potential = "중간"
                else:
                    market_potential = "낮음"

                # 리스크 수준
                if opportunity_score >= 75:
                    risk_level = "낮음"
                elif opportunity_score >= 50:
                    risk_level = "중간"
                else:
                    risk_level = "높음"

                # 타겟 고객 추론
                target_audience = self._infer_target_audience(title, description)

                # 핵심 기능 추론
                key_features = self._infer_key_features(title, description, insight_type)

                # 경쟁 우위 추론
                competitive_advantage = self._infer_competitive_advantage(
                    title, insight_type, data
                )

                # 다음 단계 추론
                next_steps = self._generate_next_steps(insight_type, opportunity_score)

                items.append(BusinessItem(
                    rank=rank,
                    title=title[:100] if title else f"Business Opportunity #{rank}",
                    category=category,
                    opportunity_score=opportunity_score,
                    market_potential=market_potential,
                    risk_level=risk_level,
                    description=description or f"Based on {insight_type.replace('_', ' ')} analysis",
                    target_audience=target_audience,
                    key_features=key_features,
                    competitive_advantage=competitive_advantage,
                    next_steps=next_steps,
                    evidence=evidence[:5] if evidence else [],
                ))
                rank += 1

        # 수요 데이터 기반 추가 아이템
        if data.demands and data.demands.get("top_opportunities"):
            for opp in data.demands["top_opportunities"][:3]:
                if rank > 8:  # 최대 8개
                    break

                representative = opp.get("representative", "")
                priority_score = opp.get("priority_score", 50)
                business_potential = opp.get("business_potential", "medium")

                if priority_score >= 60:  # 우선순위 높은 것만
                    items.append(BusinessItem(
                        rank=rank,
                        title=representative[:100] if representative else f"Demand-based Opportunity #{rank}",
                        category="미충족 수요 해결",
                        opportunity_score=priority_score,
                        market_potential="높음" if business_potential == "high" else "중간",
                        risk_level="낮음" if priority_score >= 70 else "중간",
                        description=f"Users are expressing demand for solutions related to: {representative[:200]}",
                        target_audience="Reddit community members with specific needs",
                        key_features=["User-requested functionality", "Pain point solution", "Community-validated need"],
                        competitive_advantage="Direct response to validated user demand",
                        next_steps=self._generate_next_steps("unmet_need", priority_score),
                        evidence=opp.get("sample_texts", [])[:3],
                    ))
                    rank += 1

        return items

    def _infer_target_audience(self, title: str, description: str) -> str:
        """타겟 고객을 추론한다."""
        text = (title + " " + description).lower()

        if any(word in text for word in ["developer", "code", "programming", "api"]):
            return "소프트웨어 개발자 및 기술 전문가"
        elif any(word in text for word in ["ai", "machine learning", "automation"]):
            return "AI/ML 기술에 관심 있는 전문가 및 기업"
        elif any(word in text for word in ["business", "enterprise", "team"]):
            return "기업 고객 및 비즈니스 팀"
        elif any(word in text for word in ["student", "learning", "education"]):
            return "학생 및 교육 관련 사용자"
        elif any(word in text for word in ["creative", "design", "content"]):
            return "크리에이터 및 디자이너"
        else:
            return "일반 사용자 및 얼리 어답터"

    def _infer_key_features(self, title: str, description: str, insight_type: str) -> list[str]:
        """핵심 기능을 추론한다."""
        features = []
        text = (title + " " + description).lower()

        # 공통 기능
        if "ai" in text or "automated" in text:
            features.append("AI 기반 자동화")
        if "real-time" in text or "instant" in text:
            features.append("실시간 처리")
        if "collaboration" in text or "team" in text:
            features.append("협업 기능")
        if "integration" in text or "api" in text:
            features.append("외부 서비스 연동")
        if "privacy" in text or "secure" in text:
            features.append("보안 및 프라이버시")

        # 유형별 기본 기능
        type_features = {
            "market_gap": ["차별화된 핵심 기능", "사용자 친화적 인터페이스"],
            "improvement_opportunity": ["기존 솔루션 대비 개선된 UX", "성능 최적화"],
            "emerging_trend": ["최신 기술 적용", "확장 가능한 아키텍처"],
            "competitive_weakness": ["경쟁사 약점 보완", "차별화된 고객 경험"],
            "unmet_need": ["핵심 문제 해결", "직관적인 워크플로우"],
        }

        features.extend(type_features.get(insight_type, ["핵심 가치 제공"])[:2])

        return features[:5]

    def _infer_competitive_advantage(self, title: str, insight_type: str, data: Any) -> str:
        """경쟁 우위를 추론한다."""
        if insight_type == "market_gap":
            return "시장 내 미개척 영역 선점으로 인한 선발자 우위"
        elif insight_type == "competitive_weakness":
            if data.competition and data.competition.get("insights"):
                return "경쟁사 약점을 보완한 차별화된 솔루션 제공"
            return "경쟁사 대비 개선된 사용자 경험 제공"
        elif insight_type == "emerging_trend":
            return "트렌드 선도를 통한 시장 리더십 확보"
        elif insight_type == "unmet_need":
            return "검증된 사용자 수요에 기반한 제품-시장 적합성"
        else:
            return "커뮤니티 인사이트 기반의 차별화된 접근"

    def _generate_next_steps(self, insight_type: str, score: float) -> list[str]:
        """다음 단계를 생성한다."""
        base_steps = []

        if score >= 80:
            base_steps = [
                "MVP 개발 및 초기 사용자 테스트 진행",
                "핵심 타겟 고객 인터뷰 실시",
                "경쟁사 분석 및 차별화 전략 수립",
            ]
        elif score >= 60:
            base_steps = [
                "시장 조사 및 수요 검증 심화",
                "프로토타입 개발 및 피드백 수집",
                "비즈니스 모델 구체화",
            ]
        else:
            base_steps = [
                "추가 데이터 수집 및 트렌드 모니터링",
                "유사 시장 사례 조사",
                "잠재 고객 인터뷰를 통한 수요 검증",
            ]

        type_steps = {
            "market_gap": ["시장 규모 및 성장성 분석", "진입 장벽 평가"],
            "improvement_opportunity": ["기존 솔루션 벤치마킹", "개선점 우선순위화"],
            "emerging_trend": ["기술 트렌드 심층 분석", "얼리 어답터 커뮤니티 접근"],
            "competitive_weakness": ["경쟁사 분석 리포트 작성", "차별화 포인트 정의"],
            "unmet_need": ["Pain Point 심층 인터뷰", "솔루션 가치 제안 검증"],
        }

        return base_steps + type_steps.get(insight_type, [])[:2]

    def _analyze_trends(self, data: Any) -> dict[str, Any]:
        """트렌드를 분석한다."""
        analysis = {
            "total_keywords": 0,
            "top_keywords": [],
            "rising_topics": [],
            "trend_summary": "",
        }

        if data.keywords:
            analysis["total_keywords"] = len(data.keywords)
            analysis["top_keywords"] = [
                {"keyword": kw.get("keyword", ""), "score": kw.get("score", 0)}
                for kw in data.keywords[:10]
            ]

        if data.trends:
            analysis["rising_topics"] = [
                {"topic": t.get("keyword", ""), "trend": t.get("trend", "stable")}
                for t in data.trends[:5]
            ]

        # 트렌드 요약 생성
        if analysis["top_keywords"]:
            top_kws = ", ".join([kw["keyword"] for kw in analysis["top_keywords"][:5]])
            analysis["trend_summary"] = f"주요 키워드: {top_kws}. 커뮤니티에서 이러한 주제에 대한 논의가 활발합니다."
        else:
            analysis["trend_summary"] = "트렌드 데이터가 충분하지 않습니다."

        return analysis

    def _analyze_demands(self, data: Any) -> dict[str, Any]:
        """수요를 분석한다."""
        analysis = {
            "total_demands": 0,
            "by_category": {},
            "top_opportunities": [],
            "demand_summary": "",
        }

        if data.demands:
            analysis["total_demands"] = data.demands.get("total_demands", 0)
            analysis["by_category"] = data.demands.get("by_category", {})
            analysis["top_opportunities"] = data.demands.get("top_opportunities", [])[:5]

            if analysis["top_opportunities"]:
                analysis["demand_summary"] = (
                    f"총 {analysis['total_demands']}개의 수요 신호가 감지되었습니다. "
                    "사용자들은 새로운 기능, 개선된 경험, 해결되지 않은 문제에 대한 "
                    "솔루션을 요구하고 있습니다."
                )
            else:
                analysis["demand_summary"] = "수요 데이터가 충분하지 않습니다."
        else:
            analysis["demand_summary"] = "수요 분석 데이터가 없습니다."

        return analysis

    def _analyze_competition(self, data: Any) -> dict[str, Any]:
        """경쟁을 분석한다."""
        analysis = {
            "entities_mentioned": [],
            "sentiment_distribution": {},
            "key_complaints": [],
            "competition_summary": "",
        }

        if data.competition:
            if data.competition.get("insights"):
                for insight in data.competition["insights"][:10]:
                    analysis["entities_mentioned"].append({
                        "name": insight.get("entity_name", ""),
                        "sentiment": insight.get("sentiment", "neutral"),
                        "mentions": insight.get("mention_count", 0),
                    })

            analysis["sentiment_distribution"] = data.competition.get("sentiment", {})
            analysis["key_complaints"] = data.competition.get("complaints", [])[:5]

            if analysis["entities_mentioned"]:
                entities = ", ".join([e["name"] for e in analysis["entities_mentioned"][:5]])
                analysis["competition_summary"] = (
                    f"주요 언급 브랜드/제품: {entities}. "
                    "커뮤니티에서 다양한 솔루션에 대한 논의가 이루어지고 있으며, "
                    "일부 제품에 대한 불만과 대안 요구가 있습니다."
                )
            else:
                analysis["competition_summary"] = "경쟁 분석 데이터가 충분하지 않습니다."
        else:
            analysis["competition_summary"] = "경쟁 분석 데이터가 없습니다."

        return analysis

    def _generate_executive_summary(
        self, data: Any, business_items: list[BusinessItem], trend_analysis: dict
    ) -> str:
        """Executive Summary를 생성한다."""
        subreddit = data.subreddit
        post_count = data.post_count
        insights_count = len(data.insights) if data.insights else 0
        items_count = len(business_items)

        if not business_items:
            return (
                f"r/{subreddit} 커뮤니티의 {post_count}개 게시물을 분석했습니다. "
                "현재 데이터로는 명확한 비즈니스 기회를 도출하기 어렵습니다. "
                "추가 데이터 수집 및 분석이 권장됩니다."
            )

        top_item = business_items[0]
        top_keywords = ", ".join([kw["keyword"] for kw in trend_analysis.get("top_keywords", [])[:3]])

        return (
            f"r/{subreddit} 커뮤니티의 {post_count}개 게시물 분석 결과, "
            f"{insights_count}개의 인사이트와 {items_count}개의 비즈니스 기회를 도출했습니다.\n\n"
            f"**최우선 기회**: {top_item.title}\n"
            f"- 기회 점수: {top_item.opportunity_score:.1f}/100\n"
            f"- 시장 잠재력: {top_item.market_potential}\n"
            f"- 리스크 수준: {top_item.risk_level}\n\n"
            f"**주요 트렌드**: {top_keywords if top_keywords else '분석 중'}\n\n"
            "이 보고서는 Reddit 커뮤니티의 실제 대화를 기반으로 생성되었으며, "
            "비즈니스 의사결정의 참고자료로 활용할 수 있습니다."
        )

    def _generate_market_overview(self, data: Any, trend_analysis: dict) -> dict[str, Any]:
        """시장 개요를 생성한다."""
        return {
            "community_size": f"r/{data.subreddit}",
            "activity_level": "활발" if data.post_count >= 100 else "보통" if data.post_count >= 50 else "낮음",
            "data_quality": "충분" if len(data.insights or []) >= 5 else "보통" if len(data.insights or []) >= 2 else "추가 필요",
            "key_topics": [kw["keyword"] for kw in trend_analysis.get("top_keywords", [])[:5]],
            "market_maturity": self._assess_market_maturity(data),
        }

    def _assess_market_maturity(self, data: Any) -> str:
        """시장 성숙도를 평가한다."""
        if data.competition and len(data.competition.get("insights", [])) >= 5:
            return "성숙 시장 - 기존 플레이어 다수 존재"
        elif data.competition and len(data.competition.get("insights", [])) >= 2:
            return "성장 시장 - 일부 솔루션 존재, 기회 있음"
        else:
            return "초기 시장 - 신규 진입 기회"

    def _generate_recommendations(
        self,
        business_items: list[BusinessItem],
        demand_analysis: dict,
        competition_analysis: dict,
    ) -> list[str]:
        """추천 사항을 생성한다."""
        recommendations = []

        if business_items:
            top_item = business_items[0]
            recommendations.append(
                f"1. **{top_item.title}** 기회를 우선 검토하세요. "
                f"(점수: {top_item.opportunity_score:.1f}/100)"
            )

        if demand_analysis.get("top_opportunities"):
            recommendations.append(
                "2. 사용자 수요가 높은 기능에 집중하여 MVP를 설계하세요."
            )

        if competition_analysis.get("key_complaints"):
            recommendations.append(
                "3. 경쟁 제품의 주요 불만사항을 해결하는 차별화 전략을 수립하세요."
            )

        recommendations.extend([
            "4. 타겟 커뮤니티에서 직접 피드백을 수집하여 가설을 검증하세요.",
            "5. 소규모 테스트를 통해 시장 반응을 확인한 후 본격적으로 진행하세요.",
            "6. 경쟁사 동향을 지속적으로 모니터링하세요.",
        ])

        return recommendations[:6]

    def _identify_risk_factors(self, data: Any, competition_analysis: dict) -> list[str]:
        """리스크 요인을 식별한다."""
        risks = []

        # 데이터 관련 리스크
        if data.post_count < 50:
            risks.append("데이터 샘플 크기가 작아 분석 결과의 신뢰도가 제한될 수 있음")

        # 경쟁 관련 리스크
        if len(competition_analysis.get("entities_mentioned", [])) >= 5:
            risks.append("다수의 경쟁자가 존재하여 시장 진입 장벽이 높을 수 있음")

        # 일반적 리스크
        risks.extend([
            "Reddit 커뮤니티 의견이 전체 시장을 대표하지 않을 수 있음",
            "기술 트렌드의 빠른 변화로 인한 시장 환경 불확실성",
            "초기 사용자 확보 및 제품-시장 적합성 달성의 어려움",
        ])

        return risks[:5]

    def _generate_conclusion(
        self, business_items: list[BusinessItem], recommendations: list[str]
    ) -> str:
        """결론을 생성한다."""
        if not business_items:
            return (
                "현재 데이터로는 명확한 비즈니스 기회를 도출하기 어렵습니다. "
                "추가 데이터 수집 및 다양한 커뮤니티 분석을 통해 "
                "더 많은 인사이트를 확보하시기 바랍니다."
            )

        top_items = business_items[:3]
        items_summary = ", ".join([f"'{item.title[:30]}...'" for item in top_items])

        return (
            f"본 분석을 통해 {len(business_items)}개의 비즈니스 기회를 도출했습니다. "
            f"특히 {items_summary} 등의 기회가 높은 잠재력을 보이고 있습니다.\n\n"
            "제시된 추천 사항을 참고하여 시장 검증을 진행하시고, "
            "지속적인 커뮤니티 모니터링을 통해 트렌드 변화에 대응하시기 바랍니다. "
            "본 보고서는 Reddit 데이터 기반의 분석이므로, "
            "최종 의사결정 시 추가적인 시장 조사를 권장합니다."
        )

    def generate_markdown_report(self, subreddit: str | None = None) -> str | None:
        """마크다운 형식의 보고서를 생성한다.

        Args:
            subreddit: 서브레딧 이름

        Returns:
            마크다운 문자열 또는 None
        """
        report = self.generate_report(subreddit)
        if not report:
            return None

        md = []

        # 헤더
        md.append(f"# 비즈니스 분석 보고서: r/{report.subreddit}")
        md.append("")
        md.append(f"**생성일시**: {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}")
        md.append(f"**분석 기간**: {report.analysis_period}")
        md.append(f"**분석 게시물 수**: {report.total_posts_analyzed:,}개")
        md.append("")
        md.append("---")
        md.append("")

        # Executive Summary
        md.append("## 1. Executive Summary")
        md.append("")
        md.append(report.executive_summary)
        md.append("")

        # 시장 개요
        md.append("## 2. 시장 개요")
        md.append("")
        md.append(f"- **커뮤니티**: {report.market_overview.get('community_size', 'N/A')}")
        md.append(f"- **활동 수준**: {report.market_overview.get('activity_level', 'N/A')}")
        md.append(f"- **데이터 품질**: {report.market_overview.get('data_quality', 'N/A')}")
        md.append(f"- **시장 성숙도**: {report.market_overview.get('market_maturity', 'N/A')}")
        if report.market_overview.get("key_topics"):
            topics = ", ".join(report.market_overview["key_topics"])
            md.append(f"- **주요 토픽**: {topics}")
        md.append("")

        # 비즈니스 아이템
        md.append("## 3. 도출된 비즈니스 아이템")
        md.append("")

        if report.business_items:
            for item in report.business_items:
                md.append(f"### 3.{item.rank}. {item.title}")
                md.append("")
                md.append(f"**카테고리**: {item.category}")
                md.append("")
                md.append("| 평가 항목 | 값 |")
                md.append("|----------|-----|")
                md.append(f"| 기회 점수 | {item.opportunity_score:.1f}/100 |")
                md.append(f"| 시장 잠재력 | {item.market_potential} |")
                md.append(f"| 리스크 수준 | {item.risk_level} |")
                md.append("")
                md.append(f"**설명**: {item.description}")
                md.append("")
                md.append(f"**타겟 고객**: {item.target_audience}")
                md.append("")
                md.append("**핵심 기능**:")
                for feature in item.key_features:
                    md.append(f"- {feature}")
                md.append("")
                md.append(f"**경쟁 우위**: {item.competitive_advantage}")
                md.append("")
                md.append("**다음 단계**:")
                for step in item.next_steps:
                    md.append(f"1. {step}")
                md.append("")

                if item.evidence:
                    md.append("**근거 데이터**:")
                    for ev in item.evidence[:3]:
                        md.append(f"> {ev[:200]}...")
                    md.append("")

                md.append("---")
                md.append("")
        else:
            md.append("*도출된 비즈니스 아이템이 없습니다.*")
            md.append("")

        # 트렌드 분석
        md.append("## 4. 트렌드 분석")
        md.append("")
        md.append(report.trend_analysis.get("trend_summary", ""))
        md.append("")

        if report.trend_analysis.get("top_keywords"):
            md.append("### 상위 키워드")
            md.append("")
            md.append("| 순위 | 키워드 | 점수 |")
            md.append("|------|--------|------|")
            for i, kw in enumerate(report.trend_analysis["top_keywords"][:10], 1):
                md.append(f"| {i} | {kw['keyword']} | {kw['score']:.2f} |")
            md.append("")

        # 수요 분석
        md.append("## 5. 수요 분석")
        md.append("")
        md.append(report.demand_analysis.get("demand_summary", ""))
        md.append("")

        if report.demand_analysis.get("by_category"):
            md.append("### 카테고리별 수요")
            md.append("")
            for cat, count in report.demand_analysis["by_category"].items():
                md.append(f"- **{cat}**: {count}건")
            md.append("")

        # 경쟁 분석
        md.append("## 6. 경쟁 분석")
        md.append("")
        md.append(report.competition_analysis.get("competition_summary", ""))
        md.append("")

        if report.competition_analysis.get("entities_mentioned"):
            md.append("### 주요 언급 브랜드/제품")
            md.append("")
            md.append("| 이름 | 감성 | 언급 수 |")
            md.append("|------|------|---------|")
            for entity in report.competition_analysis["entities_mentioned"][:10]:
                md.append(f"| {entity['name']} | {entity['sentiment']} | {entity['mentions']} |")
            md.append("")

        # 추천 사항
        md.append("## 7. 추천 사항")
        md.append("")
        for rec in report.recommendations:
            md.append(rec)
            md.append("")

        # 리스크 요인
        md.append("## 8. 리스크 요인")
        md.append("")
        for risk in report.risk_factors:
            md.append(f"- {risk}")
        md.append("")

        # 결론
        md.append("## 9. 결론")
        md.append("")
        md.append(report.conclusion)
        md.append("")

        # 면책조항
        md.append("---")
        md.append("")
        md.append("*본 보고서는 Reddit 커뮤니티 데이터를 기반으로 자동 생성되었습니다. "
                  "실제 비즈니스 의사결정 시 추가적인 시장 조사 및 전문가 검토를 권장합니다.*")
        md.append("")
        md.append(f"*Generated by Reddit Insight - {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}*")

        return "\n".join(md)


@lru_cache(maxsize=1)
def get_report_service() -> ReportService:
    """ReportService 싱글톤 인스턴스를 반환한다."""
    return ReportService()

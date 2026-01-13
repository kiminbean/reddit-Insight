"""
Report Generator Module.

템플릿과 데이터를 결합하여 마크다운 리포트를 생성하는 모듈.
ReportGenerator, ReportConfig, ReportDataCollector를 제공한다.

Example:
    >>> from reddit_insight.reports import ReportGenerator, ReportConfig
    >>> from reddit_insight.reports import ReportDataCollector
    >>> generator = ReportGenerator()
    >>> data = ReportDataCollector(
    ...     trend_report=trend_report,
    ...     demand_report=demand_report
    ... )
    >>> full_report = generator.generate_full_report(data)
    >>> generator.save_report(full_report, "output/full_report.md")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from reddit_insight.reports.templates import (
    ReportTemplate,
    ReportType,
    TemplateRegistry,
)

if TYPE_CHECKING:
    from reddit_insight.analysis.competitive import CompetitiveReport
    from reddit_insight.analysis.demand_analyzer import DemandReport
    from reddit_insight.insights.feasibility import InsightReport


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class ReportConfig:
    """
    리포트 생성 설정.

    리포트 커스터마이징을 위한 설정 옵션을 제공한다.

    Attributes:
        title: 리포트 제목 (기본값: "Reddit Insight Report")
        author: 작성자 (기본값: "Reddit Insight")
        include_toc: 목차 포함 여부 (기본값: True)
        include_summary: 요약 포함 여부 (기본값: True)
        include_metadata: 메타데이터 포함 여부 (기본값: True)
        max_items_per_section: 섹션당 최대 항목 수 (기본값: 10)

    Example:
        >>> config = ReportConfig(
        ...     title="Weekly Reddit Analysis",
        ...     max_items_per_section=15
        ... )
        >>> generator = ReportGenerator(config=config)
    """

    title: str = "Reddit Insight Report"
    author: str = "Reddit Insight"
    include_toc: bool = True
    include_summary: bool = True
    include_metadata: bool = True
    max_items_per_section: int = 10

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"ReportConfig(title='{self.title}', "
            f"author='{self.author}', "
            f"max_items={self.max_items_per_section})"
        )


@dataclass
class TrendReportData:
    """
    트렌드 리포트용 데이터 구조.

    KeywordTrendResult 목록을 템플릿 컨텍스트에 맞게 변환한 데이터.

    Attributes:
        title: 리포트 제목
        summary: 요약
        top_keywords: 상위 키워드 목록
        rising_keywords: 상승 키워드 목록
        period: 분석 기간 정보
        trend_changes: 트렌드 변화 요약
    """

    title: str = "Trend Analysis Report"
    summary: str = ""
    top_keywords: list[dict[str, Any]] = field(default_factory=list)
    rising_keywords: list[dict[str, Any]] = field(default_factory=list)
    period: dict[str, str] | None = None
    trend_changes: list[str] = field(default_factory=list)


@dataclass
class ReportDataCollector:
    """
    리포트 데이터 수집기.

    여러 분석 결과를 종합하여 리포트 생성에 필요한 데이터를 수집한다.

    Attributes:
        trend_report: 트렌드 분석 리포트 데이터
        demand_report: 수요 분석 리포트
        competitive_report: 경쟁 분석 리포트
        insight_report: 비즈니스 인사이트 리포트
        metadata: 추가 메타데이터

    Example:
        >>> collector = ReportDataCollector(
        ...     trend_report=trend_data,
        ...     demand_report=demand_report,
        ...     metadata={"subreddit": "python"}
        ... )
        >>> report = generator.generate_full_report(collector)
    """

    trend_report: TrendReportData | None = None
    demand_report: DemandReport | None = None
    competitive_report: CompetitiveReport | None = None
    insight_report: InsightReport | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        """String representation for debugging."""
        reports = []
        if self.trend_report:
            reports.append("trend")
        if self.demand_report:
            reports.append("demand")
        if self.competitive_report:
            reports.append("competitive")
        if self.insight_report:
            reports.append("insight")
        return f"ReportDataCollector(reports=[{', '.join(reports)}])"

    def has_any_data(self) -> bool:
        """Check if any report data is present."""
        return any([
            self.trend_report,
            self.demand_report,
            self.competitive_report,
            self.insight_report,
        ])

    def get_available_reports(self) -> list[str]:
        """Get list of available report types."""
        available = []
        if self.trend_report:
            available.append("trend")
        if self.demand_report:
            available.append("demand")
        if self.competitive_report:
            available.append("competitive")
        if self.insight_report:
            available.append("insight")
        return available


# =============================================================================
# REPORT GENERATOR
# =============================================================================


class ReportGenerator:
    """
    리포트 생성기.

    템플릿과 데이터를 결합하여 마크다운 리포트를 생성한다.

    Attributes:
        _registry: 템플릿 레지스트리
        _config: 리포트 설정

    Example:
        >>> generator = ReportGenerator()
        >>> trend_md = generator.generate_trend_report(trend_data)
        >>> generator.save_report(trend_md, "output/trend.md")

        >>> # Full report generation
        >>> data = ReportDataCollector(...)
        >>> full_md = generator.generate_full_report(data)
        >>> exported = generator.export_all(data, "output/")
    """

    def __init__(
        self,
        template_registry: TemplateRegistry | None = None,
        config: ReportConfig | None = None,
    ) -> None:
        """
        리포트 생성기 초기화.

        Args:
            template_registry: 템플릿 레지스트리 (None이면 기본 템플릿 로드)
            config: 리포트 설정 (None이면 기본 설정 사용)
        """
        self._config = config or ReportConfig()

        if template_registry is not None:
            self._registry = template_registry
        else:
            self._registry = TemplateRegistry()
            self._registry.load_defaults()

    def __repr__(self) -> str:
        """String representation for debugging."""
        template_count = len(self._registry.list_templates())
        return (
            f"ReportGenerator(templates={template_count}, "
            f"config={self._config!r})"
        )

    @property
    def config(self) -> ReportConfig:
        """Get report configuration."""
        return self._config

    @property
    def registry(self) -> TemplateRegistry:
        """Get template registry."""
        return self._registry

    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================

    def _render(
        self,
        template: ReportTemplate,
        context: dict[str, Any],
    ) -> str:
        """
        템플릿 렌더링.

        Args:
            template: 리포트 템플릿
            context: 템플릿 변수 딕셔너리

        Returns:
            렌더링된 마크다운 문자열
        """
        return template.render(**context)

    def _get_template(
        self,
        report_type: ReportType,
        template_name: str | None = None,
    ) -> ReportTemplate:
        """
        템플릿 가져오기.

        Args:
            report_type: 리포트 유형
            template_name: 템플릿 이름 (None이면 기본 템플릿 사용)

        Returns:
            리포트 템플릿
        """
        if template_name:
            return self._registry.get(template_name)

        # Get default template for report type
        templates = self._registry.list_by_type(report_type)
        if templates:
            return templates[0]

        raise KeyError(f"No template found for report type: {report_type.value}")

    def _prepare_trend_context(
        self,
        data: TrendReportData,
    ) -> dict[str, Any]:
        """
        트렌드 리포트 컨텍스트 준비.

        Args:
            data: 트렌드 리포트 데이터

        Returns:
            템플릿 컨텍스트 딕셔너리
        """
        max_items = self._config.max_items_per_section

        return {
            "title": data.title or self._config.title,
            "summary": data.summary,
            "top_keywords": data.top_keywords[:max_items],
            "rising_keywords": data.rising_keywords[:max_items],
            "period": data.period,
            "trend_changes": data.trend_changes[:max_items],
        }

    def _prepare_demand_context(
        self,
        report: DemandReport,
    ) -> dict[str, Any]:
        """
        수요 리포트 컨텍스트 준비.

        Args:
            report: 수요 분석 리포트

        Returns:
            템플릿 컨텍스트 딕셔너리
        """
        max_items = self._config.max_items_per_section

        # Convert DemandCategory keys to strings
        categories = {
            cat.value: count for cat, count in report.by_category.items()
        }

        # Convert PrioritizedDemand to dict format for template
        top_demands = []
        for opp in report.top_opportunities[:max_items]:
            top_demands.append({
                "title": opp.cluster.representative[:60],
                "description": opp.cluster.representative,
                "category": opp.cluster.primary_category.value if opp.cluster.primary_category else "unknown",
                "frequency": opp.cluster.frequency,
                "priority_score": opp.priority.total_score,
                "sample_text": opp.cluster.representative,
            })

        # Priority analysis
        priority_analysis = {
            "high": [
                opp.cluster.representative[:50]
                for opp in report.top_opportunities
                if opp.business_potential == "high"
            ][:5],
            "medium": [
                opp.cluster.representative[:50]
                for opp in report.top_opportunities
                if opp.business_potential == "medium"
            ][:5],
            "low": [
                opp.cluster.representative[:50]
                for opp in report.top_opportunities
                if opp.business_potential == "low"
            ][:5],
        }

        return {
            "title": f"{self._config.title} - Demand Analysis",
            "total_demands": report.total_demands,
            "categories": categories,
            "top_demands": top_demands,
            "priority_analysis": priority_analysis,
            "analyzed_posts": report.total_demands,
        }

    def _prepare_competitive_context(
        self,
        report: CompetitiveReport,
    ) -> dict[str, Any]:
        """
        경쟁 분석 리포트 컨텍스트 준비.

        Args:
            report: 경쟁 분석 리포트

        Returns:
            템플릿 컨텍스트 딕셔너리
        """
        max_items = self._config.max_items_per_section

        # Convert insights to entities
        entities = []
        for insight in report.insights[:max_items]:
            entities.append({
                "name": insight.entity.name,
                "type": insight.entity.entity_type.value,
                "mention_count": insight.complaint_count,
                "avg_sentiment": (insight.overall_sentiment.compound + 1) / 2,  # -1~1 to 0~1
            })

        # Sentiment summary
        positive = sum(
            1 for i in report.insights
            if i.overall_sentiment.compound > 0.1
        )
        negative = sum(
            1 for i in report.insights
            if i.overall_sentiment.compound < -0.1
        )
        neutral = len(report.insights) - positive - negative
        total = max(1, len(report.insights))

        sentiment_summary = {
            "positive": positive / total,
            "neutral": neutral / total,
            "negative": negative / total,
        }

        # Complaints
        complaints = []
        for complaint in report.top_complaints[:max_items]:
            complaints.append({
                "type": complaint.complaint_type.value,
                "severity": complaint.severity,
                "frequency": 1,
                "examples": [complaint.context[:150]],
            })

        # Alternatives
        alternatives = []
        for from_name, to_name, count in report.popular_switches[:max_items]:
            alternatives.append({
                "from_product": from_name,
                "to_product": to_name,
                "reason": "User preference",
                "frequency": count,
            })

        return {
            "title": f"{self._config.title} - Competitive Analysis",
            "entities": entities,
            "sentiment_summary": sentiment_summary,
            "complaints": complaints,
            "alternatives": alternatives,
        }

    def _prepare_insight_context(
        self,
        report: InsightReport,
    ) -> dict[str, Any]:
        """
        인사이트 리포트 컨텍스트 준비.

        Args:
            report: 인사이트 리포트

        Returns:
            템플릿 컨텍스트 딕셔너리
        """
        max_items = self._config.max_items_per_section

        # Insights
        insights = []
        for rec in report.recommendations[:max_items]:
            insights.append({
                "title": rec.insight.title,
                "type": rec.insight.insight_type.value,
                "confidence": rec.insight.confidence,
                "impact": rec.combined_score / 100,
                "description": rec.insight.description,
                "evidence": [e.summary for e in rec.insight.evidence[:3]],
            })

        # Opportunities
        opportunities = []
        for rec in report.recommendations[:max_items]:
            opportunities.append({
                "rank": rec.final_rank,
                "title": rec.insight.title,
                "score": {"total": rec.combined_score, "grade": rec.business_score.grade},
                "total_score": rec.combined_score,
                "grade": rec.business_score.grade,
                "insight": {"title": rec.insight.title},
            })

        # Recommendations
        recommendations = []
        for rec in report.recommendations[:max_items]:
            recommendations.append({
                "title": rec.insight.title,
                "priority": rec.feasibility_score.risk_level,
                "expected_impact": f"Score: {rec.combined_score:.1f}",
                "resources": rec.feasibility_score.risk_level,
                "description": rec.insight.description[:200],
                "steps": rec.action_items[:5],
            })

        # Feasibility
        feasibility = {}
        if report.recommendations:
            top = report.recommendations[0]
            for factor in top.feasibility_score.factors:
                feasibility[factor.factor.value.replace("_", " ").title()] = {
                    "level": "High" if factor.score >= 70 else "Medium" if factor.score >= 40 else "Low",
                    "score": factor.score / 100,
                }

        return {
            "title": f"{self._config.title} - Business Insights",
            "insights": insights,
            "opportunities": opportunities,
            "recommendations": recommendations,
            "feasibility": feasibility,
        }

    def _prepare_full_context(
        self,
        data: ReportDataCollector,
    ) -> dict[str, Any]:
        """
        종합 리포트 컨텍스트 준비.

        Args:
            data: 리포트 데이터 수집기

        Returns:
            템플릿 컨텍스트 딕셔너리
        """
        context: dict[str, Any] = {
            "title": self._config.title,
            "executive_summary": "",
            "trend_section": None,
            "demand_section": None,
            "competitive_section": None,
            "insight_section": None,
            "conclusions": None,
            "analysis_period": data.metadata.get("analysis_period", "N/A"),
        }

        # Executive summary
        summary_parts = []
        available = data.get_available_reports()
        summary_parts.append(f"This report includes analysis from {len(available)} sources.")

        if data.trend_report and data.trend_report.top_keywords:
            summary_parts.append(
                f"Analyzed {len(data.trend_report.top_keywords)} trending keywords."
            )

        if data.demand_report:
            summary_parts.append(
                f"Identified {data.demand_report.total_clusters} demand clusters "
                f"from {data.demand_report.total_demands} signals."
            )

        if data.competitive_report:
            summary_parts.append(
                f"Analyzed {data.competitive_report.entities_analyzed} entities "
                f"with {len(data.competitive_report.top_complaints)} complaints."
            )

        if data.insight_report:
            summary_parts.append(
                f"Generated {len(data.insight_report.recommendations)} actionable recommendations."
            )

        context["executive_summary"] = " ".join(summary_parts)

        # Trend section
        if data.trend_report:
            context["trend_section"] = {
                "summary": data.trend_report.summary,
                "top_keywords": data.trend_report.top_keywords[:5],
                "rising_keywords": data.trend_report.rising_keywords[:5],
            }

        # Demand section
        if data.demand_report:
            top_demands = []
            for opp in data.demand_report.top_opportunities[:5]:
                top_demands.append({
                    "title": opp.cluster.representative[:40],
                    "description": opp.cluster.representative,
                    "category": opp.cluster.primary_category.value if opp.cluster.primary_category else "unknown",
                })

            # Find top category
            top_category = "N/A"
            if data.demand_report.by_category:
                top_cat = max(
                    data.demand_report.by_category.items(),
                    key=lambda x: x[1]
                )
                top_category = top_cat[0].value

            context["demand_section"] = {
                "total_demands": data.demand_report.total_demands,
                "top_category": top_category,
                "top_demands": top_demands,
            }

        # Competitive section
        if data.competitive_report:
            # Sentiment summary
            positive = sum(
                1 for i in data.competitive_report.insights
                if i.overall_sentiment.compound > 0.1
            )
            negative = sum(
                1 for i in data.competitive_report.insights
                if i.overall_sentiment.compound < -0.1
            )
            total = max(1, len(data.competitive_report.insights))

            top_complaints = []
            for c in data.competitive_report.top_complaints[:5]:
                top_complaints.append({
                    "type": c.complaint_type.value,
                    "description": c.context[:50] if c.context else "",
                })

            context["competitive_section"] = {
                "sentiment_summary": {
                    "positive": positive / total,
                    "negative": negative / total,
                },
                "top_complaints": top_complaints,
            }

        # Insight section
        if data.insight_report:
            top_insights = []
            for rec in data.insight_report.recommendations[:3]:
                top_insights.append({
                    "title": rec.insight.title,
                    "description": rec.insight.description[:100],
                })

            opportunities = []
            for rec in data.insight_report.recommendations[:5]:
                opportunities.append({
                    "rank": rec.final_rank,
                    "title": rec.insight.title,
                    "total_score": rec.combined_score,
                })

            context["insight_section"] = {
                "top_insights": top_insights,
                "opportunities": opportunities,
            }

        # Conclusions
        conclusions = {
            "key_findings": [],
            "recommendations": [],
            "next_steps": [],
        }

        if data.insight_report and data.insight_report.key_findings:
            conclusions["key_findings"] = data.insight_report.key_findings[:5]

        if data.insight_report and data.insight_report.recommendations:
            conclusions["recommendations"] = [
                {
                    "title": rec.insight.title,
                    "priority": rec.feasibility_score.risk_level,
                    "description": rec.insight.description[:100],
                }
                for rec in data.insight_report.recommendations[:3]
            ]
            conclusions["next_steps"] = data.insight_report.recommendations[0].next_steps[:5]

        context["conclusions"] = conclusions

        return context

    # =========================================================================
    # PUBLIC METHODS - INDIVIDUAL REPORT GENERATION
    # =========================================================================

    def generate_trend_report(
        self,
        data: TrendReportData,
        template_name: str | None = None,
    ) -> str:
        """
        트렌드 리포트 생성.

        Args:
            data: 트렌드 리포트 데이터
            template_name: 사용할 템플릿 이름 (None이면 기본 템플릿)

        Returns:
            마크다운 형식 트렌드 리포트

        Example:
            >>> data = TrendReportData(
            ...     title="Weekly Trend Report",
            ...     top_keywords=[{"keyword": "AI", "score": 95}]
            ... )
            >>> md = generator.generate_trend_report(data)
        """
        template = self._get_template(ReportType.TREND, template_name)
        context = self._prepare_trend_context(data)
        return self._render(template, context)

    def generate_demand_report(
        self,
        report: DemandReport,
        template_name: str | None = None,
    ) -> str:
        """
        수요 리포트 생성.

        Args:
            report: 수요 분석 리포트
            template_name: 사용할 템플릿 이름 (None이면 기본 템플릿)

        Returns:
            마크다운 형식 수요 리포트

        Example:
            >>> md = generator.generate_demand_report(demand_report)
        """
        template = self._get_template(ReportType.DEMAND, template_name)
        context = self._prepare_demand_context(report)
        return self._render(template, context)

    def generate_competitive_report(
        self,
        report: CompetitiveReport,
        template_name: str | None = None,
    ) -> str:
        """
        경쟁 분석 리포트 생성.

        Args:
            report: 경쟁 분석 리포트
            template_name: 사용할 템플릿 이름 (None이면 기본 템플릿)

        Returns:
            마크다운 형식 경쟁 분석 리포트

        Example:
            >>> md = generator.generate_competitive_report(competitive_report)
        """
        template = self._get_template(ReportType.COMPETITIVE, template_name)
        context = self._prepare_competitive_context(report)
        return self._render(template, context)

    def generate_insight_report(
        self,
        report: InsightReport,
        template_name: str | None = None,
    ) -> str:
        """
        인사이트 리포트 생성.

        Args:
            report: 인사이트 리포트
            template_name: 사용할 템플릿 이름 (None이면 기본 템플릿)

        Returns:
            마크다운 형식 인사이트 리포트

        Example:
            >>> md = generator.generate_insight_report(insight_report)
        """
        template = self._get_template(ReportType.INSIGHT, template_name)
        context = self._prepare_insight_context(report)
        return self._render(template, context)

    # =========================================================================
    # PUBLIC METHODS - FULL REPORT GENERATION
    # =========================================================================

    def generate_full_report(
        self,
        data: ReportDataCollector,
    ) -> str:
        """
        종합 리포트 생성.

        모든 분석 결과를 통합하여 종합 리포트를 생성한다.

        Args:
            data: 리포트 데이터 수집기

        Returns:
            마크다운 형식 종합 리포트

        Example:
            >>> collector = ReportDataCollector(
            ...     trend_report=trend_data,
            ...     demand_report=demand_report
            ... )
            >>> full_md = generator.generate_full_report(collector)
        """
        if not data.has_any_data():
            return self._generate_empty_report()

        template = self._get_template(ReportType.FULL)
        context = self._prepare_full_context(data)
        return self._render(template, context)

    def _generate_empty_report(self) -> str:
        """빈 리포트 생성."""
        lines = [
            f"# {self._config.title}",
            "",
            f"> Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "## No Data Available",
            "",
            "No analysis data was provided for this report.",
            "",
            "---",
            "*Generated by Reddit Insight*",
        ]
        return "\n".join(lines)

    # =========================================================================
    # PUBLIC METHODS - FILE EXPORT
    # =========================================================================

    def save_report(
        self,
        content: str,
        filepath: Path | str,
        create_dirs: bool = True,
    ) -> Path:
        """
        리포트를 파일로 저장.

        Args:
            content: 리포트 내용 (마크다운 문자열)
            filepath: 저장할 파일 경로
            create_dirs: 디렉토리 자동 생성 여부 (기본값: True)

        Returns:
            저장된 파일의 Path 객체

        Raises:
            OSError: 파일 저장 실패 시

        Example:
            >>> generator.save_report(report_md, "output/report.md")
            PosixPath('output/report.md')
        """
        path = Path(filepath)

        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(content, encoding="utf-8")
        return path

    def export_all(
        self,
        data: ReportDataCollector,
        output_dir: Path | str,
    ) -> list[Path]:
        """
        모든 리포트를 파일로 내보내기.

        개별 리포트와 종합 리포트를 모두 생성하여 저장한다.

        Args:
            data: 리포트 데이터 수집기
            output_dir: 출력 디렉토리

        Returns:
            생성된 파일 경로 목록

        Example:
            >>> paths = generator.export_all(collector, "output/")
            >>> print(f"Generated {len(paths)} files")
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        exported: list[Path] = []

        # Export individual reports
        if data.trend_report:
            trend_md = self.generate_trend_report(data.trend_report)
            path = self.save_report(trend_md, output_path / "trend_report.md")
            exported.append(path)

        if data.demand_report:
            demand_md = self.generate_demand_report(data.demand_report)
            path = self.save_report(demand_md, output_path / "demand_report.md")
            exported.append(path)

        if data.competitive_report:
            competitive_md = self.generate_competitive_report(data.competitive_report)
            path = self.save_report(competitive_md, output_path / "competitive_report.md")
            exported.append(path)

        if data.insight_report:
            insight_md = self.generate_insight_report(data.insight_report)
            path = self.save_report(insight_md, output_path / "insight_report.md")
            exported.append(path)

        # Export full report
        if data.has_any_data():
            full_md = self.generate_full_report(data)
            path = self.save_report(full_md, output_path / "full_report.md")
            exported.append(path)

        # Write metadata
        if self._config.include_metadata:
            metadata_path = self._write_metadata(output_path, data)
            exported.append(metadata_path)

        return exported

    def _write_metadata(
        self,
        output_dir: Path,
        data: ReportDataCollector,
    ) -> Path:
        """
        메타데이터 파일 생성.

        Args:
            output_dir: 출력 디렉토리
            data: 리포트 데이터 수집기

        Returns:
            메타데이터 파일 경로
        """
        metadata = {
            "generated_at": datetime.now(UTC).isoformat(),
            "generator_version": "1.0.0",
            "config": {
                "title": self._config.title,
                "author": self._config.author,
                "max_items_per_section": self._config.max_items_per_section,
            },
            "reports_included": data.get_available_reports(),
            "custom_metadata": data.metadata,
        }

        # Add report-specific metadata
        if data.trend_report:
            metadata["trend_summary"] = {
                "keyword_count": len(data.trend_report.top_keywords),
                "rising_count": len(data.trend_report.rising_keywords),
            }

        if data.demand_report:
            metadata["demand_summary"] = {
                "total_demands": data.demand_report.total_demands,
                "cluster_count": data.demand_report.total_clusters,
            }

        if data.competitive_report:
            metadata["competitive_summary"] = {
                "entities_analyzed": data.competitive_report.entities_analyzed,
                "complaint_count": len(data.competitive_report.top_complaints),
            }

        if data.insight_report:
            metadata["insight_summary"] = {
                "total_insights": data.insight_report.total_insights,
                "total_opportunities": data.insight_report.total_opportunities,
                "recommendation_count": len(data.insight_report.recommendations),
            }

        metadata_path = output_dir / "report_metadata.json"
        metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return metadata_path

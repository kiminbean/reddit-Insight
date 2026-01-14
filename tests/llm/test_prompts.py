"""프롬프트 템플릿 테스트."""

from __future__ import annotations

import pytest

from reddit_insight.llm.prompts import (
    CATEGORIZE_CONTENT,
    EXTRACT_INSIGHTS,
    SENTIMENT_ANALYSIS,
    SUMMARIZE_POSTS,
    TREND_INTERPRETATION,
    PromptCategory,
    PromptTemplate,
    get_template,
    list_templates,
    register_template,
    TEMPLATES,
)


class TestPromptTemplate:
    """PromptTemplate 클래스 테스트."""

    def test_create_template(self) -> None:
        """템플릿을 생성할 수 있다."""
        template = PromptTemplate(
            template="Hello, {name}!",
            version="1.0",
        )
        assert template.template == "Hello, {name}!"
        assert template.version == "1.0"

    def test_auto_extract_required_vars(self) -> None:
        """필수 변수가 자동으로 추출된다."""
        template = PromptTemplate(
            template="Hello, {name}! You are {age} years old.",
        )
        assert "name" in template.required_vars
        assert "age" in template.required_vars
        assert len(template.required_vars) == 2

    def test_format_success(self) -> None:
        """변수를 대입하여 포맷할 수 있다."""
        template = PromptTemplate(template="Hello, {name}!")
        result = template.format(name="World")
        assert result == "Hello, World!"

    def test_format_multiple_vars(self) -> None:
        """여러 변수를 대입할 수 있다."""
        template = PromptTemplate(template="{greeting}, {name}!")
        result = template.format(greeting="Hi", name="Alice")
        assert result == "Hi, Alice!"

    def test_format_missing_var_raises_error(self) -> None:
        """필수 변수가 누락되면 에러가 발생한다."""
        template = PromptTemplate(template="Hello, {name}!")
        with pytest.raises(ValueError, match="필수 변수 누락"):
            template.format()

    def test_estimate_tokens(self) -> None:
        """토큰 수를 추정할 수 있다."""
        template = PromptTemplate(template="Hello, {name}!")
        tokens = template.estimate_tokens(name="World")
        # "Hello, World!" = 13글자 / 3 ≈ 4
        assert tokens >= 1
        assert tokens < 20

    def test_get_hash(self) -> None:
        """해시 값을 얻을 수 있다."""
        template = PromptTemplate(template="Hello, {name}!", version="1.0")
        hash1 = template.get_hash()
        assert len(hash1) == 16

        # 버전이 다르면 해시도 다름
        template2 = PromptTemplate(template="Hello, {name}!", version="2.0")
        hash2 = template2.get_hash()
        assert hash1 != hash2

    def test_repr(self) -> None:
        """repr이 올바르게 동작한다."""
        template = PromptTemplate(
            template="Test {var}",
            version="1.0",
            category=PromptCategory.GENERAL,
        )
        repr_str = repr(template)
        assert "general" in repr_str
        assert "1.0" in repr_str


class TestBuiltInTemplates:
    """기본 제공 템플릿 테스트."""

    def test_summarize_posts_template(self) -> None:
        """SUMMARIZE_POSTS 템플릿이 올바르게 동작한다."""
        assert SUMMARIZE_POSTS.category == PromptCategory.SUMMARIZATION
        assert "posts" in SUMMARIZE_POSTS.required_vars

        result = SUMMARIZE_POSTS.format(posts="Post 1\nPost 2")
        assert "Post 1" in result
        assert "주요 주제" in result

    def test_categorize_content_template(self) -> None:
        """CATEGORIZE_CONTENT 템플릿이 올바르게 동작한다."""
        assert CATEGORIZE_CONTENT.category == PromptCategory.CATEGORIZATION
        assert "text" in CATEGORIZE_CONTENT.required_vars
        assert "categories" in CATEGORIZE_CONTENT.required_vars

        result = CATEGORIZE_CONTENT.format(
            text="Test text",
            categories="Category A, Category B",
        )
        assert "Test text" in result
        assert "Category A" in result

    def test_extract_insights_template(self) -> None:
        """EXTRACT_INSIGHTS 템플릿이 올바르게 동작한다."""
        assert EXTRACT_INSIGHTS.category == PromptCategory.EXTRACTION
        assert "analysis_data" in EXTRACT_INSIGHTS.required_vars
        assert "subreddit" in EXTRACT_INSIGHTS.required_vars
        assert "period" in EXTRACT_INSIGHTS.required_vars

        result = EXTRACT_INSIGHTS.format(
            analysis_data="Data here",
            subreddit="r/python",
            period="last week",
        )
        assert "Data here" in result
        assert "r/python" in result

    def test_sentiment_analysis_template(self) -> None:
        """SENTIMENT_ANALYSIS 템플릿이 올바르게 동작한다."""
        assert SENTIMENT_ANALYSIS.category == PromptCategory.SENTIMENT
        assert "text" in SENTIMENT_ANALYSIS.required_vars

        result = SENTIMENT_ANALYSIS.format(text="I love this product!")
        assert "I love this product!" in result
        assert "sentiment" in result.lower()

    def test_trend_interpretation_template(self) -> None:
        """TREND_INTERPRETATION 템플릿이 올바르게 동작한다."""
        assert TREND_INTERPRETATION.category == PromptCategory.TREND

        required = TREND_INTERPRETATION.required_vars
        assert "trend_data" in required
        assert "rising_keywords" in required
        assert "declining_keywords" in required
        assert "target" in required
        assert "comparison_period" in required


class TestTemplateRegistry:
    """템플릿 레지스트리 테스트."""

    def test_get_template_success(self) -> None:
        """이름으로 템플릿을 조회할 수 있다."""
        template = get_template("summarize_posts")
        assert template == SUMMARIZE_POSTS

    def test_get_template_not_found(self) -> None:
        """존재하지 않는 템플릿은 KeyError를 발생시킨다."""
        with pytest.raises(KeyError, match="템플릿"):
            get_template("nonexistent_template")

    def test_list_templates(self) -> None:
        """모든 템플릿 목록을 조회할 수 있다."""
        templates = list_templates()
        assert len(templates) >= 5

        # 각 템플릿에 필수 필드가 있는지 확인
        for t in templates:
            assert "name" in t
            assert "category" in t
            assert "version" in t
            assert "description" in t
            assert "required_vars" in t

    def test_register_template(self) -> None:
        """새 템플릿을 등록할 수 있다."""
        custom_template = PromptTemplate(
            template="Custom: {input}",
            version="1.0",
            description="Test custom template",
        )

        register_template("test_custom", custom_template)

        # 등록된 템플릿을 조회
        retrieved = get_template("test_custom")
        assert retrieved == custom_template

        # 정리
        del TEMPLATES["test_custom"]

    def test_all_templates_have_descriptions(self) -> None:
        """모든 기본 템플릿이 설명을 갖고 있다."""
        for name, template in TEMPLATES.items():
            assert template.description, f"템플릿 '{name}'에 설명이 없습니다"

    def test_all_templates_have_versions(self) -> None:
        """모든 기본 템플릿이 버전을 갖고 있다."""
        for name, template in TEMPLATES.items():
            assert template.version, f"템플릿 '{name}'에 버전이 없습니다"


class TestPromptCategory:
    """PromptCategory enum 테스트."""

    def test_category_values(self) -> None:
        """모든 카테고리가 올바른 값을 갖는다."""
        assert PromptCategory.SUMMARIZATION.value == "summarization"
        assert PromptCategory.CATEGORIZATION.value == "categorization"
        assert PromptCategory.EXTRACTION.value == "extraction"
        assert PromptCategory.SENTIMENT.value == "sentiment"
        assert PromptCategory.TREND.value == "trend"
        assert PromptCategory.GENERAL.value == "general"

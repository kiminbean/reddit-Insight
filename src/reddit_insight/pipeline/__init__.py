"""데이터 파이프라인 모듈.

Reddit 데이터 수집, 전처리, 저장을 위한 파이프라인을 제공한다.
"""

from reddit_insight.pipeline.preprocessor import TextPreprocessor

__all__ = ["TextPreprocessor"]

"""로깅 시스템 모듈.

rich 라이브러리를 활용한 구조화된 로깅 시스템.
터미널 환경에서는 컬러풀한 출력, 그 외에는 기본 포맷 사용.
"""

import logging
import sys
from typing import Literal

from rich.console import Console
from rich.logging import RichHandler

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# 전역 console 인스턴스 (터미널 감지용)
_console = Console()


def setup_logging(
    level: LogLevel = "INFO",
    *,
    force_rich: bool = False,
) -> None:
    """로깅 시스템을 초기화한다.

    터미널 환경에서는 RichHandler를 사용하여 컬러풀한 출력을 제공하고,
    비터미널 환경(파이프, 파일 리다이렉트 등)에서는 기본 StreamHandler를 사용한다.

    Args:
        level: 로그 레벨 (기본값: INFO)
        force_rich: 비터미널 환경에서도 RichHandler 강제 사용 (테스트용)

    Example:
        >>> setup_logging("DEBUG")
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    # 기존 핸들러 제거
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # 로그 레벨 설정
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # 터미널 여부 확인
    is_terminal = _console.is_terminal or force_rich

    if is_terminal:
        # 터미널: RichHandler 사용
        handler = RichHandler(
            console=_console,
            show_time=level == "DEBUG",  # DEBUG 레벨에서만 시간 표시
            show_path=level == "DEBUG",  # DEBUG 레벨에서만 파일 경로 표시
            rich_tracebacks=True,
            tracebacks_show_locals=level == "DEBUG",
            markup=True,
        )
        handler.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
    else:
        # 비터미널: 기본 StreamHandler 사용
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

    handler.setLevel(numeric_level)
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """명명된 로거를 반환한다.

    모듈별로 독립적인 로거를 생성하여 로그 출처를 쉽게 식별할 수 있게 한다.

    Args:
        name: 로거 이름 (일반적으로 __name__ 사용)

    Returns:
        logging.Logger: 명명된 로거 인스턴스

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing started")
        >>> logger.debug("Detailed debug info")
    """
    return logging.getLogger(name)

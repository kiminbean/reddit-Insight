"""인증 및 권한 관리 모듈.

API Key 기반 인증과 세션 관리를 제공한다.
"""

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from reddit_insight.dashboard.database import APIKey, SessionLocal, init_db

# API Key 헤더 스키마
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def generate_api_key() -> str:
    """새로운 API 키를 생성한다.

    Returns:
        32바이트 hex 문자열 (64자)
    """
    return secrets.token_hex(32)


def hash_api_key(key: str) -> str:
    """API 키를 해시한다.

    Args:
        key: 원본 API 키

    Returns:
        SHA-256 해시값
    """
    return hashlib.sha256(key.encode()).hexdigest()


def create_api_key(name: str, rate_limit: int = 100) -> tuple[str, int]:
    """새로운 API 키를 생성하고 저장한다.

    Args:
        name: API 키 이름/설명
        rate_limit: 분당 요청 제한

    Returns:
        (원본 API 키, 데이터베이스 ID) 튜플
    """
    init_db()

    raw_key = generate_api_key()
    hashed_key = hash_api_key(raw_key)

    db = SessionLocal()
    try:
        api_key = APIKey(
            key=hashed_key,
            name=name,
            rate_limit=rate_limit,
            is_active=True,
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        return raw_key, api_key.id
    finally:
        db.close()


def validate_api_key(key: str) -> APIKey | None:
    """API 키를 검증한다.

    Args:
        key: 검증할 API 키

    Returns:
        유효한 경우 APIKey 객체, 아니면 None
    """
    if not key:
        return None

    hashed_key = hash_api_key(key)

    db = SessionLocal()
    try:
        api_key = (
            db.query(APIKey)
            .filter(APIKey.key == hashed_key, APIKey.is_active == True)
            .first()
        )

        if api_key:
            # 마지막 사용 시간 업데이트
            api_key.last_used_at = datetime.now(UTC)
            db.commit()
            db.refresh(api_key)

        return api_key
    finally:
        db.close()


def get_api_keys() -> list[dict]:
    """모든 API 키 목록을 반환한다."""
    init_db()

    db = SessionLocal()
    try:
        keys = db.query(APIKey).order_by(APIKey.created_at.desc()).all()
        return [
            {
                "id": k.id,
                "name": k.name,
                "created_at": k.created_at.isoformat() if k.created_at else None,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "is_active": bool(k.is_active),
                "rate_limit": k.rate_limit,
            }
            for k in keys
        ]
    finally:
        db.close()


def deactivate_api_key(key_id: int) -> bool:
    """API 키를 비활성화한다.

    Args:
        key_id: API 키 ID

    Returns:
        성공 여부
    """
    db = SessionLocal()
    try:
        api_key = db.query(APIKey).filter(APIKey.id == key_id).first()
        if api_key:
            api_key.is_active = False
            db.commit()
            return True
        return False
    finally:
        db.close()


def delete_api_key(key_id: int) -> bool:
    """API 키를 삭제한다.

    Args:
        key_id: API 키 ID

    Returns:
        성공 여부
    """
    db = SessionLocal()
    try:
        api_key = db.query(APIKey).filter(APIKey.id == key_id).first()
        if api_key:
            db.delete(api_key)
            db.commit()
            return True
        return False
    finally:
        db.close()


# ============================================================================
# FastAPI 의존성
# ============================================================================


async def get_api_key_optional(
    api_key: Annotated[str | None, Depends(api_key_header)] = None,
) -> APIKey | None:
    """선택적 API 키 검증 (인증 없이도 접근 가능)."""
    if api_key:
        return validate_api_key(api_key)
    return None


async def get_api_key_required(
    api_key: Annotated[str | None, Depends(api_key_header)] = None,
) -> APIKey:
    """필수 API 키 검증 (인증 필요)."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    validated_key = validate_api_key(api_key)
    if not validated_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or inactive API key",
        )

    return validated_key


# 환경 변수로 인증 필수 여부 설정
import os

AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "false").lower() == "true"


async def get_current_auth(
    request: Request,
    api_key: Annotated[str | None, Depends(api_key_header)] = None,
) -> APIKey | None:
    """현재 인증 상태를 반환한다.

    AUTH_REQUIRED=true면 인증 필수, 아니면 선택적.
    """
    if AUTH_REQUIRED:
        return await get_api_key_required(api_key)
    return await get_api_key_optional(api_key)


# ============================================================================
# CLI 유틸리티
# ============================================================================


def cli_create_api_key(name: str, rate_limit: int = 100) -> None:
    """CLI에서 API 키를 생성한다."""
    raw_key, key_id = create_api_key(name, rate_limit)
    print(f"\n=== API Key Created ===")
    print(f"ID: {key_id}")
    print(f"Name: {name}")
    print(f"Rate Limit: {rate_limit} requests/min")
    print(f"\nAPI Key (save this, it won't be shown again):")
    print(f"{raw_key}")
    print(f"\nUse this key in the X-API-Key header")


def cli_list_api_keys() -> None:
    """CLI에서 API 키 목록을 출력한다."""
    keys = get_api_keys()
    if not keys:
        print("No API keys found.")
        return

    print("\n=== API Keys ===")
    print(f"{'ID':<5} {'Name':<20} {'Active':<8} {'Rate Limit':<12} {'Last Used':<20}")
    print("-" * 70)
    for k in keys:
        last_used = k["last_used_at"][:19] if k["last_used_at"] else "Never"
        print(
            f"{k['id']:<5} {k['name'][:20]:<20} {'Yes' if k['is_active'] else 'No':<8} "
            f"{k['rate_limit']:<12} {last_used:<20}"
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m reddit_insight.dashboard.auth create <name> [rate_limit]")
        print("  python -m reddit_insight.dashboard.auth list")
        print("  python -m reddit_insight.dashboard.auth delete <id>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        if len(sys.argv) < 3:
            print("Error: Name required")
            sys.exit(1)
        name = sys.argv[2]
        rate_limit = int(sys.argv[3]) if len(sys.argv) > 3 else 100
        cli_create_api_key(name, rate_limit)

    elif command == "list":
        cli_list_api_keys()

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Error: ID required")
            sys.exit(1)
        key_id = int(sys.argv[2])
        if delete_api_key(key_id):
            print(f"API key {key_id} deleted.")
        else:
            print(f"API key {key_id} not found.")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

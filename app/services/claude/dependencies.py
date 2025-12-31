"""Claude 서비스 의존성 주입"""

from app.services.claude.protocol import AIServiceProtocol
from app.services.claude.service import ClaudeService

_claude_service: ClaudeService | None = None


def _get_singleton() -> ClaudeService:
    """싱글톤 인스턴스 반환 (내부용)"""
    global _claude_service
    if _claude_service is None:
        _claude_service = ClaudeService()
    return _claude_service


async def get_claude_service() -> AIServiceProtocol:
    """
    Claude 서비스 의존성 주입 포인트

    테스트에서 override 가능:
        app.dependency_overrides[get_claude_service] = lambda: FakeClaudeService()
    """
    return _get_singleton()

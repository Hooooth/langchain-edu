from opensearchpy import OpenSearch
from app.core.config import settings

_client: OpenSearch | None = None


def get_opensearch_client() -> OpenSearch:
    """OpenSearch 클라이언트 싱글턴을 반환합니다."""
    global _client
    if _client is None:
        _client = OpenSearch(
            hosts=[settings.OPENSEARCH_HOST],
            http_auth=(settings.OPENSEARCH_USERNAME, settings.OPENSEARCH_PASSWORD),
            verify_certs=settings.OPENSEARCH_VERIFY_CERTS,
            ssl_show_warn=False,
        )
    return _client

"""Tests de la política de reintentos del scheduler (transitorio/permanente, backoff).

`_handle_publish_result` decide publicado/reprogramar/fallar según el `PublishResult`
que devuelve el publisher activo (hoy `ZernioPublisher`). Lógica agnóstica del
proveedor, sin DB. (La publicación en sí se prueba en test_zernio_publisher.py.)
"""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.services.marketing.publisher_base import PublishResult
from app.workers import tasks_scheduler


class TestHandlePublishResult:
    def _post(self, retry_count=0):
        return SimpleNamespace(
            retry_count=retry_count, status="scheduled",
            scheduled_at=None, error_message="boom",
        )

    def test_published(self):
        post = self._post()
        assert tasks_scheduler._handle_publish_result(
            post, PublishResult(True, False), datetime.now(UTC)
        ) == "published"

    def test_transient_reschedules_with_backoff(self):
        now = datetime.now(UTC)
        post = self._post(retry_count=0)
        outcome = tasks_scheduler._handle_publish_result(post, PublishResult(False, True), now)
        assert outcome == "retried"
        assert post.retry_count == 1
        assert post.status == "scheduled"
        assert post.scheduled_at == now + timedelta(minutes=5)

    def test_backoff_doubles(self):
        now = datetime.now(UTC)
        post = self._post(retry_count=2)
        tasks_scheduler._handle_publish_result(post, PublishResult(False, True), now)
        # retry_count 2 → 3, delay = 5 * 2^(3-1) = 20 min
        assert post.retry_count == 3
        assert post.scheduled_at == now + timedelta(minutes=20)

    def test_retries_exhausted_fails(self):
        post = self._post(retry_count=tasks_scheduler._MAX_PUBLISH_RETRIES)
        outcome = tasks_scheduler._handle_publish_result(
            post, PublishResult(False, True), datetime.now(UTC)
        )
        assert outcome == "failed"

    def test_permanent_fails_without_retry(self):
        post = self._post(retry_count=0)
        outcome = tasks_scheduler._handle_publish_result(
            post, PublishResult(False, False), datetime.now(UTC)
        )
        assert outcome == "failed"
        assert post.retry_count == 0

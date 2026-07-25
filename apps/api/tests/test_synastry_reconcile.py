"""Unit tests for synastry_reconcile job."""

from unittest.mock import AsyncMock, patch
import uuid
import pytest

from app.db.models import SynastryReport
from app.jobs.synastry_reconcile import main, reconcile_stale_reports


@pytest.mark.asyncio
async def test_reconcile_stale_reports_calls_pipeline():
    db = AsyncMock()
    rep_id_1 = uuid.uuid4()
    rep_id_2 = uuid.uuid4()

    db.execute.return_value = AsyncMock(scalars=lambda: AsyncMock(all=lambda: [rep_id_1, rep_id_2]))

    mock_report_1 = SynastryReport(id=rep_id_1, state="ready")
    mock_report_2 = SynastryReport(id=rep_id_2, state="failed", error_code="LLM_FAILED")

    with patch("app.jobs.synastry_reconcile.SynastryService") as mock_service_cls:
        mock_service = AsyncMock()
        mock_service.run_report_pipeline.side_effect = [mock_report_1, mock_report_2]
        mock_service_cls.return_value = mock_service

        count = await reconcile_stale_reports(db, limit=20, cutoff_minutes=5)

        assert count == 2
        assert mock_service.run_report_pipeline.call_count == 2


@pytest.mark.asyncio
async def test_reconcile_stale_reports_empty_batch():
    db = AsyncMock()
    db.execute.return_value = AsyncMock(scalars=lambda: AsyncMock(all=lambda: []))

    count = await reconcile_stale_reports(db, limit=20, cutoff_minutes=5)
    assert count == 0


@pytest.mark.asyncio
async def test_reconcile_stale_reports_swallows_individual_error():
    db = AsyncMock()
    rep_id_1 = uuid.uuid4()
    rep_id_2 = uuid.uuid4()

    db.execute.return_value = AsyncMock(scalars=lambda: AsyncMock(all=lambda: [rep_id_1, rep_id_2]))

    mock_report_2 = SynastryReport(id=rep_id_2, state="ready")

    with patch("app.jobs.synastry_reconcile.SynastryService") as mock_service_cls:
        mock_service = AsyncMock()
        mock_service.run_report_pipeline.side_effect = [RuntimeError("Pipeline crash"), mock_report_2]
        mock_service_cls.return_value = mock_service

        count = await reconcile_stale_reports(db, limit=20, cutoff_minutes=5)

        assert count == 1
        assert mock_service.run_report_pipeline.call_count == 2


def test_main_entrypoint_returns_zero():
    with patch("app.jobs.synastry_reconcile._run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = 0
        res = main()
        assert res == 0

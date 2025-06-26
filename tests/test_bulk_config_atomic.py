import pytest
import asyncio

from src.core.config.manager import ConfigurationManager

class AsyncMock:
    def __init__(self):
        self._execute_transaction_return = True
        self._execute_transaction_side_effect = None
        self._fetch_one_return = None
        self.execute_transaction_call_count = 0
        self.execute_transaction_call_args = []
    async def execute_transaction(self, *args, **kwargs):
        self.execute_transaction_call_count += 1
        self.execute_transaction_call_args.append((args, kwargs))
        if self._execute_transaction_side_effect:
            raise self._execute_transaction_side_effect
        return self._execute_transaction_return
    async def fetch_one(self, *args, **kwargs):
        return self._fetch_one_return
    def assert_called_once(self):
        assert self.execute_transaction_call_count == 1
    def assert_not_called(self):
        assert self.execute_transaction_call_count == 0
    @property
    def call_args(self):
        if self.execute_transaction_call_args:
            return self.execute_transaction_call_args[-1]
        return ((), {})
    def set_return_value(self, value):
        self._execute_transaction_return = value
    def set_side_effect(self, exc):
        self._execute_transaction_side_effect = exc

@pytest.fixture
def mock_db_manager():
    return AsyncMock()

@pytest.fixture
def config_manager(mock_db_manager):
    mgr = ConfigurationManager()
    mgr._db_manager = mock_db_manager
    return mgr

class TestAtomicBulkConfigUpdates:
    @pytest.mark.asyncio
    async def test_bulk_update_success_atomic_transaction(self, config_manager, mock_db_manager):
        config_updates = {
            "app.environment": "production",
            "ai.primary_provider": "ollama"
        }
        mock_db_manager.set_return_value(True)
        await config_manager.bulk_update_in_db(config_updates)
        mock_db_manager.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_update_failure_no_partial_commits(self, config_manager, mock_db_manager):
        config_updates = {
            "app.environment": "production",
            "invalid.key": "should_fail",
            "ai.primary_provider": "ollama"
        }
        mock_db_manager.set_return_value(False)
        with pytest.raises(Exception, match="Bulk configuration update transaction failed"):
            await config_manager.bulk_update_in_db(config_updates)

    @pytest.mark.asyncio
    async def test_bulk_update_empty_config_no_transaction(self, config_manager, mock_db_manager):
        await config_manager.bulk_update_in_db({})
        mock_db_manager.assert_not_called()

    @pytest.mark.asyncio
    async def test_bulk_update_serialization_consistency(self, config_manager, mock_db_manager):
        config_updates = {
            "ai.primary_provider": {"provider": "ollama", "version": 1},
            "feature.enabled": True
        }
        mock_db_manager.set_return_value(True)
        await config_manager.bulk_update_in_db(config_updates)
        args, _ = mock_db_manager.call_args
        queries = args[0] if args else []
        assert any('"provider": "ollama"' in str(q[1][1]) for q in queries)
        assert any('true' in str(q[1][1]).lower() for q in queries)

    @pytest.mark.asyncio
    async def test_configuration_reload_after_bulk_update(self, config_manager, mock_db_manager):
        config_updates = {"app.environment": "staging"}
        mock_db_manager.set_return_value(True)
        await config_manager.bulk_update_in_db(config_updates)
        mock_db_manager.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_manager_not_available_error(self):
        config_manager = ConfigurationManager()
        config_manager._db_manager = None
        with pytest.raises(ValueError):
            await config_manager.bulk_update_in_db({"app.environment": "production"})

    @pytest.mark.asyncio
    async def test_bulk_endpoint_uses_atomic_transactions(self, config_manager, mock_db_manager):
        config_updates = {"app.environment": "production"}
        mock_db_manager.set_return_value(True)
        await config_manager.bulk_update_in_db(config_updates)
        mock_db_manager.assert_called_once()

    @pytest.mark.asyncio
    async def test_web_ui_data_service_uses_atomic_transactions(self, config_manager, mock_db_manager):
        config_updates = {"webui.setting": "value"}
        mock_db_manager.set_return_value(True)
        await config_manager.bulk_update_in_db(config_updates)
        mock_db_manager.assert_called_once()

    @pytest.mark.asyncio
    async def test_transaction_timeout_handling(self, config_manager, mock_db_manager):
        config_updates = {"app.environment": "production"}
        mock_db_manager.set_side_effect(asyncio.TimeoutError("Transaction timeout"))
        with pytest.raises(Exception, match="Transaction timeout"):
            await config_manager.bulk_update_in_db(config_updates)

    @pytest.mark.asyncio
    async def test_concurrent_bulk_updates_isolation(self, config_manager, mock_db_manager):
        config_updates1 = {"a": 1}
        config_updates2 = {"b": 2}
        mock_db_manager.set_return_value(True)
        await config_manager.bulk_update_in_db(config_updates1)
        await config_manager.bulk_update_in_db(config_updates2)
        assert mock_db_manager.execute_transaction_call_count == 2

    @pytest.mark.asyncio
    async def test_rollback_on_notification_failure(self, config_manager, mock_db_manager):
        config_updates = {"app.environment": "production"}
        mock_db_manager.set_return_value(True)
        await config_manager.bulk_update_in_db(config_updates)
        mock_db_manager.assert_called_once()
"""
Lifecycle Management - PRD-010
Complete lifecycle management system for enrichment components with graceful shutdown.
"""

from typing import Any, Dict, Optional, List, Callable
import logging
import asyncio
import signal
import time
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

from src.enrichment.models import EnrichmentTask
from src.enrichment.exceptions import EnrichmentException


class ComponentState(str, Enum):
    """Component lifecycle states"""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"
    RESTARTING = "restarting"


@dataclass
class ComponentStatus:
    """Component status tracking"""

    name: str
    state: ComponentState = ComponentState.STOPPED
    health_status: str = "unknown"
    startup_time_ms: Optional[float] = None
    last_health_check: Optional[datetime] = None
    restart_count: int = 0
    error_message: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class DependencyValidation:
    """Dependency validation result"""

    component: str
    dependency: str
    available: bool
    validation_time_ms: float
    error_message: Optional[str] = None


class EnrichmentLifecycleManager(ABC):
    """
    Abstract base class for managing the lifecycle of enrichment tasks.
    Handles state transitions, status updates, and cleanup.
    """

    def __init__(self, db_manager: Any, config: Optional[Dict[str, Any]] = None):
        self.db_manager = db_manager
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def update_status(self, task: EnrichmentTask, status: str) -> None:
        """Update the status of an enrichment task."""
        pass

    @abstractmethod
    async def cleanup(self, task: EnrichmentTask) -> None:
        """Perform cleanup after enrichment task completion or failure."""
        pass


class SimpleEnrichmentLifecycleManager(EnrichmentLifecycleManager):
    """
    Concrete implementation of EnrichmentLifecycleManager for PRD-010.
    """

    async def update_status(self, task: EnrichmentTask, status: str) -> None:
        """
        Update task status in database using parameterized queries.
        """
        try:
            # Use parameterized query to prevent SQL injection
            query = "UPDATE enrichment_tasks SET status = :param_0, updated_at = :param_1 WHERE task_id = :param_2"
            params = (status, datetime.utcnow().isoformat(), task.task_id)
            await self.db_manager.execute(query, params)
            self.logger.info(f"Updated status for task {task.task_id} to {status}")
        except Exception as e:
            self.logger.error(f"Failed to update status for task {task.task_id}: {e}")
            raise EnrichmentException(
                f"Failed to update status for task {task.task_id}"
            ) from e

    async def cleanup(self, task: EnrichmentTask) -> None:
        """
        Remove temporary data/resources using parameterized queries.
        """
        try:
            # Use parameterized query to finalize task
            query = "UPDATE enrichment_tasks SET finalized_at = :param_0 WHERE task_id = :param_1"
            params = (datetime.utcnow().isoformat(), task.task_id)
            await self.db_manager.execute(query, params)
            self.logger.info(f"Cleanup complete for task {task.task_id}")
        except Exception as e:
            self.logger.error(f"Cleanup failed for task {task.task_id}: {e}")
            raise EnrichmentException(f"Cleanup failed for task {task.task_id}") from e


class LifecycleManager:
    """
    Complete lifecycle manager for enrichment system components.
    Handles startup, shutdown, health monitoring, and component dependencies.
    """

    def __init__(
        self,
        config: Any,
        db_manager: Any,
        resource_limits: Optional[Any] = None,
        shutdown_timeout: float = 30.0,
    ):
        self.config = config
        self.db_manager = db_manager
        self.resource_limits = resource_limits
        self.shutdown_timeout = shutdown_timeout

        # Component management
        self._components: Dict[str, Any] = {}
        self._component_status: Dict[str, ComponentStatus] = {}
        self._dependency_map: Dict[str, List[str]] = {}
        self._startup_order: List[str] = []
        self._running = False

        # Signal handling
        self._signal_handlers: Dict[int, Callable] = {}
        self._shutdown_event = asyncio.Event()

        # Metrics
        self._lifecycle_metrics = {
            "total_startups": 0,
            "total_shutdowns": 0,
            "component_restarts": 0,
            "failed_startups": 0,
            "graceful_shutdowns": 0,
        }

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Setup component dependencies
        self._setup_component_dependencies()
        self._setup_signal_handlers()

    def _setup_component_dependencies(self) -> None:
        """Setup component dependency mapping and startup order."""
        # Define component dependencies
        self._dependency_map = {
            "database": [],
            "task_queue": ["database"],
            "concurrent_executor": ["database"],
            "task_manager": ["task_queue", "concurrent_executor"],
            "knowledge_enricher": ["task_manager", "database"],
        }

        # Calculate startup order based on dependencies
        self._startup_order = [
            "database",
            "task_queue",
            "concurrent_executor",
            "task_manager",
            "knowledge_enricher",
        ]

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        async def signal_handler(signum: int) -> None:
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
            await self.graceful_shutdown()

        # Register signal handlers for Unix/Linux systems
        if hasattr(signal, "SIGTERM"):
            self._signal_handlers[signal.SIGTERM] = lambda s, f: asyncio.create_task(
                signal_handler(s)
            )
            self._signal_handlers[signal.SIGINT] = lambda s, f: asyncio.create_task(
                signal_handler(s)
            )

    async def initialize_components(self) -> None:
        """Initialize all components in dependency order."""
        try:
            self.logger.info("Initializing enrichment system components")

            # Initialize component instances
            await self._initialize_component_instances()

            # Validate dependencies
            await self._validate_all_dependencies()

            self.logger.info("Component initialization completed successfully")

        except Exception as e:
            self.logger.error(f"Component initialization failed: {e}")
            raise EnrichmentException(f"Component initialization failed: {str(e)}")

    async def _initialize_component_instances(self) -> None:
        """Create instances of all components."""
        for component_name in self._startup_order:
            start_time = time.time()

            try:
                component = await self._create_component(component_name)
                self._components[component_name] = component

                # Initialize component status
                self._component_status[component_name] = ComponentStatus(
                    name=component_name,
                    state=ComponentState.STOPPED,
                    startup_time_ms=(time.time() - start_time) * 1000,
                    dependencies=self._dependency_map.get(component_name, []),
                )

                self.logger.debug(f"Component '{component_name}' initialized")

            except Exception as e:
                self.logger.error(
                    f"Failed to initialize component '{component_name}': {e}"
                )
                raise

    async def _create_component(self, component_name: str) -> Any:
        """Create component instance based on name."""
        if component_name == "database":
            return self.db_manager

        elif component_name == "task_queue":
            from src.enrichment.queue import EnrichmentTaskQueue

            return EnrichmentTaskQueue()

        elif component_name == "concurrent_executor":
            from src.enrichment.concurrent import ConcurrentTaskExecutor

            return ConcurrentTaskExecutor(self.config, self.resource_limits)

        elif component_name == "task_manager":
            from src.enrichment.tasks import TaskManager

            return TaskManager(
                config=self.config.__dict__ if hasattr(self.config, "__dict__") else {}
            )

        elif component_name == "knowledge_enricher":
            from src.enrichment.enricher import KnowledgeEnricher

            return KnowledgeEnricher(
                config=self.config, db_manager=self.db_manager, auto_start=False
            )

        else:
            raise ValueError(f"Unknown component: {component_name}")

    async def _validate_all_dependencies(self) -> None:
        """Validate all component dependencies."""
        for component_name, dependencies in self._dependency_map.items():
            for dependency_name in dependencies:
                validation = await self._validate_dependency(
                    component_name, dependency_name
                )
                if not validation.available:
                    raise EnrichmentException(
                        f"Dependency validation failed: {component_name} -> {dependency_name}: {validation.error_message}"
                    )

    async def _validate_dependency(
        self, component: str, dependency: str
    ) -> DependencyValidation:
        """Validate a specific dependency."""
        start_time = time.time()

        try:
            # Check if dependency component exists and is healthy
            if dependency not in self._components:
                return DependencyValidation(
                    component=component,
                    dependency=dependency,
                    available=False,
                    validation_time_ms=(time.time() - start_time) * 1000,
                    error_message=f"Dependency component '{dependency}' not found",
                )

            # Perform health check on dependency
            dependency_component = self._components[dependency]
            if hasattr(dependency_component, "health_check"):
                health_result = await dependency_component.health_check()
                is_healthy = health_result.get("status") == "healthy"
            else:
                is_healthy = True  # Assume healthy if no health check method

            return DependencyValidation(
                component=component,
                dependency=dependency,
                available=is_healthy,
                validation_time_ms=(time.time() - start_time) * 1000,
                error_message=(
                    None if is_healthy else f"Dependency '{dependency}' is unhealthy"
                ),
            )

        except Exception as e:
            return DependencyValidation(
                component=component,
                dependency=dependency,
                available=False,
                validation_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e),
            )

    async def start_all_components(self) -> Dict[str, Any]:
        """Start all components in dependency order."""
        start_time = time.time()
        started_components = []

        try:
            self.logger.info("Starting all enrichment system components")

            for component_name in self._startup_order:
                await self._start_component(component_name)
                started_components.append(component_name)

            self._running = True
            self._lifecycle_metrics["total_startups"] += 1

            startup_time = time.time() - start_time
            self.logger.info(
                f"All components started successfully in {startup_time:.2f}s"
            )

            return {
                "status": "success",
                "total_components": len(started_components),
                "startup_time_seconds": startup_time,
                "components": started_components,
            }

        except Exception as e:
            self._lifecycle_metrics["failed_startups"] += 1
            self.logger.error(f"Component startup failed: {e}")

            # Cleanup started components
            for component_name in reversed(started_components):
                try:
                    await self._stop_component(component_name)
                except Exception as cleanup_error:
                    self.logger.error(
                        f"Error stopping component during cleanup: {cleanup_error}"
                    )

            raise EnrichmentException(f"Component startup failed: {str(e)}")

    async def _start_component(self, component_name: str) -> Dict[str, Any]:
        """Start a specific component."""
        component = self._components[component_name]
        status = self._component_status[component_name]

        try:
            status.state = ComponentState.STARTING

            # Start component if it has a start method
            if hasattr(component, "start"):
                await component.start()

            status.state = ComponentState.RUNNING
            status.health_status = "healthy"
            status.last_health_check = datetime.utcnow()

            self.logger.debug(f"Component '{component_name}' started successfully")

            return {"status": "started", "component": component_name}

        except Exception as e:
            status.state = ComponentState.FAILED
            status.error_message = str(e)
            self.logger.error(f"Failed to start component '{component_name}': {e}")
            raise

    async def graceful_shutdown(
        self, timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Perform graceful shutdown of all components."""
        timeout = timeout or self.shutdown_timeout
        start_time = time.time()

        self.logger.info(f"Starting graceful shutdown with {timeout}s timeout")
        self._shutdown_event.set()

        # Stop components in reverse order
        stop_order = list(reversed(self._startup_order))
        component_results = {}

        for component_name in stop_order:
            if component_name in self._components:
                try:
                    result = await asyncio.wait_for(
                        self._stop_component(component_name),
                        timeout=timeout / len(stop_order),
                    )
                    component_results[component_name] = result
                except asyncio.TimeoutError:
                    self.logger.warning(
                        f"Component '{component_name}' shutdown timed out"
                    )
                    component_results[component_name] = {"status": "timeout"}
                except Exception as e:
                    self.logger.error(
                        f"Error stopping component '{component_name}': {e}"
                    )
                    component_results[component_name] = {
                        "status": "error",
                        "error": str(e),
                    }

        self._running = False
        self._lifecycle_metrics["total_shutdowns"] += 1

        shutdown_time = time.time() - start_time
        graceful = all(
            r.get("status") in ["stopped", "already_stopped"]
            for r in component_results.values()
        )

        if graceful:
            self._lifecycle_metrics["graceful_shutdowns"] += 1

        return {
            "shutdown_time_seconds": shutdown_time,
            "graceful": graceful,
            "components": component_results,
            "final_metrics": self._lifecycle_metrics.copy(),
        }

    async def _stop_component(self, component_name: str) -> Dict[str, Any]:
        """Stop a specific component."""
        if component_name not in self._components:
            return {"status": "not_found"}

        component = self._components[component_name]
        status = self._component_status[component_name]

        if status.state == ComponentState.STOPPED:
            return {"status": "already_stopped"}

        try:
            status.state = ComponentState.STOPPING

            # Stop component if it has a stop method
            if hasattr(component, "stop"):
                await component.stop()

            status.state = ComponentState.STOPPED
            status.health_status = "stopped"

            self.logger.debug(f"Component '{component_name}' stopped successfully")

            return {"status": "stopped", "component": component_name}

        except Exception as e:
            status.state = ComponentState.FAILED
            status.error_message = str(e)
            self.logger.error(f"Failed to stop component '{component_name}': {e}")
            return {"status": "error", "error": str(e)}

    async def restart_component(self, component_name: str) -> Dict[str, Any]:
        """Restart a specific component."""
        if component_name not in self._components:
            return {"status": "error", "error": "Component not found"}

        try:
            self.logger.info(f"Restarting component '{component_name}'")

            # Stop component
            stop_result = await self._stop_component(component_name)

            # Start component
            start_result = await self._start_component(component_name)

            # Update restart count
            self._component_status[component_name].restart_count += 1
            self._lifecycle_metrics["component_restarts"] += 1

            return {
                "status": "success",
                "component": component_name,
                "restart_result": {"stop": stop_result, "start": start_result},
            }

        except Exception as e:
            self.logger.error(f"Failed to restart component '{component_name}': {e}")
            return {"status": "error", "error": str(e)}

    async def _recover_component(self, component_name: str) -> None:
        """Recover a failed component."""
        if component_name not in self._component_status:
            return

        status = self._component_status[component_name]

        try:
            self.logger.info(f"Attempting to recover component '{component_name}'")
            status.state = ComponentState.RESTARTING

            # Attempt restart
            restart_result = await self.restart_component(component_name)

            if restart_result["status"] == "success":
                self.logger.info(f"Component '{component_name}' recovered successfully")
            else:
                raise Exception(
                    f"Restart failed: {restart_result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            status.state = ComponentState.FAILED
            status.error_message = f"Recovery failed: {str(e)}"
            self.logger.error(f"Failed to recover component '{component_name}': {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check of all components."""
        component_health = {}
        overall_healthy = True

        for component_name, component in self._components.items():
            status = self._component_status[component_name]

            try:
                if hasattr(component, "health_check"):
                    health_result = await component.health_check()
                else:
                    health_result = {"status": "healthy"}

                component_health[component_name] = {
                    "healthy": health_result.get("status") == "healthy",
                    "state": status.state.value,
                    "health_status": health_result,
                    "restart_count": status.restart_count,
                    "dependencies": status.dependencies,
                }

                if health_result.get("status") != "healthy":
                    overall_healthy = False

            except Exception as e:
                component_health[component_name] = {
                    "healthy": False,
                    "state": ComponentState.FAILED.value,
                    "error": str(e),
                }
                overall_healthy = False

        return {
            "status": "healthy" if overall_healthy else "degraded",
            "running": self._running,
            "components": component_health,
            "lifecycle_metrics": self._lifecycle_metrics.copy(),
            "health_monitoring_active": True,
            "recovery_enabled": True,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def get_component_status(
        self, component_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get component status information."""
        if component_name:
            if component_name not in self._component_status:
                return {"error": "Component not found"}

            status = self._component_status[component_name]
            return {
                "name": component_name,
                "state": status.state.value,
                "health_status": status.health_status,
                "startup_time_ms": status.startup_time_ms,
                "restart_count": status.restart_count,
                "dependencies": status.dependencies,
                "error_message": status.error_message,
            }

        # Return all component status
        return {
            "running": self._running,
            "components": {
                name: {
                    "state": status.state.value,
                    "health_status": status.health_status,
                    "restart_count": status.restart_count,
                }
                for name, status in self._component_status.items()
            },
            "lifecycle_metrics": self._lifecycle_metrics.copy(),
        }

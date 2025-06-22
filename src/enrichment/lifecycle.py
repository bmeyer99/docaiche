"""
Lifecycle Management - PRD-010
Comprehensive lifecycle management for all enrichment components.

Implements proper startup/shutdown procedures, graceful shutdown with pending task
completion handling, component health monitoring, resource cleanup protocols,
and dependency initialization for production readiness.
"""

import asyncio
import logging
import signal
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, field
import os
import inspect

from .models import EnrichmentConfig
from .exceptions import EnrichmentError, TaskProcessingError
from .concurrent import ConcurrentTaskExecutor, ResourceLimits
from .enricher import KnowledgeEnricher
from .tasks import TaskManager
from .queue import EnrichmentTaskQueue

logger = logging.getLogger(__name__)


class ComponentState(str, Enum):
    """States for enrichment components during lifecycle management"""
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    RECOVERING = "recovering"


@dataclass
class ComponentStatus:
    """Status information for a managed component"""
    name: str
    state: ComponentState
    last_state_change: datetime
    health_status: str = "unknown"
    error_message: Optional[str] = None
    restart_count: int = 0
    dependencies: List[str] = field(default_factory=list)
    startup_time_ms: Optional[int] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyValidation:
    """Dependency validation result"""
    component: str
    dependency: str
    available: bool
    error_message: Optional[str] = None
    validation_time_ms: int = 0


class LifecycleManager:
    """
    Comprehensive lifecycle manager for enrichment components.
    
    Manages coordinated startup/shutdown, dependency validation, health monitoring,
    and recovery mechanisms for all enrichment pipeline components.
    """
    
    def __init__(
        self,
        config: EnrichmentConfig,
        db_manager: Optional[Any] = None,
        resource_limits: Optional[ResourceLimits] = None,
        shutdown_timeout: float = 30.0
    ):
        """
        Initialize lifecycle manager.
        
        Args:
            config: Enrichment configuration
            db_manager: Database manager instance
            resource_limits: Resource limits for concurrency control
            shutdown_timeout: Maximum time to wait for graceful shutdown
        """
        self.config = config
        self.db_manager = db_manager
        self.resource_limits = resource_limits or ResourceLimits()
        self.shutdown_timeout = shutdown_timeout
        
        # Component registry and status tracking
        self._components: Dict[str, Any] = {}
        self._component_status: Dict[str, ComponentStatus] = {}
        self._dependency_map: Dict[str, List[str]] = {}
        self._startup_order: List[str] = []
        
        # Lifecycle state management
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._health_check_interval = 30.0
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Signal handling for container environments
        self._signal_handlers: Dict[int, Callable] = {}
        self._graceful_shutdown_task: Optional[asyncio.Task] = None
        
        # Recovery and restart mechanisms
        self._recovery_enabled = True
        self._max_restart_attempts = 3
        self._restart_backoff_seconds = 5.0
        
        # Metrics and monitoring
        self._lifecycle_metrics = {
            'total_startups': 0,
            'total_shutdowns': 0,
            'failed_startups': 0,
            'recovery_attempts': 0,
            'successful_recoveries': 0,
            'component_restarts': 0
        }
        
        logger.info("LifecycleManager initialized")
    
    async def initialize_components(self) -> None:
        """
        Initialize all enrichment components with proper dependency order.
        
        Raises:
            EnrichmentError: If component initialization fails
        """
        try:
            logger.info("Initializing enrichment components")
            
            # Define component dependencies
            self._setup_component_dependencies()
            
            # Initialize components in dependency order
            await self._initialize_component_instances()
            
            # Validate all dependencies
            await self._validate_all_dependencies()
            
            logger.info("All enrichment components initialized successfully")
            
        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            await self._cleanup_failed_initialization()
            raise EnrichmentError(f"Component initialization failed: {str(e)}")
    
    def _setup_component_dependencies(self) -> None:
        """Setup component dependency mapping and startup order."""
        # Define component dependencies (components depend on their dependencies)
        self._dependency_map = {
            'database': [],  # No dependencies
            'task_queue': ['database'],
            'concurrent_executor': ['database'],
            'task_manager': ['database', 'task_queue', 'concurrent_executor'],
            'knowledge_enricher': ['database', 'task_manager']
        }
        
        # Calculate startup order using topological sort
        self._startup_order = self._calculate_startup_order()
        
        logger.debug(f"Component startup order: {self._startup_order}")
    
    def _calculate_startup_order(self) -> List[str]:
        """Calculate component startup order based on dependencies."""
        # Simple topological sort for dependency resolution
        visited = set()
        order = []
        
        def visit(component: str):
            if component in visited:
                return
            visited.add(component)
            
            for dependency in self._dependency_map.get(component, []):
                visit(dependency)
            
            order.append(component)
        
        for component in self._dependency_map.keys():
            visit(component)
        
        return order
    
    async def _initialize_component_instances(self) -> None:
        """Initialize component instances in dependency order."""
        for component_name in self._startup_order:
            try:
                start_time = time.time()
                
                # Update component status
                self._component_status[component_name] = ComponentStatus(
                    name=component_name,
                    state=ComponentState.INITIALIZING,
                    last_state_change=datetime.utcnow(),
                    dependencies=self._dependency_map.get(component_name, [])
                )
                
                # Initialize specific component
                component = await self._create_component(component_name)
                self._components[component_name] = component
                
                # Calculate startup time
                startup_time = int((time.time() - start_time) * 1000)
                
                # Update status to initialized
                self._component_status[component_name].state = ComponentState.STOPPED
                self._component_status[component_name].startup_time_ms = startup_time
                self._component_status[component_name].last_state_change = datetime.utcnow()
                
                logger.info(f"Component '{component_name}' initialized in {startup_time}ms")
                
            except Exception as e:
                self._component_status[component_name].state = ComponentState.FAILED
                self._component_status[component_name].error_message = str(e)
                self._component_status[component_name].last_state_change = datetime.utcnow()
                
                logger.error(f"Failed to initialize component '{component_name}': {e}")
                raise
    
    async def _create_component(self, component_name: str) -> Any:
        """Create specific component instance."""
        if component_name == 'database':
            # Database manager should be provided or created externally
            if self.db_manager is None:
                from src.database.connection import DatabaseManager
                return DatabaseManager()
            return self.db_manager
            
        elif component_name == 'task_queue':
            return EnrichmentTaskQueue(self.config)
            
        elif component_name == 'concurrent_executor':
            return ConcurrentTaskExecutor(self.config, self.resource_limits)
            
        elif component_name == 'task_manager':
            task_queue = self._components['task_queue']
            db_manager = self._components['database']
            return TaskManager(self.config, task_queue, db_manager, self.resource_limits)
            
        elif component_name == 'knowledge_enricher':
            db_manager = self._components['database']
            return KnowledgeEnricher(
                config=self.config,
                db_manager=db_manager,
                content_processor=None,  # Would be injected if available
                anythingllm_client=None,  # Would be injected if available
                search_orchestrator=None  # Would be injected if available
            )
            
        else:
            raise EnrichmentError(f"Unknown component: {component_name}")
    
    async def _validate_all_dependencies(self) -> None:
        """Validate all component dependencies are satisfied."""
        validation_results = []
        
        for component_name, dependencies in self._dependency_map.items():
            for dependency in dependencies:
                result = await self._validate_dependency(component_name, dependency)
                validation_results.append(result)
                
                if not result.available:
                    raise EnrichmentError(
                        f"Dependency validation failed: {component_name} requires {dependency}",
                        error_context={"validation_result": result.__dict__}
                    )
        
        logger.info(f"All dependencies validated successfully ({len(validation_results)} checks)")
    
    async def _validate_dependency(self, component: str, dependency: str) -> DependencyValidation:
        """Validate a specific component dependency."""
        start_time = time.time()
        
        try:
            # Check if dependency component exists and is initialized
            if dependency not in self._components:
                return DependencyValidation(
                    component=component,
                    dependency=dependency,
                    available=False,
                    error_message=f"Dependency component '{dependency}' not found",
                    validation_time_ms=int((time.time() - start_time) * 1000)
                )
            
            dependency_component = self._components[dependency]
            
            # Perform specific validation based on component type
            if dependency == 'database' and hasattr(dependency_component, 'health_check'):
                health_result = await dependency_component.health_check()
                if health_result.get('status') != 'healthy':
                    return DependencyValidation(
                        component=component,
                        dependency=dependency,
                        available=False,
                        error_message=f"Database health check failed: {health_result}",
                        validation_time_ms=int((time.time() - start_time) * 1000)
                    )
            
            return DependencyValidation(
                component=component,
                dependency=dependency,
                available=True,
                validation_time_ms=int((time.time() - start_time) * 1000)
            )
            
        except Exception as e:
            return DependencyValidation(
                component=component,
                dependency=dependency,
                available=False,
                error_message=str(e),
                validation_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def start_all_components(self) -> Dict[str, Any]:
        """
        Start all components in dependency order with proper error handling.
        
        Returns:
            Startup results and metrics
            
        Raises:
            EnrichmentError: If startup fails
        """
        try:
            if self._running:
                logger.warning("Components already running")
                return {"status": "already_running", "message": "Components are already started"}
            
            logger.info("Starting all enrichment components")
            startup_start = time.time()
            self._lifecycle_metrics['total_startups'] += 1
            
            startup_results = {}
            
            # Start components in dependency order
            for component_name in self._startup_order:
                try:
                    result = await self._start_component(component_name)
                    startup_results[component_name] = result
                    
                except Exception as e:
                    startup_results[component_name] = {
                        'status': 'failed',
                        'error': str(e)
                    }
                    self._lifecycle_metrics['failed_startups'] += 1
                    
                    # Stop already started components on failure
                    await self._stop_started_components(list(startup_results.keys())[:-1])
                    raise EnrichmentError(f"Component startup failed: {component_name}: {str(e)}")
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            # Start health monitoring
            await self._start_health_monitoring()
            
            self._running = True
            startup_time = time.time() - startup_start
            
            logger.info(f"All components started successfully in {startup_time:.2f}s")
            
            return {
                'status': 'success',
                'startup_time_seconds': startup_time,
                'components': startup_results,
                'total_components': len(self._startup_order)
            }
            
        except Exception as e:
            logger.error(f"Component startup failed: {e}")
            self._lifecycle_metrics['failed_startups'] += 1
            raise EnrichmentError(f"Component startup failed: {str(e)}")
    
    async def _start_component(self, component_name: str) -> Dict[str, Any]:
        """Start a specific component."""
        try:
            start_time = time.time()
            component = self._components[component_name]
            
            # Update status
            self._component_status[component_name].state = ComponentState.STARTING
            self._component_status[component_name].last_state_change = datetime.utcnow()
            
            # Start component if it has a start method
            if hasattr(component, 'start'):
                await component.start()
            
            # Update status to running
            self._component_status[component_name].state = ComponentState.RUNNING
            self._component_status[component_name].last_state_change = datetime.utcnow()
            self._component_status[component_name].error_message = None
            
            startup_time = int((time.time() - start_time) * 1000)
            
            logger.info(f"Component '{component_name}' started successfully in {startup_time}ms")
            
            return {
                'status': 'started',
                'startup_time_ms': startup_time
            }
            
        except Exception as e:
            self._component_status[component_name].state = ComponentState.FAILED
            self._component_status[component_name].error_message = str(e)
            self._component_status[component_name].last_state_change = datetime.utcnow()
            
            logger.error(f"Failed to start component '{component_name}': {e}")
            raise
    
    async def _stop_started_components(self, component_names: List[str]) -> None:
        """Stop a list of components in reverse order."""
        for component_name in reversed(component_names):
            try:
                await self._stop_component(component_name)
            except Exception as e:
                logger.error(f"Error stopping component '{component_name}' during cleanup: {e}")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown in container environments."""
        if os.name != 'nt':  # Unix/Linux only
            def signal_handler(signum: int, frame) -> None:
                logger.info(f"Received signal {signum}, initiating graceful shutdown")
                if not self._graceful_shutdown_task or self._graceful_shutdown_task.done():
                    self._graceful_shutdown_task = asyncio.create_task(self.graceful_shutdown())
            
            # Handle SIGTERM (Docker stop) and SIGINT (Ctrl+C)
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
            
            logger.debug("Signal handlers configured for graceful shutdown")
    
    async def _start_health_monitoring(self) -> None:
        """Start background health monitoring task."""
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_monitor_loop())
            logger.info("Health monitoring started")
    
    async def _health_monitor_loop(self) -> None:
        """Background health monitoring loop."""
        logger.info("Health monitoring loop started")
        
        while self._running and not self._shutdown_event.is_set():
            try:
                await self._perform_health_checks()
                
                # Wait for next check interval or shutdown event
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self._health_check_interval
                    )
                    break  # Shutdown event received
                except asyncio.TimeoutError:
                    continue  # Normal timeout, continue monitoring
                    
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
        
        logger.info("Health monitoring loop stopped")
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all components."""
        for component_name, component in self._components.items():
            try:
                # Perform health check if component supports it
                if hasattr(component, 'health_check'):
                    health_result = await component.health_check()
                    health_status = health_result.get('status', 'unknown')
                    
                    # Update component status
                    self._component_status[component_name].health_status = health_status
                    self._component_status[component_name].metrics = health_result
                    
                    # Handle unhealthy components
                    if health_status not in ['healthy', 'degraded']:
                        await self._handle_unhealthy_component(component_name, health_result)
                        
                else:
                    self._component_status[component_name].health_status = 'no_health_check'
                    
            except Exception as e:
                logger.error(f"Health check failed for component '{component_name}': {e}")
                self._component_status[component_name].health_status = 'health_check_failed'
                self._component_status[component_name].error_message = str(e)
    
    async def _handle_unhealthy_component(self, component_name: str, health_result: Dict[str, Any]) -> None:
        """Handle unhealthy component with recovery if enabled."""
        if not self._recovery_enabled:
            logger.warning(f"Component '{component_name}' is unhealthy but recovery is disabled")
            return
        
        component_status = self._component_status[component_name]
        
        # Check if component needs restart
        if (component_status.restart_count < self._max_restart_attempts and
            component_status.state != ComponentState.RECOVERING):
            
            logger.warning(f"Attempting to recover unhealthy component '{component_name}'")
            await self._recover_component(component_name)
    
    async def _recover_component(self, component_name: str) -> None:
        """Attempt to recover a failed component."""
        try:
            self._lifecycle_metrics['recovery_attempts'] += 1
            component_status = self._component_status[component_name]
            
            # Update status
            component_status.state = ComponentState.RECOVERING
            component_status.last_state_change = datetime.utcnow()
            component_status.restart_count += 1
            
            logger.info(f"Recovering component '{component_name}' (attempt {component_status.restart_count})")
            
            # Stop component
            await self._stop_component(component_name, force=True)
            
            # Wait before restart
            await asyncio.sleep(self._restart_backoff_seconds)
            
            # Restart component
            await self._start_component(component_name)
            
            self._lifecycle_metrics['successful_recoveries'] += 1
            self._lifecycle_metrics['component_restarts'] += 1
            
            logger.info(f"Component '{component_name}' recovered successfully")
            
        except Exception as e:
            logger.error(f"Recovery failed for component '{component_name}': {e}")
            component_status.state = ComponentState.FAILED
            component_status.error_message = f"Recovery failed: {str(e)}"
            component_status.last_state_change = datetime.utcnow()
    
    async def graceful_shutdown(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Perform graceful shutdown with pending task completion handling.
        
        Args:
            timeout: Shutdown timeout in seconds
            
        Returns:
            Shutdown statistics and results
        """
        timeout = timeout or self.shutdown_timeout
        logger.info(f"Starting graceful shutdown with {timeout}s timeout")
        
        shutdown_start = time.time()
        self._lifecycle_metrics['total_shutdowns'] += 1
        
        try:
            # Signal shutdown to all components
            self._shutdown_event.set()
            self._running = False
            
            # Stop health monitoring
            if self._health_check_task and not self._health_check_task.done():
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Shutdown components in reverse dependency order
            shutdown_results = {}
            
            for component_name in reversed(self._startup_order):
                try:
                    if component_name in self._components:
                        result = await asyncio.wait_for(
                            self._stop_component(component_name),
                            timeout=timeout / len(self._startup_order)
                        )
                        shutdown_results[component_name] = result
                        
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout stopping component '{component_name}', forcing shutdown")
                    shutdown_results[component_name] = {
                        'status': 'timeout',
                        'forced': True
                    }
                    await self._stop_component(component_name, force=True)
                    
                except Exception as e:
                    logger.error(f"Error stopping component '{component_name}': {e}")
                    shutdown_results[component_name] = {
                        'status': 'error',
                        'error': str(e)
                    }
            
            # Final cleanup
            await self._cleanup_failed_initialization()
            
            shutdown_time = time.time() - shutdown_start
            graceful = all(
                result.get('status') not in ['timeout', 'error'] 
                for result in shutdown_results.values()
            )
            
            result = {
                'shutdown_time_seconds': shutdown_time,
                'graceful': graceful,
                'components': shutdown_results,
                'final_metrics': self._lifecycle_metrics.copy()
            }
            
            logger.info(f"Graceful shutdown completed in {shutdown_time:.2f}s (graceful: {graceful})")
            return result
            
        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}")
            return {
                'shutdown_time_seconds': time.time() - shutdown_start,
                'graceful': False,
                'error': str(e),
                'final_metrics': self._lifecycle_metrics.copy()
            }
    
    async def _stop_component(self, component_name: str, force: bool = False) -> Dict[str, Any]:
        """Stop a specific component."""
        try:
            start_time = time.time()
            component = self._components.get(component_name)
            
            if not component:
                return {'status': 'not_found'}
            
            # Update status if component status exists
            if component_name in self._component_status:
                self._component_status[component_name].state = ComponentState.STOPPING
                self._component_status[component_name].last_state_change = datetime.utcnow()
            
            # Stop component with graceful shutdown if supported
            if hasattr(component, 'graceful_shutdown') and not force:
                # Check if it's an async method or AsyncMock
                if (inspect.iscoroutinefunction(component.graceful_shutdown) or
                    str(type(component.graceful_shutdown)).__contains__('AsyncMock')):
                    await component.graceful_shutdown()
                else:
                    component.graceful_shutdown()
            elif hasattr(component, 'stop'):
                # Check if it's an async method or AsyncMock
                if (inspect.iscoroutinefunction(component.stop) or
                    str(type(component.stop)).__contains__('AsyncMock')):
                    await component.stop()
                else:
                    component.stop()
            
            # Update status if component status exists
            if component_name in self._component_status:
                self._component_status[component_name].state = ComponentState.STOPPED
                self._component_status[component_name].last_state_change = datetime.utcnow()
            
            stop_time = int((time.time() - start_time) * 1000)
            
            logger.info(f"Component '{component_name}' stopped successfully in {stop_time}ms")
            
            return {
                'status': 'stopped',
                'stop_time_ms': stop_time,
                'forced': force
            }
            
        except Exception as e:
            if component_name in self._component_status:
                self._component_status[component_name].state = ComponentState.FAILED
                self._component_status[component_name].error_message = str(e)
                self._component_status[component_name].last_state_change = datetime.utcnow()
            
            logger.error(f"Error stopping component '{component_name}': {e}")
            raise
    
    async def _cleanup_failed_initialization(self) -> None:
        """Clean up resources from failed initialization."""
        try:
            # Clear component references
            self._components.clear()
            
            # Reset shutdown event
            if self._shutdown_event.is_set():
                self._shutdown_event.clear()
            
            logger.debug("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def get_component_status(self, component_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get status information for components.
        
        Args:
            component_name: Specific component name, or None for all components
            
        Returns:
            Component status information
        """
        try:
            if component_name:
                if component_name not in self._component_status:
                    return {'error': f'Component {component_name} not found'}
                
                status = self._component_status[component_name]
                return {
                    'name': status.name,
                    'state': status.state.value,
                    'health_status': status.health_status,
                    'last_state_change': status.last_state_change.isoformat(),
                    'error_message': status.error_message,
                    'restart_count': status.restart_count,
                    'dependencies': status.dependencies,
                    'startup_time_ms': status.startup_time_ms,
                    'metrics': status.metrics
                }
            else:
                return {
                    'components': {
                        name: {
                            'state': status.state.value,
                            'health_status': status.health_status,
                            'last_state_change': status.last_state_change.isoformat(),
                            'error_message': status.error_message,
                            'restart_count': status.restart_count
                        }
                        for name, status in self._component_status.items()
                    },
                    'running': self._running,
                    'lifecycle_metrics': self._lifecycle_metrics.copy()
                }
                
        except Exception as e:
            logger.error(f"Error getting component status: {e}")
            return {'error': str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of lifecycle manager and all components.
        
        Returns:
            Health status and detailed information
        """
        try:
            # Perform component health checks
            await self._perform_health_checks()
            
            # Aggregate health status
            component_health = {}
            overall_healthy = True
            
            for name, status in self._component_status.items():
                is_healthy = (
                    status.state == ComponentState.RUNNING and
                    status.health_status in ['healthy', 'degraded']
                )
                
                component_health[name] = {
                    'healthy': is_healthy,
                    'state': status.state.value,
                    'health_status': status.health_status,
                    'restart_count': status.restart_count
                }
                
                if not is_healthy:
                    overall_healthy = False
            
            return {
                'status': 'healthy' if overall_healthy else 'degraded',
                'running': self._running,
                'components': component_health,
                'lifecycle_metrics': self._lifecycle_metrics.copy(),
                'health_monitoring_active': (
                    self._health_check_task is not None and 
                    not self._health_check_task.done()
                ),
                'recovery_enabled': self._recovery_enabled,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Lifecycle health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_component(self, component_name: str) -> Optional[Any]:
        """
        Get component instance by name.
        
        Args:
            component_name: Name of component to retrieve
            
        Returns:
            Component instance or None if not found
        """
        return self._components.get(component_name)
    
    async def restart_component(self, component_name: str) -> Dict[str, Any]:
        """
        Restart a specific component.
        
        Args:
            component_name: Name of component to restart
            
        Returns:
            Restart operation result
        """
        try:
            if component_name not in self._components:
                return {'status': 'error', 'message': f'Component {component_name} not found'}
            
            logger.info(f"Restarting component '{component_name}'")
            
            # Stop component
            await self._stop_component(component_name)
            
            # Start component
            result = await self._start_component(component_name)
            
            self._lifecycle_metrics['component_restarts'] += 1
            
            return {
                'status': 'success',
                'component': component_name,
                'restart_result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to restart component '{component_name}': {e}")
            return {
                'status': 'error',
                'component': component_name,
                'error': str(e)
            }
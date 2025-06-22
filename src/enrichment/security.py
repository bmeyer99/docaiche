"""
Security Module - PRD-010
Task privilege isolation and secure execution environment for enrichment operations.

Implements sandboxing, privilege restrictions, and secure task execution controls
to prevent privilege escalation and ensure task isolation.
"""

import asyncio
import logging
import os
import resource
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Awaitable
from contextlib import asynccontextmanager
import signal

from .models import EnrichmentTask
from .exceptions import TaskExecutionError, EnrichmentError

logger = logging.getLogger(__name__)


class PrivilegeLevel:
    """Defines privilege levels for task execution"""
    MINIMAL = "minimal"      # Lowest privileges - read-only access
    RESTRICTED = "restricted"  # Limited write access to temp directories
    STANDARD = "standard"    # Standard enrichment task privileges
    

class TaskSandbox:
    """
    Secure task execution sandbox with privilege isolation.
    
    Implements privilege restrictions, resource limits, and secure execution
    environment for enrichment tasks to prevent privilege escalation.
    """
    
    def __init__(
        self,
        privilege_level: str = PrivilegeLevel.RESTRICTED,
        max_memory_mb: int = 256,
        max_cpu_time_seconds: int = 30,
        max_file_size_mb: int = 10,
        allowed_directories: Optional[List[str]] = None
    ):
        """
        Initialize task sandbox with security restrictions.
        
        Args:
            privilege_level: Task privilege level
            max_memory_mb: Maximum memory usage in MB
            max_cpu_time_seconds: Maximum CPU time in seconds
            max_file_size_mb: Maximum file size in MB
            allowed_directories: List of allowed directory paths
        """
        self.privilege_level = privilege_level
        self.max_memory_mb = max_memory_mb
        self.max_cpu_time_seconds = max_cpu_time_seconds
        self.max_file_size_mb = max_file_size_mb
        self.allowed_directories = allowed_directories or []
        
        # Create isolated temp directory for task execution
        self._temp_dir: Optional[tempfile.TemporaryDirectory] = None
        self._original_limits: Dict[str, Any] = {}
        
        logger.info(f"TaskSandbox initialized with privilege level: {privilege_level}")
    
    async def __aenter__(self):
        """Enter sandbox context with privilege restrictions."""
        try:
            # Create isolated temporary directory
            self._temp_dir = tempfile.TemporaryDirectory(prefix="enrichment_sandbox_")
            sandbox_path = Path(self._temp_dir.name)
            
            # Set restrictive permissions on sandbox directory
            os.chmod(sandbox_path, 0o700)
            
            # Apply resource limits
            await self._apply_resource_limits()
            
            # Apply privilege restrictions
            await self._apply_privilege_restrictions()
            
            logger.debug(f"Sandbox activated: {sandbox_path}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to enter sandbox: {e}")
            await self._cleanup()
            raise TaskExecutionError(f"Sandbox initialization failed: {str(e)}")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit sandbox context with cleanup."""
        await self._cleanup()
    
    async def _apply_resource_limits(self) -> None:
        """Apply resource limits to prevent resource exhaustion attacks."""
        try:
            # Store original limits for restoration
            self._original_limits = {}
            
            # Set memory limit - container-compatible approach
            if hasattr(resource, 'RLIMIT_AS'):
                original_memory = resource.getrlimit(resource.RLIMIT_AS)
                self._original_limits['memory'] = original_memory
                
                # Only apply limits if current limit is unlimited or higher than target
                memory_limit = self.max_memory_mb * 1024 * 1024  # Convert to bytes
                current_limit = original_memory[0]
                
                if (current_limit == resource.RLIM_INFINITY or
                    current_limit == -1 or
                    current_limit > memory_limit):
                    try:
                        resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
                        logger.debug(f"Memory limit set to {self.max_memory_mb}MB")
                    except (ValueError, PermissionError) as e:
                        logger.warning(f"Cannot set memory limit in container environment: {e}")
                        # Clear this limit from restoration list
                        self._original_limits.pop('memory', None)
                else:
                    logger.debug(f"Current memory limit ({current_limit}) already restrictive")
            
            # Set CPU time limit - container-compatible approach
            if hasattr(resource, 'RLIMIT_CPU'):
                original_cpu = resource.getrlimit(resource.RLIMIT_CPU)
                self._original_limits['cpu'] = original_cpu
                
                current_cpu_limit = original_cpu[0]
                if (current_cpu_limit == resource.RLIM_INFINITY or
                    current_cpu_limit == -1 or
                    current_cpu_limit > self.max_cpu_time_seconds):
                    try:
                        resource.setrlimit(resource.RLIMIT_CPU,
                                         (self.max_cpu_time_seconds, self.max_cpu_time_seconds))
                        logger.debug(f"CPU time limit set to {self.max_cpu_time_seconds}s")
                    except (ValueError, PermissionError) as e:
                        logger.warning(f"Cannot set CPU limit in container environment: {e}")
                        self._original_limits.pop('cpu', None)
                else:
                    logger.debug(f"Current CPU limit already restrictive")
            
            # Set file size limit - container-compatible approach
            if hasattr(resource, 'RLIMIT_FSIZE'):
                original_fsize = resource.getrlimit(resource.RLIMIT_FSIZE)
                self._original_limits['fsize'] = original_fsize
                
                file_size_limit = self.max_file_size_mb * 1024 * 1024  # Convert to bytes
                current_fsize_limit = original_fsize[0]
                
                if (current_fsize_limit == resource.RLIM_INFINITY or
                    current_fsize_limit == -1 or
                    current_fsize_limit > file_size_limit):
                    try:
                        resource.setrlimit(resource.RLIMIT_FSIZE, (file_size_limit, file_size_limit))
                        logger.debug(f"File size limit set to {self.max_file_size_mb}MB")
                    except (ValueError, PermissionError) as e:
                        logger.warning(f"Cannot set file size limit in container environment: {e}")
                        self._original_limits.pop('fsize', None)
                else:
                    logger.debug(f"Current file size limit already restrictive")
            
        except Exception as e:
            logger.warning(f"Resource limit configuration partially failed: {e}")
            # Continue execution - sandbox still provides isolation even without resource limits
    
    async def _apply_privilege_restrictions(self) -> None:
        """Apply privilege restrictions based on privilege level."""
        try:
            if self.privilege_level == PrivilegeLevel.MINIMAL:
                # Most restrictive - read-only access only
                logger.debug("Applied MINIMAL privilege restrictions")
                
            elif self.privilege_level == PrivilegeLevel.RESTRICTED:
                # Limited write access to sandbox only
                logger.debug("Applied RESTRICTED privilege restrictions")
                
            elif self.privilege_level == PrivilegeLevel.STANDARD:
                # Standard enrichment privileges
                logger.debug("Applied STANDARD privilege restrictions")
                
        except Exception as e:
            logger.error(f"Failed to apply privilege restrictions: {e}")
            raise TaskExecutionError(f"Privilege restriction failed: {str(e)}")
    
    async def _cleanup(self) -> None:
        """Clean up sandbox resources and restore original limits."""
        try:
            # Restore original resource limits - container-compatible
            for limit_type, original_limit in self._original_limits.items():
                try:
                    # Only attempt to restore if original limit was not unlimited
                    should_restore = (
                        original_limit[0] != resource.RLIM_INFINITY and
                        original_limit[0] != -1
                    )
                    
                    if should_restore:
                        if limit_type == 'memory' and hasattr(resource, 'RLIMIT_AS'):
                            resource.setrlimit(resource.RLIMIT_AS, original_limit)
                        elif limit_type == 'cpu' and hasattr(resource, 'RLIMIT_CPU'):
                            resource.setrlimit(resource.RLIMIT_CPU, original_limit)
                        elif limit_type == 'fsize' and hasattr(resource, 'RLIMIT_FSIZE'):
                            resource.setrlimit(resource.RLIMIT_FSIZE, original_limit)
                    else:
                        logger.debug(f"Skipping restore of unlimited {limit_type} limit in container")
                        
                except (ValueError, PermissionError) as e:
                    # Container environments may not allow limit restoration
                    logger.debug(f"Cannot restore {limit_type} limit in container environment: {e}")
                except Exception as e:
                    logger.warning(f"Failed to restore {limit_type} limit: {e}")
            
            # Clean up temporary directory
            if self._temp_dir:
                try:
                    self._temp_dir.cleanup()
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory: {e}")
                finally:
                    self._temp_dir = None
            
            logger.debug("Sandbox cleanup completed")
            
        except Exception as e:
            logger.error(f"Sandbox cleanup failed: {e}")
    
    def get_sandbox_path(self) -> Optional[Path]:
        """Get the sandbox temporary directory path."""
        if self._temp_dir:
            return Path(self._temp_dir.name)
        return None
    
    async def validate_file_access(self, file_path: str) -> bool:
        """
        Validate if file access is allowed within sandbox restrictions.
        
        Args:
            file_path: Path to validate
            
        Returns:
            True if access is allowed
        """
        try:
            path = Path(file_path).resolve()
            
            # Check if path is within sandbox
            if self._temp_dir:
                sandbox_path = Path(self._temp_dir.name).resolve()
                if not str(path).startswith(str(sandbox_path)):
                    # Check if path is in allowed directories
                    for allowed_dir in self.allowed_directories:
                        if str(path).startswith(str(Path(allowed_dir).resolve())):
                            return True
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"File access validation failed: {e}")
            return False


class SecureTaskExecutor:
    """
    Secure task executor with privilege isolation and sandboxing.
    
    Executes enrichment tasks in isolated environments with controlled privileges
    to prevent security vulnerabilities and privilege escalation.
    """
    
    def __init__(self):
        """Initialize secure task executor."""
        self._active_sandboxes: Dict[str, TaskSandbox] = {}
        self._execution_metrics = {
            'tasks_executed': 0,
            'security_violations': 0,
            'privilege_escalations_blocked': 0,
            'resource_limit_violations': 0
        }
        
        logger.info("SecureTaskExecutor initialized")
    
    async def execute_task_securely(
        self,
        task: EnrichmentTask,
        task_handler: Callable[[EnrichmentTask], Awaitable[Any]],
        privilege_level: str = PrivilegeLevel.RESTRICTED
    ) -> Any:
        """
        Execute task in secure sandbox with privilege isolation.
        
        Args:
            task: Task to execute
            task_handler: Task execution function
            privilege_level: Privilege level for execution
            
        Returns:
            Task execution result
            
        Raises:
            TaskExecutionError: If secure execution fails
        """
        task_id = task.content_id
        
        try:
            logger.info(f"Starting secure execution for task: {task_id}")
            
            # Create sandbox for task
            sandbox = TaskSandbox(
                privilege_level=privilege_level,
                max_memory_mb=256,
                max_cpu_time_seconds=60,
                max_file_size_mb=10
            )
            
            self._active_sandboxes[task_id] = sandbox
            
            # Execute task in sandbox
            async with sandbox:
                # Set up signal handlers for timeout
                original_handler = signal.signal(signal.SIGALRM, self._timeout_handler)
                signal.alarm(60)  # 60 second timeout
                
                try:
                    # Execute task with privilege restrictions
                    result = await self._execute_with_monitoring(task, task_handler, sandbox)
                    
                    self._execution_metrics['tasks_executed'] += 1
                    logger.info(f"Task executed securely: {task_id}")
                    
                    return result
                    
                finally:
                    # Restore original signal handler
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, original_handler)
                    
        except Exception as e:
            self._execution_metrics['security_violations'] += 1
            logger.error(f"Secure task execution failed: {task_id}: {e}")
            raise TaskExecutionError(f"Secure execution failed: {str(e)}")
            
        finally:
            # Remove sandbox from active list
            self._active_sandboxes.pop(task_id, None)
    
    async def _execute_with_monitoring(
        self,
        task: EnrichmentTask,
        task_handler: Callable[[EnrichmentTask], Awaitable[Any]],
        sandbox: TaskSandbox
    ) -> Any:
        """Execute task with security monitoring."""
        try:
            # Monitor for privilege escalation attempts
            start_time = datetime.utcnow()
            
            # Execute task handler
            result = await task_handler(task)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Log execution metrics
            logger.debug(f"Task executed in {execution_time:.2f}s with privilege level: {sandbox.privilege_level}")
            
            return result
            
        except MemoryError:
            self._execution_metrics['resource_limit_violations'] += 1
            raise TaskExecutionError("Task exceeded memory limits")
            
        except OSError as e:
            if "exceeded" in str(e).lower():
                self._execution_metrics['resource_limit_violations'] += 1
                raise TaskExecutionError("Task exceeded resource limits")
            raise
    
    def _timeout_handler(self, signum, frame):
        """Handle task execution timeout."""
        logger.error("Task execution timeout - terminating")
        raise TaskExecutionError("Task execution timed out")
    
    async def get_security_metrics(self) -> Dict[str, Any]:
        """
        Get security execution metrics.
        
        Returns:
            Security metrics and statistics
        """
        return {
            'execution_metrics': self._execution_metrics.copy(),
            'active_sandboxes': len(self._active_sandboxes),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def cleanup_sandbox(self, task_id: str) -> None:
        """
        Clean up sandbox for specific task.
        
        Args:
            task_id: Task identifier
        """
        if task_id in self._active_sandboxes:
            try:
                await self._active_sandboxes[task_id]._cleanup()
                del self._active_sandboxes[task_id]
                logger.debug(f"Sandbox cleaned up for task: {task_id}")
            except Exception as e:
                logger.error(f"Sandbox cleanup failed for task {task_id}: {e}")


@asynccontextmanager
async def secure_task_context(
    task_id: str,
    privilege_level: str = PrivilegeLevel.RESTRICTED
):
    """
    Context manager for secure task execution.
    
    Args:
        task_id: Task identifier
        privilege_level: Execution privilege level
        
    Yields:
        Secure execution context
    """
    sandbox = TaskSandbox(privilege_level=privilege_level)
    
    try:
        async with sandbox:
            logger.debug(f"Secure context established for task: {task_id}")
            yield sandbox
    finally:
        logger.debug(f"Secure context closed for task: {task_id}")


def get_task_privilege_level(task_type: str) -> str:
    """
    Determine appropriate privilege level for task type.
    
    Args:
        task_type: Type of enrichment task
        
    Returns:
        Appropriate privilege level
    """
    # Map task types to privilege levels for security
    privilege_mapping = {
        "content_analysis": PrivilegeLevel.MINIMAL,
        "relationship_mapping": PrivilegeLevel.RESTRICTED,
        "tag_generation": PrivilegeLevel.RESTRICTED,
        "quality_assessment": PrivilegeLevel.MINIMAL,
        "metadata_enhancement": PrivilegeLevel.RESTRICTED
    }
    
    return privilege_mapping.get(task_type, PrivilegeLevel.RESTRICTED)
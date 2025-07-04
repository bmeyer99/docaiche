"""
Job Scheduler for Context7 Background Jobs
==========================================

Handles job scheduling with cron expressions, intervals, and one-time executions.
Provides flexible scheduling capabilities for Context7 document management jobs.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import re

from .models import JobConfig, JobSchedule, BackgroundJobManagerConfig

logger = logging.getLogger(__name__)


class CronParser:
    """Simple cron expression parser"""
    
    @staticmethod
    def parse_cron(cron_expr: str) -> Dict[str, Set[int]]:
        """Parse cron expression into field sets"""
        fields = cron_expr.split()
        if len(fields) not in [5, 6]:
            raise ValueError("Cron expression must have 5 or 6 fields")
        
        # Standard 5-field cron: minute hour day month weekday
        # 6-field cron: second minute hour day month weekday
        field_names = ["minute", "hour", "day", "month", "weekday"]
        if len(fields) == 6:
            field_names = ["second"] + field_names
        
        parsed = {}
        for i, field in enumerate(fields):
            field_name = field_names[i]
            parsed[field_name] = CronParser._parse_field(field, field_name)
        
        return parsed
    
    @staticmethod
    def _parse_field(field: str, field_name: str) -> Set[int]:
        """Parse individual cron field"""
        if field == "*":
            return set(range(*CronParser._get_field_range(field_name)))
        
        if field.startswith("*/"):
            step = int(field[2:])
            field_range = CronParser._get_field_range(field_name)
            return set(range(field_range[0], field_range[1], step))
        
        if "-" in field:
            start, end = map(int, field.split("-"))
            return set(range(start, end + 1))
        
        if "," in field:
            return set(map(int, field.split(",")))
        
        return {int(field)}
    
    @staticmethod
    def _get_field_range(field_name: str) -> tuple:
        """Get valid range for cron field"""
        ranges = {
            "second": (0, 60),
            "minute": (0, 60),
            "hour": (0, 24),
            "day": (1, 32),
            "month": (1, 13),
            "weekday": (0, 7)  # 0 and 7 are Sunday
        }
        return ranges.get(field_name, (0, 60))
    
    @staticmethod
    def matches(cron_expr: str, dt: datetime) -> bool:
        """Check if datetime matches cron expression"""
        try:
            parsed = CronParser.parse_cron(cron_expr)
            
            # Check each field
            if "second" in parsed and dt.second not in parsed["second"]:
                return False
            if "minute" in parsed and dt.minute not in parsed["minute"]:
                return False
            if "hour" in parsed and dt.hour not in parsed["hour"]:
                return False
            if "day" in parsed and dt.day not in parsed["day"]:
                return False
            if "month" in parsed and dt.month not in parsed["month"]:
                return False
            if "weekday" in parsed:
                weekday = dt.weekday()  # Monday is 0
                # Convert to cron weekday (Sunday is 0)
                cron_weekday = (weekday + 1) % 7
                if cron_weekday not in parsed["weekday"] and weekday not in parsed["weekday"]:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error parsing cron expression '{cron_expr}': {e}")
            return False


class JobScheduler:
    """
    Job scheduler for Context7 background jobs
    
    Handles various scheduling types:
    - Interval-based (seconds, minutes, hours, days)
    - Cron expressions
    - One-time executions
    """
    
    def __init__(self, config: BackgroundJobManagerConfig):
        self.config = config
        self.scheduled_jobs: Dict[str, JobConfig] = {}
        self.next_execution_times: Dict[str, datetime] = {}
        self.execution_counts: Dict[str, int] = {}
        
        logger.info("Job scheduler initialized")
    
    async def schedule_job(self, job_config: JobConfig) -> None:
        """Schedule a job for execution"""
        try:
            self.scheduled_jobs[job_config.job_id] = job_config
            
            # Calculate next execution time
            next_time = self._calculate_next_execution(job_config)
            if next_time:
                self.next_execution_times[job_config.job_id] = next_time
                logger.info(f"Scheduled job '{job_config.job_id}' for {next_time}")
            else:
                logger.warning(f"Could not schedule job '{job_config.job_id}' - invalid schedule")
            
            # Initialize execution count
            self.execution_counts[job_config.job_id] = 0
            
        except Exception as e:
            logger.error(f"Failed to schedule job '{job_config.job_id}': {e}")
            raise
    
    async def unschedule_job(self, job_id: str) -> None:
        """Unschedule a job"""
        try:
            if job_id in self.scheduled_jobs:
                del self.scheduled_jobs[job_id]
            if job_id in self.next_execution_times:
                del self.next_execution_times[job_id]
            if job_id in self.execution_counts:
                del self.execution_counts[job_id]
            
            logger.info(f"Unscheduled job: {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to unschedule job '{job_id}': {e}")
            raise
    
    async def get_due_jobs(self) -> List[JobConfig]:
        """Get jobs that are due for execution"""
        due_jobs = []
        current_time = datetime.utcnow()
        
        for job_id, job_config in self.scheduled_jobs.items():
            if not job_config.enabled:
                continue
            
            # Check if job is due
            if self._is_job_due(job_id, current_time):
                due_jobs.append(job_config)
                
                # Update next execution time
                next_time = self._calculate_next_execution(job_config, current_time)
                if next_time:
                    self.next_execution_times[job_id] = next_time
                else:
                    # Job has completed all executions
                    logger.info(f"Job '{job_id}' has completed all scheduled executions")
                    if job_id in self.next_execution_times:
                        del self.next_execution_times[job_id]
                
                # Increment execution count
                self.execution_counts[job_id] = self.execution_counts.get(job_id, 0) + 1
        
        return due_jobs
    
    def _is_job_due(self, job_id: str, current_time: datetime) -> bool:
        """Check if a job is due for execution"""
        if job_id not in self.next_execution_times:
            return False
        
        next_execution = self.next_execution_times[job_id]
        return current_time >= next_execution
    
    def _calculate_next_execution(
        self, 
        job_config: JobConfig, 
        from_time: Optional[datetime] = None
    ) -> Optional[datetime]:
        """Calculate next execution time for a job"""
        if from_time is None:
            from_time = datetime.utcnow()
        
        schedule = job_config.schedule
        
        # Check execution limits
        if schedule.max_executions is not None:
            execution_count = self.execution_counts.get(job_config.job_id, 0)
            if execution_count >= schedule.max_executions:
                return None
        
        # Check schedule bounds
        if schedule.start_time and from_time < schedule.start_time:
            from_time = schedule.start_time
        
        if schedule.end_time and from_time > schedule.end_time:
            return None
        
        # Calculate based on schedule type
        if schedule.schedule_type == "once":
            return schedule.execute_at
        
        elif schedule.schedule_type == "interval":
            return self._calculate_interval_next(schedule, from_time)
        
        elif schedule.schedule_type == "cron":
            return self._calculate_cron_next(schedule, from_time)
        
        else:
            logger.error(f"Unknown schedule type: {schedule.schedule_type}")
            return None
    
    def _calculate_interval_next(
        self, 
        schedule: JobSchedule, 
        from_time: datetime
    ) -> Optional[datetime]:
        """Calculate next execution time for interval schedule"""
        delta = timedelta()
        
        if schedule.interval_seconds:
            delta += timedelta(seconds=schedule.interval_seconds)
        if schedule.interval_minutes:
            delta += timedelta(minutes=schedule.interval_minutes)
        if schedule.interval_hours:
            delta += timedelta(hours=schedule.interval_hours)
        if schedule.interval_days:
            delta += timedelta(days=schedule.interval_days)
        
        if delta.total_seconds() == 0:
            logger.error("Interval schedule has no interval specified")
            return None
        
        next_time = from_time + delta
        
        # Check end time
        if schedule.end_time and next_time > schedule.end_time:
            return None
        
        return next_time
    
    def _calculate_cron_next(
        self, 
        schedule: JobSchedule, 
        from_time: datetime
    ) -> Optional[datetime]:
        """Calculate next execution time for cron schedule"""
        if not schedule.cron_expression:
            return None
        
        # Start from the next minute to avoid immediate re-execution
        next_time = from_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
        
        # Search for next matching time (within reasonable bounds)
        max_iterations = 60 * 24 * 7  # One week worth of minutes
        iterations = 0
        
        while iterations < max_iterations:
            if CronParser.matches(schedule.cron_expression, next_time):
                # Check end time
                if schedule.end_time and next_time > schedule.end_time:
                    return None
                return next_time
            
            next_time += timedelta(minutes=1)
            iterations += 1
        
        logger.error(f"Could not find next execution time for cron: {schedule.cron_expression}")
        return None
    
    def get_next_execution_time(self, job_id: str) -> Optional[datetime]:
        """Get next execution time for a job"""
        return self.next_execution_times.get(job_id)
    
    def get_scheduled_jobs(self) -> Dict[str, JobConfig]:
        """Get all scheduled jobs"""
        return self.scheduled_jobs.copy()
    
    def get_job_schedule_info(self, job_id: str) -> Optional[Dict[str, any]]:
        """Get schedule information for a job"""
        if job_id not in self.scheduled_jobs:
            return None
        
        job_config = self.scheduled_jobs[job_id]
        return {
            "job_id": job_id,
            "job_name": job_config.job_name,
            "schedule_type": job_config.schedule.schedule_type,
            "enabled": job_config.enabled,
            "next_execution": self.next_execution_times.get(job_id),
            "execution_count": self.execution_counts.get(job_id, 0),
            "max_executions": job_config.schedule.max_executions,
            "start_time": job_config.schedule.start_time,
            "end_time": job_config.schedule.end_time
        }
    
    def get_all_schedule_info(self) -> List[Dict[str, any]]:
        """Get schedule information for all jobs"""
        return [
            self.get_job_schedule_info(job_id)
            for job_id in self.scheduled_jobs.keys()
        ]
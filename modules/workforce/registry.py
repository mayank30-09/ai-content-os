"""Worker registry module for AI Workforce Core subsystem.

Manages registration, unregistration, capability searching, enabling, disabling,
and health auditing for AI workforce workers.
"""


from loguru import logger

from modules.workforce.base_worker import BaseWorker


class WorkerRegistry:
    """Central registry managing worker registration and capability lookups."""

    def __init__(self):
        self._workers: dict[str, BaseWorker] = {}
        self._enabled_states: dict[str, bool] = {}

    def register(self, worker: BaseWorker) -> None:
        """Registers a BaseWorker instance in the registry.

        Args:
            worker: BaseWorker instance to register.
        """
        if worker.worker_id in self._workers:
            logger.warning(f"Overwriting registered worker ID: '{worker.worker_id}'")
        self._workers[worker.worker_id] = worker
        self._enabled_states[worker.worker_id] = True
        logger.info(
            f"Registered worker '{worker.worker_name}' (ID: {worker.worker_id}) "
            f"[Role: {worker.role}, Capabilities: {worker.capabilities}]"
        )

    def unregister(self, worker_id: str) -> BaseWorker | None:
        """Unregisters and returns a worker by ID.

        Args:
            worker_id: Target worker ID string.

        Returns:
            Optional[BaseWorker]: Removed worker instance or None if not found.
        """
        worker = self._workers.pop(worker_id, None)
        self._enabled_states.pop(worker_id, None)
        if worker:
            logger.info(f"Unregistered worker ID: '{worker_id}'")
        return worker

    def enable(self, worker_id: str) -> bool:
        """Enables a worker by ID."""
        if worker_id in self._workers:
            self._enabled_states[worker_id] = True
            logger.info(f"Enabled worker ID: '{worker_id}'")
            return True
        return False

    def disable(self, worker_id: str) -> bool:
        """Disables a worker by ID."""
        if worker_id in self._workers:
            self._enabled_states[worker_id] = False
            logger.info(f"Disabled worker ID: '{worker_id}'")
            return True
        return False

    def get_worker(self, worker_id: str) -> BaseWorker | None:
        """Gets worker instance by ID."""
        return self._workers.get(worker_id)

    def is_enabled(self, worker_id: str) -> bool:
        """Returns True if worker is registered and enabled."""
        return self._enabled_states.get(worker_id, False)

    def find_by_capability(self, capability: str) -> list[BaseWorker]:
        """Finds all active, enabled workers that support the required capability.

        Args:
            capability: Required capability descriptor string.

        Returns:
            List[BaseWorker]: List of matching enabled workers.
        """
        matches = []
        for worker_id, worker in self._workers.items():
            if self._enabled_states.get(worker_id, False) and capability in worker.capabilities:
                matches.append(worker)
        logger.debug(f"Found {len(matches)} active workers for capability '{capability}'")
        return matches

    def discover(self) -> list[str]:
        """Returns list of all registered worker IDs."""
        return list(self._workers.keys())

    async def run_health_checks(self) -> dict[str, bool]:
        """Runs health checks across all registered workers.

        Returns:
            Dict[str, bool]: Map of worker_id to health status boolean.
        """
        statuses = {}
        for worker_id, worker in self._workers.items():
            try:
                is_healthy = await worker.health_check()
                statuses[worker_id] = is_healthy
                logger.debug(f"Worker health check '{worker_id}': {'HEALTHY' if is_healthy else 'UNHEALTHY'}")
            except Exception as e:
                logger.error(f"Health check exception for worker '{worker_id}': {e}")
                statuses[worker_id] = False
        return statuses

worker_registry = WorkerRegistry()

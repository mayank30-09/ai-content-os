"""Publisher Worker telemetry metrics model.

Tracks performance indicators for the PublisherWorker execution pipeline.
"""

from pydantic import BaseModel, Field


class PublisherWorkerMetrics(BaseModel):
    """Telemetry metrics for the PublisherWorker execution pipeline.

    Attributes:
        publish_time: Total pipeline execution duration in seconds.
        payload_size: Character length of the constructed platform payload.
        link_resolution_count: Total count of internal and external links resolved.
        schema_resolution_count: Total count of schema placeholders populated.
        publish_success: Boolean indicating whether publication succeeded.
        retry_count: Count of publication retry attempts executed.
        adapter_latency: Time spent inside the platform adapter call.
        platform_response_time: Response latency reported by platform adapter.
        total_publications: Total number of publications executed by worker.
    """

    publish_time: float = Field(default=0.0, ge=0.0, description="Pipeline duration in seconds")
    payload_size: int = Field(default=0, ge=0, description="Character length of constructed payload")
    link_resolution_count: int = Field(default=0, ge=0, description="Resolved link count")
    schema_resolution_count: int = Field(default=0, ge=0, description="Populated schema placeholders count")
    publish_success: bool = Field(default=True, description="Publication outcome boolean")
    retry_count: int = Field(default=0, ge=0, description="Retry attempt count")
    adapter_latency: float = Field(default=0.0, ge=0.0, description="Platform adapter latency")
    platform_response_time: float = Field(default=0.0, ge=0.0, description="Platform response latency")
    total_publications: int = Field(default=1, ge=0, description="Total publications count")

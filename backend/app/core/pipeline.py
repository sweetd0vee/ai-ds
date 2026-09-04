import logging
from pathlib import Path

from .llm import get_llm_analyst
from .pipeline_steps import (
    PipelineContext,
    step_analysis_and_visualizations,
    step_discovery,
    step_final_report,
    step_insights,
    step_metrics,
    step_prepare,
    step_structure,
)
from ..jobs import JobStore

logger = logging.getLogger(__name__)


async def run_analysis_pipeline(job_id: str, store: JobStore):
    job = store.get(job_id)
    output_dir = Path(job.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ctx = PipelineContext(
        job_id=job_id,
        store=store,
        job=job,
        output_dir=output_dir,
        graph_count=job.graph_count,
        analyst=get_llm_analyst(job.analyst_model),
    )

    try:
        await step_prepare(ctx)
        await step_structure(ctx)
        await step_insights(ctx)
        await step_discovery(ctx)
        await step_metrics(ctx)
        await step_analysis_and_visualizations(ctx)
        await step_final_report(ctx)
        await store.complete(job_id, ctx.state)
    except Exception as e:
        logger.exception("Pipeline failed for job %s", job_id)
        await store.fail(job_id, str(e), ctx.state)

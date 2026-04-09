"""
VETKA Eval Routes - FastAPI Version

@file eval_routes.py
@status ACTIVE
@phase Phase 39.4
@lastAudit 2026-01-05

Evaluation API routes - EvalAgent endpoints.
Migrated from src/server/routes/eval_routes.py (Flask Blueprint)

Endpoints:
- POST /api/eval/score - Evaluate agent output
- POST /api/eval/score/with-retry - Evaluate with automatic retry
- GET /api/eval/history - Get evaluation history
- GET /api/eval/stats - Get evaluation statistics
- POST /api/eval/feedback/submit - Submit user feedback

Changes from Flask version:
- Blueprint -> APIRouter
- request.get_json() -> Pydantic BaseModel
- request.args.get() -> Query()
- current_app.config -> request.app.state
- return jsonify({}) -> return {}
- def -> async def
"""

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional, List


router = APIRouter(prefix="/api/eval", tags=["evaluation"])


# ============================================================
# PYDANTIC MODELS
# ============================================================

class EvalScoreRequest(BaseModel):
    """Request to evaluate output."""
    task: str
    output: str
    complexity: Optional[str] = "MEDIUM"


class EvalWithRetryRequest(BaseModel):
    """Request to evaluate with retry logic."""
    task: str
    output: str
    complexity: Optional[str] = "MEDIUM"


class FeedbackSubmitRequest(BaseModel):
    """Request to submit evaluation feedback."""
    evaluation_id: str
    task: Optional[str] = ""
    output: Optional[str] = ""
    rating: Optional[str] = ""
    correction: Optional[str] = ""
    score: Optional[float] = None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_eval_components(request: Request) -> dict:
    """Get eval-related components from app state (DI pattern)."""
    flask_config = getattr(request.app.state, 'flask_config', {})
    return {
        'get_eval_agent': flask_config.get('get_eval_agent'),
        'get_memory_manager': flask_config.get('get_memory_manager'),
        'feedback_loop': flask_config.get('feedback_loop'),
        'FEEDBACK_LOOP_V2_AVAILABLE': flask_config.get('FEEDBACK_LOOP_V2_AVAILABLE', False),
    }


# ============================================================
# ROUTES
# ============================================================

@router.post("/score")
async def evaluate_output(req: EvalScoreRequest, request: Request):
    """
    Evaluate agent output.

    Returns evaluation result with score and breakdown.
    """
    try:
        components = _get_eval_components(request)
        get_eval_agent = components['get_eval_agent']

        if not get_eval_agent:
            # Graceful degradation
            return {
                'score': 0.75,
                'breakdown': {},
                'feedback': 'EvalAgent not available, returning default score',
                'available': False
            }

        evaluator = get_eval_agent()
        result = evaluator.evaluate(
            task=req.task,
            output=req.output,
            complexity=req.complexity
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/score/with-retry")
async def evaluate_with_retry(req: EvalWithRetryRequest, request: Request):
    """
    Evaluate with automatic retry.

    If initial evaluation fails threshold, will retry.
    """
    try:
        components = _get_eval_components(request)
        get_eval_agent = components['get_eval_agent']

        if not get_eval_agent:
            # Graceful degradation
            return {
                'score': 0.75,
                'attempts': 1,
                'improved': False,
                'final_output': req.output,
                'available': False
            }

        evaluator = get_eval_agent()
        result = evaluator.evaluate_with_retry(
            task=req.task,
            output=req.output,
            complexity=req.complexity
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_eval_history(
    limit: int = Query(10, description="Max history items"),
    request: Request = None
):
    """
    Get EvalAgent history.

    Returns recent evaluation results.
    """
    try:
        components = _get_eval_components(request)
        get_eval_agent = components['get_eval_agent']

        if not get_eval_agent:
            return {'history': [], 'available': False}

        evaluator = get_eval_agent()
        history = evaluator.get_history(limit=limit)

        return {'history': history}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_eval_stats(request: Request):
    """
    Get EvalAgent statistics.

    Returns aggregated evaluation metrics.
    """
    try:
        components = _get_eval_components(request)
        get_eval_agent = components['get_eval_agent']

        if not get_eval_agent:
            return {
                'total_evals': 0,
                'avg_score': 0.0,
                'pass_rate': 0.0,
                'available': False
            }

        evaluator = get_eval_agent()
        stats = evaluator.get_stats()

        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback/submit")
async def submit_eval_feedback(req: FeedbackSubmitRequest, request: Request):
    """
    Submit user feedback on evaluation.

    Stores feedback in memory and FeedbackLoop v2 if available.
    """
    try:
        components = _get_eval_components(request)
        get_memory_manager = components['get_memory_manager']
        feedback_loop = components['feedback_loop']
        FEEDBACK_LOOP_V2_AVAILABLE = components['FEEDBACK_LOOP_V2_AVAILABLE']

        if not get_memory_manager:
            raise HTTPException(status_code=503, detail="Memory manager not available")

        memory = get_memory_manager()
        success = memory.save_feedback(
            evaluation_id=req.evaluation_id,
            task=req.task,
            output=req.output,
            rating=req.rating,
            correction=req.correction,
            score=req.score
        )

        # Also store in Feedback Loop v2 if available
        feedback_loop_success = False
        if FEEDBACK_LOOP_V2_AVAILABLE and feedback_loop:
            try:
                feedback_loop_success = feedback_loop.submit_feedback(
                    eval_id=req.evaluation_id,
                    task=req.task,
                    output=req.output,
                    rating=req.rating,
                    score=req.score or 0.0,
                    correction=req.correction
                )
                if feedback_loop_success:
                    print(f"  [Eval] Feedback saved to FeedbackLoopV2: {req.evaluation_id}")
                else:
                    print(f"  [Eval] FeedbackLoopV2 returned False: {req.evaluation_id}")
            except Exception as e:
                print(f"  [Eval] FeedbackLoopV2 error (fallback): {e}")

        if success:
            print(f"  [Eval] Feedback saved: {req.evaluation_id} -> {req.rating}")
            return {
                'status': 'success',
                'message': f'Feedback saved to learning system ({req.rating})',
                'evaluation_id': req.evaluation_id,
                'learning_context': 'This will improve future similar tasks',
                'weaviate_saved': True,
                'feedback_loop_saved': feedback_loop_success
            }
        else:
            print(f"  [Eval] Failed to save feedback: {req.evaluation_id}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save feedback for {req.evaluation_id}"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"  [Eval] Feedback endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

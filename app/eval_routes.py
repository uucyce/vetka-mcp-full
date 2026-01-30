"""Flask API routes for EvalAgent integration"""

from flask import Blueprint, request, jsonify
from src.agents.eval_agent import EvalAgent

# Create blueprint
eval_bp = Blueprint('eval', __name__, url_prefix='/api/eval')

# Global EvalAgent instance
_eval_agent_instance = None


def get_eval_agent():
    """Get or create EvalAgent instance"""
    global _eval_agent_instance
    if _eval_agent_instance is None:
        _eval_agent_instance = EvalAgent(model="deepseek-coder:6.7b")
    return _eval_agent_instance


# ============ EVALUATION ENDPOINTS ============

@eval_bp.route('/score', methods=['POST'])
def evaluate_output():
    """
    Evaluate agent output
    
    POST /api/eval/score
    {
        "task": "Add login button",
        "output": "def login_button(): ...",
        "complexity": "SMALL",
        "reference": "Optional reference output"
    }
    
    Response:
    {
        "score": 0.75,
        "scores": {
            "correctness": 0.8,
            "completeness": 0.7,
            "code_quality": 0.7,
            "clarity": 0.8
        },
        "feedback": "Good overall...",
        "should_retry": false
    }
    """
    try:
        data = request.json or {}
        task = data.get('task', '')
        output = data.get('output', '')
        complexity = data.get('complexity', 'MEDIUM')
        reference = data.get('reference', None)
        
        if not task or not output:
            return jsonify({'error': 'task and output are required'}), 400
        
        # Evaluate
        eval_agent = get_eval_agent()
        result = eval_agent.evaluate(
            task=task,
            output=output,
            complexity=complexity,
            reference=reference
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@eval_bp.route('/score/with-retry', methods=['POST'])
def evaluate_with_retry():
    """
    Evaluate with automatic retry (max 3 times)
    
    POST /api/eval/score/with-retry
    {
        "task": "Add login button",
        "output": "def login_button(): ...",
        "complexity": "SMALL"
    }
    """
    try:
        data = request.json or {}
        task = data.get('task', '')
        output = data.get('output', '')
        complexity = data.get('complexity', 'MEDIUM')
        
        if not task or not output:
            return jsonify({'error': 'task and output are required'}), 400
        
        # Evaluate with retry
        eval_agent = get_eval_agent()
        result = eval_agent.evaluate_with_retry(
            task=task,
            output=output,
            complexity=complexity
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@eval_bp.route('/history', methods=['GET'])
def get_eval_history():
    """
    Get EvalAgent evaluation history
    
    GET /api/eval/history?limit=10
    
    Response: { "history": [...] }
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        eval_agent = get_eval_agent()
        history = eval_agent.get_history(limit=limit)
        
        return jsonify({'history': history}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@eval_bp.route('/stats', methods=['GET'])
def get_eval_stats():
    """
    Get EvalAgent statistics
    
    GET /api/eval/stats
    
    Response:
    {
        "total_evaluations": 42,
        "average_score": 0.78,
        "success_rate": 71.4,
        "successful": 30,
        "failed": 12
    }
    """
    try:
        eval_agent = get_eval_agent()
        stats = eval_agent.get_stats()
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@eval_bp.route('/clear-history', methods=['DELETE'])
def clear_history():
    """
    Clear evaluation history
    
    DELETE /api/eval/clear-history
    """
    try:
        eval_agent = get_eval_agent()
        eval_agent.evaluation_history = []
        
        return jsonify({
            'status': 'success',
            'message': 'Evaluation history cleared'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ FEEDBACK ENDPOINTS (Human-in-the-Loop) ============

@eval_bp.route('/feedback/submit', methods=['POST'])
def submit_feedback():
    """
    Submit user feedback on evaluation
    (Готовка для Phase 6.3 - Human-in-the-Loop)
    
    POST /api/eval/feedback/submit
    {
        "evaluation_id": "eval_20251027_...",
        "rating": "👍" or "👎",
        "correction": "Optional correction from user",
        "comment": "Optional comment"
    }
    
    Response:
    {
        "status": "success",
        "message": "Feedback saved"
    }
    """
    try:
        data = request.json or {}
        eval_id = data.get('evaluation_id', '')
        rating = data.get('rating', '')  # 👍 or 👎
        correction = data.get('correction', '')
        comment = data.get('comment', '')
        
        if not eval_id:
            return jsonify({'error': 'evaluation_id is required'}), 400
        
        # TODO: Save to Weaviate VetkaUserFeedback collection
        # This will be done in Phase 6.3 when we integrate Weaviate feedback loop
        
        return jsonify({
            'status': 'success',
            'message': 'Feedback recorded',
            'evaluation_id': eval_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@eval_bp.route('/feedback/list', methods=['GET'])
def list_feedback():
    """
    List all user feedback
    (Для Phase 6.3 dashboard)
    
    GET /api/eval/feedback/list?limit=20
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        
        # TODO: Query from Weaviate VetkaUserFeedback collection
        # For now, return empty
        
        return jsonify({
            'feedback': [],
            'total': 0
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

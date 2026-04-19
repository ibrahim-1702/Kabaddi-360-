"""
LLM Feedback System - Django Views

Django views for LLM Feedback generation with CORS support
"""

import json
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from llm_feedback.prompt_builder import build_prompts, validate_context
from llm_feedback.llm_client import generate_feedback


def add_cors_headers(response):
    """Add CORS headers to response"""
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def generate_feedback_view(request):
    """
    Generate coaching feedback from canonical context JSON.
    
    Handles OPTIONS preflight and POST requests with CORS headers.
    """
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'ok'})
        return add_cors_headers(response)
    
    try:
        # Parse request body
        print(f"[LLM FEEDBACK] Received POST request")
        print(f"[LLM FEEDBACK] Request body: {request.body}")
        
        body = json.loads(request.body)
        session_id = body.get('session_id')
        context = body.get('context')
        technique_name = body.get('technique_name', 'Unknown Technique')
        
        print(f"[LLM FEEDBACK] Session ID: {session_id}")
        print(f"[LLM FEEDBACK] Technique: {technique_name}")
        print(f"[LLM FEEDBACK] Has inline context: {context is not None}")
        
        # Load context from session_id if provided
        if session_id and not context:
            context_path = Path(__file__).parent.parent / 'data' / 'results' / session_id / 'context.json'
            print(f"[LLM FEEDBACK] Context path: {context_path}")
            print(f"[LLM FEEDBACK] Context exists: {context_path.exists()}")
            
            if not context_path.exists():
                response = JsonResponse({
                    "error": f"Context file not found for session: {session_id}",
                    "generation_status": "error"
                }, status=404)
                return add_cors_headers(response)
            
            try:
                with open(context_path, 'r') as f:
                    context = json.load(f)
                print(f"[LLM FEEDBACK] Context loaded successfully")
            except Exception as e:
                print(f"[LLM FEEDBACK] Error loading context: {e}")
                response = JsonResponse({
                    "error": f"Failed to load context file: {str(e)}",
                    "generation_status": "error"
                }, status=500)
                return add_cors_headers(response)
        
        # Validate that we have context
        if not context:
            response = JsonResponse({
                "error": "Missing 'context' or 'session_id' in request body",
                "generation_status": "error"
            }, status=400)
            return add_cors_headers(response)
        
        # Validate context structure
        try:
            validate_context(context)
            print(f"[LLM FEEDBACK] Context validation passed")
        except KeyError as e:
            print(f"[LLM FEEDBACK] Context validation failed: {e}")
            response = JsonResponse({
                "error": f"Invalid context structure: {str(e)}",
                "generation_status": "error"
            }, status=400)
            return add_cors_headers(response)
        
        # Build prompts
        try:
            print(f"[LLM FEEDBACK] Building prompts...")
            prompts = build_prompts(context, technique_name=technique_name)
            system_prompt = prompts['system']
            instruction_prompt = prompts['instruction']
            print(f"[LLM FEEDBACK] Prompts built successfully")
        except Exception as e:
            print(f"[LLM FEEDBACK] Error building prompts: {e}")
            response = JsonResponse({
                "error": f"Failed to build prompts: {str(e)}",
                "generation_status": "error"
            }, status=500)
            return add_cors_headers(response)
        
        # Generate feedback via LLM
        print(f"[LLM FEEDBACK] Generating feedback via LLM...")
        result = generate_feedback(system_prompt, instruction_prompt)
        print(f"[LLM FEEDBACK] Generation status: {result.get('generation_status')}")
        
        # Check generation status
        if result['generation_status'] == 'error':
            response = JsonResponse({
                "error": result.get('error_message', 'Unknown LLM error'),
                "model_used": result.get('model_used', 'unknown'),
                "generation_status": "error"
            }, status=500)
            return add_cors_headers(response)
        
        # Return successful response
        response = JsonResponse({
            "feedback_text": result['feedback_text'],
            "model_used": result['model_used'],
            "generation_status": "success"
        })
        return add_cors_headers(response)
    
    except json.JSONDecodeError:
        response = JsonResponse({
            "error": "Invalid JSON in request body",
            "generation_status": "error"
        }, status=400)
        return add_cors_headers(response)
    
    except Exception as e:
        # Catch-all for unexpected errors (no stack trace to user)
        response = JsonResponse({
            "error": "Internal server error",
            "generation_status": "error"
        }, status=500)
        return add_cors_headers(response)


@require_http_methods(["GET", "OPTIONS"])
def llm_health_check(request):
    """
    Check if LLM service is available.
    """
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'ok'})
        return add_cors_headers(response)
    
    from llm_feedback.llm_client import LLMClient
    from llm_feedback.config import get_llm_config
    
    try:
        config = get_llm_config()
        client = LLMClient(config)
        
        # Try a simple test prompt
        test_result = client.generate(
            system_prompt="You are a helpful assistant.",
            instruction_prompt="Say 'OK' if you can read this."
        )
        
        if test_result['generation_status'] == 'success':
            response = JsonResponse({
                "status": "healthy",
                "message": f"LLM service ({config['model']}) is responsive",
                "model": config['model'],
                "endpoint": config['endpoint']
            })
            return add_cors_headers(response)
        else:
            response = JsonResponse({
                "status": "unhealthy",
                "message": test_result.get('error_message', 'LLM failed to respond'),
                "model": config['model'],
                "endpoint": config['endpoint']
            }, status=503)
            return add_cors_headers(response)
    
    except Exception as e:
        response = JsonResponse({
            "status": "unhealthy",
            "message": str(e)
        }, status=503)
        return add_cors_headers(response)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def raw_feedback_view(request):
    """
    Generate RAW LLM feedback WITHOUT any context or prompt engineering.
    
    This endpoint sends a generic kabaddi coaching question to the LLM
    without any performance data, system prompt, or instruction template.
    Used to demonstrate the difference between prompt-engineered vs raw output.
    """
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'ok'})
        return add_cors_headers(response)
    
    try:
        print(f"[RAW LLM] Received request for raw (no-context) feedback")
        
        # Generic prompt - no context, no system prompt engineering
        raw_prompt = "Give me feedback on my kabaddi raid technique."
        
        # Call LLM with minimal/generic prompts
        result = generate_feedback(
            system_prompt="You are an assistant.",
            instruction_prompt=raw_prompt
        )
        
        print(f"[RAW LLM] Generation status: {result.get('generation_status')}")
        
        if result['generation_status'] == 'error':
            response = JsonResponse({
                "error": result.get('error_message', 'Unknown LLM error'),
                "model_used": result.get('model_used', 'unknown'),
                "generation_status": "error"
            }, status=500)
            return add_cors_headers(response)
        
        response = JsonResponse({
            "feedback_text": result['feedback_text'],
            "model_used": result['model_used'],
            "generation_status": "success",
            "mode": "raw"
        })
        return add_cors_headers(response)
    
    except Exception as e:
        print(f"[RAW LLM] Error: {e}")
        response = JsonResponse({
            "error": "Internal server error",
            "generation_status": "error"
        }, status=500)
        return add_cors_headers(response)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def compare_feedback_view(request):
    """
    Generate BOTH prompt-engineered and raw LLM feedback,
    then compute automated quality metrics for comparison.
    """
    
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'ok'})
        return add_cors_headers(response)
    
    try:
        from llm_feedback.feedback_metrics import compute_all_metrics
        
        body = json.loads(request.body)
        session_id = body.get('session_id')
        technique_name = body.get('technique_name', 'Unknown Technique')
        
        print(f"[COMPARE] Starting comparison for session: {session_id}")
        
        # --- Load context ---
        context_path = Path(__file__).parent.parent / 'data' / 'results' / session_id / 'context.json'
        if not context_path.exists():
            response = JsonResponse({
                "error": f"Context not found for session: {session_id}",
                "generation_status": "error"
            }, status=404)
            return add_cors_headers(response)
        
        with open(context_path, 'r') as f:
            context = json.load(f)
        
        # --- Generate ENGINEERED response ---
        print(f"[COMPARE] Generating prompt-engineered response...")
        prompts = build_prompts(context, technique_name=technique_name)
        engineered_result = generate_feedback(prompts['system'], prompts['instruction'])
        
        if engineered_result['generation_status'] == 'error':
            response = JsonResponse({
                "error": "Engineered feedback generation failed: " + engineered_result.get('error_message', ''),
                "generation_status": "error"
            }, status=500)
            return add_cors_headers(response)
        
        # --- Generate RAW response ---
        print(f"[COMPARE] Generating raw (no-context) response...")
        raw_result = generate_feedback(
            system_prompt="You are an assistant.",
            instruction_prompt="Give me feedback on my kabaddi raid technique."
        )
        
        if raw_result['generation_status'] == 'error':
            response = JsonResponse({
                "error": "Raw feedback generation failed: " + raw_result.get('error_message', ''),
                "generation_status": "error"
            }, status=500)
            return add_cors_headers(response)
        
        # --- Compute metrics for both ---
        print(f"[COMPARE] Computing metrics...")
        engineered_metrics = compute_all_metrics(
            engineered_result['feedback_text'], context, technique_name
        )
        raw_metrics = compute_all_metrics(
            raw_result['feedback_text'], context, technique_name
        )
        
        print(f"[COMPARE] Engineered score: {engineered_metrics['overall_percentage']}%")
        print(f"[COMPARE] Raw score: {raw_metrics['overall_percentage']}%")
        
        response = JsonResponse({
            "generation_status": "success",
            "engineered": {
                "feedback_text": engineered_result['feedback_text'],
                "model_used": engineered_result['model_used'],
                "metrics": engineered_metrics
            },
            "raw": {
                "feedback_text": raw_result['feedback_text'],
                "model_used": raw_result['model_used'],
                "metrics": raw_metrics
            },
            "technique_name": technique_name
        })
        return add_cors_headers(response)
    
    except Exception as e:
        print(f"[COMPARE] Error: {e}")
        import traceback
        traceback.print_exc()
        response = JsonResponse({
            "error": "Internal server error",
            "generation_status": "error"
        }, status=500)
        return add_cors_headers(response)

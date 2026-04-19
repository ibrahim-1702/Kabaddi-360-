# Django Integration - Quick Start Guide

## Step 1: Update Main URLs

Add to `kabaddi_trainer/urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # Existing routes...
    
    # LLM Feedback routes
    path('llm_feedback/', include('llm_feedback.urls')),
]
```

## Step 2: Ensure Context Generation

In your pipeline runner, after generating `results.json`:

```python
from llm_feedback import generate_context, save_context

# After pipeline execution
results = run_pipeline(...)
results_dir = Path('data/results') / session_id

# Save results
save_results(results, results_dir / 'results.json')

# Generate and save context
context = generate_context(results)
save_context(context, results_dir / 'context.json')
```

## Step 3: Update Results View

Ensure your results view passes `session_id` to template:

```python
def results_view(request, session_id):
    # Existing code...
    
    context = {
        'session_id': session_id,
        'scores': scores,
        # ... other variables
    }
    
    return render(request, 'results.html', context)
```

## Step 4: Add HTML to Results Template

Copy content from `llm_feedback/templates/feedback_section.html` to your results template where you want the feedback section to appear (typically below the scores section).

## Step 5: Start Ollama

```bash
# Start Ollama server
ollama serve

# Pull model (if not already done)
ollama pull mistral
```

## Step 6: Test

1. Run Django server: `python manage.py runserver`
2. Upload a pose and view results
3. Click "Generate AI Feedback"
4. Feedback should appear within 5-10 seconds

## Troubleshooting

**"Context file not found"**
- Ensure Context Engine is running after pipeline
- Check that `data/results/{session_id}/context.json` exists

**"Could not connect to Ollama"**
- Start Ollama: `ollama serve`
- Check it's running on `http://localhost:11434`

**"Request timed out"**
- Increase `LLM_TIMEOUT` in `llm_feedback/config.py`
- Default is 30 seconds

**Feedback not displaying**
- Check browser console for JavaScript errors
- Verify `session_id` is passed to template
- Check Django logs for API errors

## API Endpoints

**Generate Feedback**
```
POST /llm_feedback/generate/
Body: {"session_id": "..."}
```

**Health Check**
```
GET /llm_feedback/health/
```

## File Structure

```
llm_feedback/
├── urls.py                              # NEW - URL routing
├── views.py                             # UPDATED - Session support
├── static/
│   └── feedback_integration.js          # NEW - Frontend JS
└── templates/
    └── feedback_section.html            # NEW - HTML template
```

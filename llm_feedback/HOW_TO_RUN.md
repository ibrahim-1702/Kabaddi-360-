# How to Run the LLM Feedback System

## Prerequisites

### 1. Install Ollama (if not already installed)

**Windows**:
```bash
# Download and install from: https://ollama.ai/download
# Or use winget:
winget install Ollama.Ollama
```

**Linux/Mac**:
```bash
curl https://ollama.ai/install.sh | sh
```

### 2. Pull an LLM Model

```bash
# Pull mistral (recommended, ~4GB)
ollama pull mistral

# OR pull gemma (lighter, ~2GB)
ollama pull gemma

# OR pull llama2
ollama pull llama2
```

### 3. Start Ollama Server

```bash
ollama serve
```

**Note**: Keep this terminal window open. Ollama runs on `http://localhost:11434`

---

## Option 1: Standalone Testing (No Django)

Test the LLM system with existing context data.

### Step 1: Verify Context File Exists

```bash
# Check if you have a context.json from a previous session
dir "data\results\039ae972-178d-4520-86ff-b7c9b02d5d6b\context.json"
```

### Step 2: Test Prompt Builder

```bash
cd "C:\Users\msibr\Documents\MCA\SEM 4\Project\kabaddi_trainer"

python -c "
from llm_feedback import build_prompts
import json

# Load context
with open('data/results/039ae972-178d-4520-86ff-b7c9b02d5d6b/context.json') as f:
    context = json.load(f)

# Build prompts
prompts = build_prompts(context)

print('System Prompt:')
print(prompts['system'][:200] + '...')
print('\nInstruction Prompt:')
print(prompts['instruction'][:500] + '...')
"
```

### Step 3: Test Full Pipeline (Context → Feedback)

```bash
python -c "
from llm_feedback import build_prompts, generate_feedback
import json

# Load context
with open('data/results/039ae972-178d-4520-86ff-b7c9b02d5d6b/context.json') as f:
    context = json.load(f)

# Build prompts
prompts = build_prompts(context)

# Generate feedback
print('Generating feedback (this may take 10-30 seconds)...\n')
result = generate_feedback(prompts['system'], prompts['instruction'])

if result['generation_status'] == 'success':
    print('=== FEEDBACK ===')
    print(result['feedback_text'])
    print(f'\nModel used: {result["model_used"]}')
else:
    print('ERROR:', result.get('error_message'))
"
```

### Step 4: Test with Different Session

```bash
# Replace SESSION_ID with your actual session ID
python -c "
from llm_feedback import build_prompts, generate_feedback
import json
from pathlib import Path

session_id = 'YOUR_SESSION_ID_HERE'
context_path = Path('data/results') / session_id / 'context.json'

if not context_path.exists():
    print(f'Context not found: {context_path}')
    exit(1)

with open(context_path) as f:
    context = json.load(f)

prompts = build_prompts(context)
result = generate_feedback(prompts['system'], prompts['instruction'])

print(result['feedback_text'])
"
```

---

## Option 2: Full Django Integration

Run the complete web application with AI feedback.

### Step 1: Update Main URLs

Edit `kabaddi_trainer/urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # Your existing routes...
    
    # Add this line:
    path('llm_feedback/', include('llm_feedback.urls')),
]
```

### Step 2: Update Results Template

Add to your results template (e.g., `templates/results.html` or wherever you display results):

```html
<!-- Add this at the end of your results section -->

<!-- AI Feedback Section -->
<div class="feedback-container" style="margin-top: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
    <h3>AI Coaching Feedback</h3>
    
    <button 
        id="generate-feedback-btn" 
        onclick="generateAIFeedback('{{ session_id }}')"
        style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">
        Generate AI Feedback
    </button>
    
    <div id="ai-loading" style="display: none; color: #1976d2; margin-top: 10px;">
        🔄 Generating personalized feedback...
    </div>
    
    <div id="ai-error" style="display: none; color: #d32f2f; background: #ffebee; padding: 10px; border-radius: 4px; margin-top: 10px;"></div>
    
    <div id="ai-feedback-section" style="display: none;">
        <div style="background: #f9f9f9; padding: 20px; border-left: 4px solid #007bff; margin-top: 15px; line-height: 1.6;">
            <p id="ai-feedback-text" style="white-space: pre-wrap;"></p>
        </div>
    </div>
</div>

<script>
async function generateAIFeedback(sessionId) {
    const feedbackSection = document.getElementById('ai-feedback-section');
    const feedbackText = document.getElementById('ai-feedback-text');
    const loadingIndicator = document.getElementById('ai-loading');
    const errorMessage = document.getElementById('ai-error');
    const generateButton = document.getElementById('generate-feedback-btn');
    
    loadingIndicator.style.display = 'block';
    errorMessage.style.display = 'none';
    feedbackText.style.display = 'none';
    generateButton.disabled = true;
    generateButton.textContent = 'Generating...';
    
    try {
        const response = await fetch('/llm_feedback/generate/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        
        const data = await response.json();
        
        if (data.generation_status === 'success') {
            feedbackText.textContent = data.feedback_text;
            feedbackText.style.display = 'block';
            feedbackSection.style.display = 'block';
            generateButton.textContent = 'Regenerate Feedback';
        } else {
            errorMessage.textContent = data.error || 'Failed to generate feedback';
            errorMessage.style.display = 'block';
            generateButton.textContent = 'Generate AI Feedback';
        }
    } catch (error) {
        errorMessage.textContent = 'Network error. Please check if Ollama is running.';
        errorMessage.style.display = 'block';
        generateButton.textContent = 'Generate AI Feedback';
    } finally {
        loadingIndicator.style.display = 'none';
        generateButton.disabled = false;
    }
}
</script>
```

### Step 3: Ensure Context Generation

Update your pipeline to generate `context.json` after `results.json`.

If you're using `pipeline_runner.py`, add this after saving results:

```python
from llm_feedback import generate_context, save_context

# After your pipeline runs and saves results.json
results_path = Path('data/results') / session_id / 'results.json'
context_path = Path('data/results') / session_id / 'context.json'

# Load results
with open(results_path) as f:
    results = json.load(f)

# Generate context
context = generate_context(results)

# Save context
save_context(context, context_path)
```

### Step 4: Start Django Server

```bash
cd "C:\Users\msibr\Documents\MCA\SEM 4\Project\kabaddi_trainer"

# Start Django
python manage.py runserver
```

### Step 5: Test the System

1. **Upload a pose** via the web interface
2. **View results** page
3. **Click "Generate AI Feedback"** button
4. **Wait 10-30 seconds** for feedback to appear

---

## Testing Health Check

### Command Line Test

```bash
curl http://localhost:8000/llm_feedback/health/
```

**Expected Output**:
```json
{
  "status": "healthy",
  "message": "LLM service (mistral) is responsive",
  "model": "mistral",
  "endpoint": "http://localhost:11434/api/generate"
}
```

### Browser Test

Navigate to: `http://localhost:8000/llm_feedback/health/`

---

## Quick Test Script

Save this as `test_llm_feedback.py`:

```python
#!/usr/bin/env python3
"""
Quick test script for LLM Feedback System
"""

from llm_feedback import build_prompts, generate_feedback
import json
from pathlib import Path

def test_feedback(session_id):
    """Test feedback generation for a session"""
    
    # Find context file
    context_path = Path('data/results') / session_id / 'context.json'
    
    if not context_path.exists():
        print(f"❌ Context file not found: {context_path}")
        return False
    
    print(f"✅ Found context file: {context_path}")
    
    # Load context
    with open(context_path) as f:
        context = json.load(f)
    
    print(f"✅ Loaded context: {len(str(context))} bytes")
    
    # Build prompts
    try:
        prompts = build_prompts(context)
        print(f"✅ Built prompts successfully")
    except Exception as e:
        print(f"❌ Failed to build prompts: {e}")
        return False
    
    # Generate feedback
    print(f"⏳ Generating feedback (this may take 10-30 seconds)...")
    result = generate_feedback(prompts['system'], prompts['instruction'])
    
    if result['generation_status'] == 'success':
        print(f"✅ Feedback generated successfully!")
        print(f"\n{'='*70}")
        print(f"MODEL: {result['model_used']}")
        print(f"{'='*70}")
        print(result['feedback_text'])
        print(f"{'='*70}\n")
        return True
    else:
        print(f"❌ Failed to generate feedback: {result.get('error_message')}")
        return False

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_llm_feedback.py <session_id>")
        print("Example: python test_llm_feedback.py 039ae972-178d-4520-86ff-b7c9b02d5d6b")
        sys.exit(1)
    
    session_id = sys.argv[1]
    success = test_feedback(session_id)
    sys.exit(0 if success else 1)
```

**Run it**:
```bash
python test_llm_feedback.py 039ae972-178d-4520-86ff-b7c9b02d5d6b
```

---

## Troubleshooting

### "Could not connect to Ollama"

**Cause**: Ollama server not running  
**Solution**:
```bash
ollama serve
```

### "Context file not found"

**Cause**: Context not generated for this session  
**Solution**:
```bash
python -c "
from llm_feedback import generate_context, load_raw_scores, save_context

# Generate context from results.json
results = load_raw_scores('data/results/YOUR_SESSION_ID/results.json')
context = generate_context(results)
save_context(context, 'data/results/YOUR_SESSION_ID/context.json')
"
```

### "Request timed out"

**Cause**: LLM taking too long  
**Solution**: Edit `llm_feedback/config.py`:
```python
LLM_TIMEOUT = 60  # Increase from 30 to 60 seconds
```

### Button does nothing

**Cause**: JavaScript error  
**Solution**:
1. Open browser console (F12)
2. Check for errors
3. Verify `session_id` is available in template

### Feedback looks wrong

**Cause**: Context might be invalid  
**Solution**: Regenerate context:
```bash
python verify_context_engine.py
```

---

## Summary

**For Quick Testing**:
```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Test feedback generation
python test_llm_feedback.py 039ae972-178d-4520-86ff-b7c9b02d5d6b
```

**For Full Web App**:
```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start Django
python manage.py runserver

# Browser: http://localhost:8000 → Upload → View Results → Click "Generate AI Feedback"
```

---

## Expected Timeline

- **Ollama model download**: 1-5 minutes (one-time)
- **Ollama startup**: 5-10 seconds
- **Feedback generation**: 10-30 seconds per request
- **Context generation**: <1 second

Total from fresh install to first feedback: **~10 minutes**

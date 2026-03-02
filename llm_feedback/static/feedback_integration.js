/**
 * LLM Feedback Integration - Frontend JavaScript
 * 
 * Add this to your results page template to enable AI feedback generation.
 * 
 * Prerequisites:
 * - Django view must pass `session_id` to template
 * - HTML elements with IDs must exist (see feedback_section.html)
 */

async function generateAIFeedback(sessionId) {
    // Get DOM elements
    const feedbackSection = document.getElementById('ai-feedback-section');
    const feedbackText = document.getElementById('ai-feedback-text');
    const loadingIndicator = document.getElementById('ai-loading');
    const errorMessage = document.getElementById('ai-error');
    const generateButton = document.getElementById('generate-feedback-btn');
    
    // Show loading state
    loadingIndicator.classList.remove('hidden');
    errorMessage.classList.add('hidden');
    feedbackText.classList.add('hidden');
    generateButton.disabled = true;
    generateButton.textContent = 'Generating...';
    
    try {
        // Call Django API
        const response = await fetch('/llm_feedback/generate/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId
            })
        });
        
        const data = await response.json();
        
        if (data.generation_status === 'success') {
            // Display feedback
            feedbackText.textContent = data.feedback_text;
            feedbackText.classList.remove('hidden');
            feedbackSection.classList.remove('hidden');
            
            // Update button text
            generateButton.textContent = 'Regenerate Feedback';
        } else {
            // Display error message
            errorMessage.textContent = data.error || 'Failed to generate feedback';
            errorMessage.classList.remove('hidden');
            
            // Reset button
            generateButton.textContent = 'Generate AI Feedback';
        }
    } catch (error) {
        // Network or parsing error
        console.error('Feedback generation error:', error);
        errorMessage.textContent = 'Network error. Please check if Ollama is running.';
        errorMessage.classList.remove('hidden');
        
        // Reset button
        generateButton.textContent = 'Generate AI Feedback';
    } finally {
        // Hide loading state
        loadingIndicator.classList.add('hidden');
        generateButton.disabled = false;
    }
}

/**
 * Optional: Check LLM health status on page load
 */
async function checkLLMHealth() {
    try {
        const response = await fetch('/llm_feedback/health/');
        const data = await response.json();
        
        if (data.status === 'healthy') {
            console.log('✅ LLM service is available:', data.model);
        } else {
            console.warn('⚠️ LLM service is unavailable:', data.message);
        }
    } catch (error) {
        console.warn('⚠️ Could not check LLM health:', error);
    }
}

// Optional: Check health on page load
// document.addEventListener('DOMContentLoaded', checkLLMHealth);

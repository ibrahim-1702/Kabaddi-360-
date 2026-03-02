"""
LLM Feedback System - LLM Client

This module handles communication with the local LLM via Ollama HTTP API.

Responsibilities:
- Call Ollama API with system + instruction prompts
- Handle streaming or aggregated responses
- Timeout and error handling
- Return generated feedback text

Design:
- Framework-agnostic (no Django dependencies)
- Configurable model and endpoint
- Safe error handling (no stack traces to user)
"""

import requests
import json
from typing import Dict, Optional
from llm_feedback.config import get_llm_config


# ============================================================================
# LLM CLIENT
# ============================================================================

class LLMClient:
    """
    Client for calling local LLM via Ollama API.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize LLM client.
        
        Args:
            config: Optional config override. If None, uses config.py defaults.
        """
        self.config = config or get_llm_config()
        self.endpoint = self.config['endpoint']
        self.model = self.config['model']
        self.temperature = self.config['temperature']
        self.max_tokens = self.config['max_tokens']
        self.timeout = self.config['timeout']
        self.stream = self.config['stream']
    
    def generate(self, system_prompt: str, instruction_prompt: str) -> Dict:
        """
        Generate feedback using LLM.
        
        Args:
            system_prompt: System prompt defining LLM role and constraints
            instruction_prompt: Instruction prompt with context fields injected
            
        Returns:
            Dictionary with:
                - feedback_text: Generated feedback (str)
                - model_used: Model name (str)
                - generation_status: "success" or "error" (str)
                - error_message: Error details if status is "error" (optional)
        """
        try:
            print(f"[LLM CLIENT] Preparing request...")
            print(f"[LLM CLIENT] Endpoint: {self.endpoint}")
            print(f"[LLM CLIENT] Model: {self.model}")
            
            # Combine prompts according to Ollama format
            # Some models expect system prompt separately, others inline
            combined_prompt = f"{system_prompt}\n\n{instruction_prompt}"
            
            # Build request payload
            payload = {
                "model": self.model,
                "prompt": combined_prompt,
                "stream": self.stream,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens
                }
            }
            
            print(f"[LLM CLIENT] Sending request to Ollama...")
            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=self.timeout
            )
            
            print(f"[LLM CLIENT] Response status: {response.status_code}")
            
            # Check HTTP status
            if response.status_code != 200:
                error_detail = response.text[:200] if response.text else "No error details"
                print(f"[LLM CLIENT] Error response: {error_detail}")
                return {
                    "feedback_text": "",
                    "model_used": self.model,
                    "generation_status": "error",
                    "error_message": f"HTTP {response.status_code}: {error_detail}"
                }
            
            # Parse response
            if self.stream:
                # Aggregate streaming response
                feedback_text = self._aggregate_stream(response)
            else:
                # Parse single response
                result = response.json()
                feedback_text = result.get('response', '').strip()
            
            # Validate output
            if not feedback_text:
                return {
                    "feedback_text": "",
                    "model_used": self.model,
                    "generation_status": "error",
                    "error_message": "LLM returned empty response"
                }
            
            return {
                "feedback_text": feedback_text,
                "model_used": self.model,
                "generation_status": "success"
            }
        
        except requests.exceptions.Timeout:
            return {
                "feedback_text": "",
                "model_used": self.model,
                "generation_status": "error",
                "error_message": f"Request timed out after {self.timeout}s"
            }
        
        except requests.exceptions.ConnectionError:
            return {
                "feedback_text": "",
                "model_used": self.model,
                "generation_status": "error",
                "error_message": "Could not connect to Ollama. Is it running?"
            }
        
        except Exception as e:
            return {
                "feedback_text": "",
                "model_used": self.model,
                "generation_status": "error",
                "error_message": f"Unexpected error: {str(e)[:200]}"
            }
    
    def _aggregate_stream(self, response: requests.Response) -> str:
        """
        Aggregate streaming response from Ollama.
        
        Args:
            response: Streaming HTTP response
            
        Returns:
            Complete aggregated response text
        """
        aggregated = []
        
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    if 'response' in chunk:
                        aggregated.append(chunk['response'])
                    
                    # Check if done
                    if chunk.get('done', False):
                        break
                
                except json.JSONDecodeError:
                    continue
        
        return ''.join(aggregated).strip()


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def generate_feedback(system_prompt: str, instruction_prompt: str, 
                     config: Optional[Dict] = None) -> Dict:
    """
    Convenience function for generating feedback.
    
    Args:
        system_prompt: System prompt
        instruction_prompt: Instruction prompt with context
        config: Optional config override
        
    Returns:
        Generation result dictionary (see LLMClient.generate)
    """
    client = LLMClient(config=config)
    return client.generate(system_prompt, instruction_prompt)


if __name__ == "__main__":
    print("LLM Client Module")
    print("=" * 70)
    print("\nThis module handles communication with local LLM via Ollama API.")
    print("\nUsage:")
    print("  from llm_feedback.llm_client import generate_feedback")
    print("  result = generate_feedback(system_prompt, instruction_prompt)")
    print("\nRequires:")
    print("  - Ollama running locally (http://localhost:11434)")
    print("  - Model downloaded (e.g., 'ollama pull mistral')")

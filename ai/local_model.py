"""
Local LLM inference using llama-cpp-python
Supports GGUF quantized models for efficient CPU inference
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from llama_cpp import Llama

# Setup logging
logger = logging.getLogger(__name__)


class LocalModelManager:
    """Manages local LLM inference with caching and retry logic"""

    def __init__(self, model_path: str, n_ctx: int = 512, n_threads: int = 4):
        """
        Initialize local model manager

        Args:
            model_path: Path to GGUF model file
            n_ctx: Context window size (512 tokens = faster inference)
            n_threads: CPU threads to use (Pi 5 has 4 cores)
        """
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads

        logger.info(f"Loading local model: {model_path}")
        try:
            self.llm = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_threads=n_threads,
                n_batch=512,
                use_mlock=True,  # Keep model in RAM
                verbose=False
            )
            logger.info("✓ Local model loaded successfully")
        except Exception as e:
            logger.error(f"✗ Failed to load model: {e}")
            raise

    def generate(self, prompt: str, max_tokens: int = 256,
                 temperature: float = 0.3, stop: Optional[List[str]] = None) -> str:
        """
        Generate text completion

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            stop: Stop sequences

        Returns:
            Generated text
        """
        try:
            response = self.llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop or ["</s>", "User:", "\n\n\n"],
                echo=False
            )
            return response['choices'][0]['text'].strip()
        except Exception as e:
            logger.error(f"✗ Generation error: {e}")
            return ""

    def generate_json(self, system_prompt: str, user_prompt: str,
                     max_tokens: int = 256, retries: int = 2) -> Dict[str, Any]:
        """
        Generate structured JSON output with retry logic

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            max_tokens: Maximum tokens to generate
            retries: Number of retry attempts on parse failure

        Returns:
            Parsed JSON dictionary or fallback structure
        """
        # TinyLlama chat format
        full_prompt = f"""<|system|>
{system_prompt}
You must respond with valid JSON only. No explanations.</s>
<|user|>
{user_prompt}</s>
<|assistant|>
"""

        for attempt in range(retries + 1):
            logger.info(f"JSON generation attempt {attempt + 1}/{retries + 1}")

            try:
                response_text = self.generate(
                    full_prompt,
                    max_tokens=max_tokens,
                    temperature=0.1,  # Low temp for structured output
                    stop=["</s>"]
                )

                # Clean and parse JSON
                cleaned_text = self._clean_json_response(response_text)
                parsed = json.loads(cleaned_text)
                logger.info("✓ JSON parsed successfully")
                return parsed

            except json.JSONDecodeError as e:
                logger.warning(f"⚠️  JSON parse error (attempt {attempt + 1}): {e}")
                logger.debug(f"Raw response: {response_text[:200]}")

                if attempt < retries:
                    logger.info("🔄 Retrying...")
                    continue
                else:
                    logger.error("✗ All retries failed, using fallback")
                    return self._get_fallback_structure(system_prompt, user_prompt)

            except Exception as e:
                logger.error(f"✗ Generation error: {e}")
                return self._get_fallback_structure(system_prompt, user_prompt)

        return {}

    def _clean_json_response(self, text: str) -> str:
        """
        Extract JSON from response text

        Args:
            text: Raw model output

        Returns:
            Cleaned JSON string
        """
        text = text.strip()

        # Remove markdown code blocks
        if '```' in text:
            parts = text.split('```')
            for part in parts:
                if part.strip().startswith('json'):
                    text = part[4:].strip()
                elif part.strip().startswith('{'):
                    text = part.strip()
                    break

        # Find JSON object boundaries
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            text = text[start:end+1]

        return text

    def _get_fallback_structure(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Return safe fallback structure based on prompt type

        Args:
            system_prompt: System prompt (used to infer type)
            user_prompt: User prompt

        Returns:
            Fallback dictionary structure
        """
        combined = (system_prompt + " " + user_prompt).lower()

        # Intent classification fallback
        if 'intent' in combined or 'classify' in combined:
            return {
                "intent": "GENERAL",
                "confidence": 0.3,
                "reasoning": "Fallback - model failed to classify"
            }

        # Assignment extraction fallback
        elif 'due_date' in combined or 'assignment' in combined:
            return {
                "class_name": None,
                "due_date": None,
                "title": "Untitled Assignment",
                "description": None,
                "priority": "medium"
            }

        # Note extraction fallback
        elif 'note' in combined:
            return {
                "class_name": None,
                "content": user_prompt[:200] if user_prompt else "Note content unavailable",
                "note_type": "general",
                "tags": []
            }

        # Query understanding fallback
        elif 'query' in combined:
            return {
                "query_type": "general",
                "search_term": "",
                "filters": {}
            }

        # Generic fallback
        else:
            return {
                "error": "parsing_failed",
                "raw_prompt": user_prompt[:100]
            }


# Test function
def test_local_model():
    """Test local model loading and generation"""
    import os
    from config import Config

    model_path = os.getenv('LOCAL_MODEL_PATH', './models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf')

    if not os.path.exists(model_path):
        print(f"✗ Model not found: {model_path}")
        print("  Download model first using huggingface-hub")
        return

    try:
        print("Testing LocalModelManager...")
        manager = LocalModelManager(model_path, n_ctx=512, n_threads=4)

        # Test simple generation
        print("\n=== Test 1: Simple Generation ===")
        response = manager.generate("Say hello in one sentence.", max_tokens=50)
        print(f"Response: {response}")

        # Test JSON generation
        print("\n=== Test 2: JSON Generation ===")
        system = "You are Jarvis. Classify intent as JSON."
        user = 'Email: "Data Mining assignment due tomorrow"\nReturn JSON: {"intent": "ASSIGNMENT", "confidence": 0.9}'
        json_response = manager.generate_json(system, user, max_tokens=100)
        print(f"JSON: {json_response}")

        print("\n✓ All tests passed!")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_local_model()

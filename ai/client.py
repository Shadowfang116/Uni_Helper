"""
AI client initialization
Supports Anthropic Claude, OpenAI GPT-4, and local LLMs via llama-cpp
"""

import os
from typing import Optional, Dict, Any
from config import Config


class AIClient:
    """Unified AI client supporting Claude, OpenAI, and local models"""

    def __init__(self, provider: Optional[str] = None):
        """
        Initialize AI client

        Args:
            provider: 'claude', 'openai', or 'local' (defaults to Config.AI_PROVIDER)
        """
        self.provider = provider or Config.AI_PROVIDER

        if self.provider == 'claude':
            self._init_claude()
        elif self.provider == 'openai':
            self._init_openai()
        elif self.provider == 'local':
            self._init_local()
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")

    def _init_claude(self):
        """Initialize Anthropic Claude client"""
        try:
            from anthropic import Anthropic

            if not Config.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not set in environment")

            self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
            self.model = "claude-3-5-sonnet-20241022"  # Latest Claude model
            print(f"✓ Initialized Claude AI client (model: {self.model})")

        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

    def _init_openai(self):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI

            if not Config.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set in environment")

            self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
            self.model = "gpt-4o"  # GPT-4o (latest)
            print(f"✓ Initialized OpenAI client (model: {self.model})")

        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    def _init_local(self):
        """Initialize local LLM client"""
        try:
            from ai.local_model import LocalModelManager

            if not hasattr(Config, 'LOCAL_MODEL_PATH') or not Config.LOCAL_MODEL_PATH:
                raise ValueError("LOCAL_MODEL_PATH not set in environment")

            if not os.path.exists(Config.LOCAL_MODEL_PATH):
                raise FileNotFoundError(f"Model not found: {Config.LOCAL_MODEL_PATH}")

            n_threads = getattr(Config, 'LOCAL_MODEL_THREADS', 4)
            self.client = LocalModelManager(
                model_path=Config.LOCAL_MODEL_PATH,
                n_threads=n_threads
            )
            self.model = "tinyllama-1.1b-chat"
            print(f"✓ Initialized local AI client (model: {self.model})")

        except ImportError:
            raise ImportError("llama-cpp-python not installed. Run: pip install llama-cpp-python")

    def generate(self, system_prompt: str, user_prompt: str,
                 max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """
        Generate AI response

        Args:
            system_prompt: System prompt (personality/instructions)
            user_prompt: User prompt (actual query)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            Generated text response
        """
        try:
            if self.provider == 'claude':
                return self._generate_claude(system_prompt, user_prompt, max_tokens, temperature)
            elif self.provider == 'openai':
                return self._generate_openai(system_prompt, user_prompt, max_tokens, temperature)
            elif self.provider == 'local':
                return self._generate_local(system_prompt, user_prompt, max_tokens, temperature)
        except Exception as e:
            print(f"✗ AI generation error: {e}")
            raise

    def _generate_claude(self, system_prompt: str, user_prompt: str,
                        max_tokens: int, temperature: float) -> str:
        """Generate response using Claude"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.content[0].text

    def _generate_openai(self, system_prompt: str, user_prompt: str,
                        max_tokens: int, temperature: float) -> str:
        """Generate response using OpenAI"""
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.choices[0].message.content

    def _generate_local(self, system_prompt: str, user_prompt: str,
                       max_tokens: int, temperature: float) -> str:
        """Generate response using local model"""
        # Combine prompts for local model
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        return self.client.generate(full_prompt, max_tokens, temperature)

    def generate_json(self, system_prompt: str, user_prompt: str,
                     max_tokens: int = 1024) -> Dict[str, Any]:
        """
        Generate JSON response (for structured data extraction)

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            max_tokens: Maximum tokens

        Returns:
            Parsed JSON dictionary
        """
        import json

        # Local model uses native generate_json with retry logic
        if self.provider == 'local':
            return self.client.generate_json(system_prompt, user_prompt, max_tokens)

        # Cloud providers use standard generate with post-processing
        # Add JSON formatting instruction
        json_instruction = "\n\nIMPORTANT: Return ONLY valid JSON. No explanation, no markdown formatting."
        full_system = system_prompt + json_instruction

        response_text = self.generate(
            full_system,
            user_prompt,
            max_tokens=max_tokens,
            temperature=0.3  # Lower temp for structured output
        )

        # Clean response (remove markdown code blocks if present)
        response_text = response_text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]

        response_text = response_text.strip()

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"✗ Failed to parse JSON response: {e}")
            print(f"  Raw response: {response_text}")
            raise


def test_client():
    """Test AI client"""
    from config import Config

    print("Testing AI client...")

    if not Config.is_configured():
        print("✗ Configuration errors:")
        for error in Config.validate():
            print(f"  - {error}")
        return

    try:
        client = AIClient()

        # Test simple generation
        system = "You are Jarvis, a helpful AI assistant."
        user = "Say hello in one sentence."

        print("\nTesting AI generation...")
        response = client.generate(system, user, max_tokens=100)
        print(f"Response: {response}")

        # Test JSON generation
        print("\nTesting JSON generation...")
        system_json = "You are a JSON generator."
        user_json = 'Return JSON: {"status": "ok", "message": "test"}'

        json_response = client.generate_json(system_json, user_json, max_tokens=100)
        print(f"JSON Response: {json_response}")

        print("\n✓ AI client test complete!")

    except Exception as e:
        print(f"\n✗ AI client test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_client()

"""
LLM Provider Module
Supports Anthropic Claude and HuggingFace Inference APIs.
"""
import httpx
import json
import re
from ..config import settings


class LLMProvider:
    """Unified interface for LLM text generation."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.client = httpx.AsyncClient(timeout=60.0)

    async def generate(self, system_prompt: str, messages: list[dict]) -> str:
        """Generate text using configured LLM provider."""
        if self.provider == "anthropic":
            return await self._call_anthropic(system_prompt, messages)
        elif self.provider == "huggingface":
            return await self._call_huggingface(system_prompt, messages)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    async def _call_anthropic(self, system_prompt: str, messages: list[dict]) -> str:
        """Call Anthropic Claude API."""
        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set. Set it in your environment.")

        # Filter out system messages from the messages list
        api_messages = []
        for msg in messages:
            if msg["role"] != "system":
                api_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # Ensure messages alternate properly and start with user
        if not api_messages or api_messages[0]["role"] != "user":
            api_messages.insert(0, {"role": "user", "content": "Hello"})

        payload = {
            "model": settings.ANTHROPIC_MODEL,
            "max_tokens": 2048,
            "system": system_prompt,
            "messages": api_messages
        }

        response = await self.client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json=payload
        )

        if response.status_code != 200:
            error_body = response.text
            raise Exception(f"Anthropic API error ({response.status_code}): {error_body}")

        data = response.json()
        return data["content"][0]["text"]

    async def _call_huggingface(self, system_prompt: str, messages: list[dict]) -> str:
        """Call HuggingFace Router API (OpenAI-compatible chat completions)."""
        api_key = settings.HF_API_KEY
        if not api_key:
            raise ValueError("HF_API_KEY not set. Set it in your environment.")

        # Build OpenAI-compatible messages array
        api_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            if msg["role"] != "system":
                api_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        response = await self.client.post(
            f"{settings.HF_API_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": settings.HF_MODEL,
                "messages": api_messages,
                "max_tokens": 2048,
                "temperature": 0.1,
                "stream": False
            }
        )

        if response.status_code != 200:
            raise Exception(f"HuggingFace API error ({response.status_code}): {response.text}")

        data = response.json()
        # OpenAI-compatible response format
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return str(data)

    def parse_sql_response(self, response: str) -> dict:
        """Parse LLM response to extract SQL and explanation."""
        sql = ""
        explanation = ""

        # Extract SQL from code block
        sql_match = re.search(r'```sql\s*(.*?)\s*```', response, re.DOTALL)
        if sql_match:
            sql = sql_match.group(1).strip()
        else:
            # Try to find SQL without code blocks
            sql_match = re.search(r'(?:SQL:|SELECT|INSERT|UPDATE|DELETE|CREATE|WITH)\s+.*?(?:;|$)', response, re.DOTALL | re.IGNORECASE)
            if sql_match:
                sql = sql_match.group(0).strip()

        # Extract explanation
        expl_match = re.search(r'EXPLANATION:\s*(.*?)(?:$)', response, re.DOTALL)
        if expl_match:
            explanation = expl_match.group(1).strip()
        else:
            # Use everything after SQL block as explanation
            parts = response.split('```')
            if len(parts) >= 3:
                explanation = parts[-1].strip()

        # Clean up SQL
        sql = sql.rstrip(';').strip() + ';' if sql else ""

        return {"sql": sql, "explanation": explanation, "raw_response": response}

    async def close(self):
        await self.client.aclose()

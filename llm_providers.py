import os
from abc import ABC, abstractmethod
from typing import Generator, List, Dict, Any, Optional

# Standard wrappers around LLM provider SDKs with graceful import error handling

class LLMProvider(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """Return provider name."""
        pass

    @abstractmethod
    def list_default_models(self) -> List[str]:
        """Return default model names."""
        pass

    @abstractmethod
    def generate_stream(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Generator[str, None, None]:
        """Stream response chunks from the LLM."""
        pass


class GeminiProvider(LLMProvider):
    def get_name(self) -> str:
        return "Google Gemini"

    def list_default_models(self) -> List[str]:
        return [
            # The current flagship Flash model (Fast, highly capable, Free Tier active)
            "gemini-3.5-flash",

            # The premium multi-step reasoning model (Best for coding and hard tasks)
            "gemini-3.1-pro",
            
            # The extreme speed / high-volume model (Highly cost-efficient)
            "gemini-3.1-flash-lite"
        ]

    def generate_stream(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Generator[str, None, None]:
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("Please install the Google Generative AI package: `pip install google-generativeai`")
        
        if not api_key:
            raise ValueError("API Key is required for Google Gemini.")
            
        genai.configure(api_key=api_key)
        
        # Format history for Gemini
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [msg["content"]]
            })
            
        # Set up generation config
        config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens
        )
        
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(contents, generation_config=config, stream=True)
        
        for chunk in response:
            if chunk.text:
                yield chunk.text


class GroqProvider(LLMProvider):
    def get_name(self) -> str:
        return "Groq"

    def list_default_models(self) -> List[str]:
        return [
            "llama-3.3-70b-versatile",
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]

    def generate_stream(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Generator[str, None, None]:
        try:
            from groq import Groq
        except ImportError:
            raise ImportError("Please install the Groq package: `pip install groq`")
            
        if not api_key:
            raise ValueError("API Key is required for Groq.")
            
        client = Groq(api_key=api_key)
        
        # Format messages matching Groq expectations (role, content)
        formatted_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
        
        completion = client.chat.completions.create(
            model=model_name,
            messages=formatted_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )
        
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class DeepSeekProvider(LLMProvider):
    def get_name(self) -> str:
        return "DeepSeek"

    def list_default_models(self) -> List[str]:
        return [
            "deepseek-chat",
            "deepseek-reasoner"
        ]

    def generate_stream(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Generator[str, None, None]:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Please install the OpenAI package to use DeepSeek: `pip install openai`")
            
        if not api_key:
            raise ValueError("API Key is required for DeepSeek.")
            
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        
        formatted_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
        
        completion = client.chat.completions.create(
            model=model_name,
            messages=formatted_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )
        
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class HuggingFaceProvider(LLMProvider):
    def get_name(self) -> str:
        return "Hugging Face"

    def list_default_models(self) -> List[str]:
        return [
            "meta-llama/Llama-3-8B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "microsoft/Phi-3-mini-4k-instruct"
        ]

    def generate_stream(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Generator[str, None, None]:
        try:
            from huggingface_hub import InferenceClient
        except ImportError:
            raise ImportError("Please install the huggingface_hub package: `pip install huggingface_hub`")
            
        if not api_key:
            raise ValueError("Hugging Face API Token is required.")
            
        client = InferenceClient(api_key=api_key)
        
        formatted_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
        
        stream = client.chat_completion(
            model=model_name,
            messages=formatted_messages,
            max_tokens=max_tokens,
            stream=True
        )
        
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# A generic provider allowing users to connect to any OpenAI-compatible API
class CustomOpenAIProvider(LLMProvider):
    def __init__(self, name: str = "Custom OpenAI API", default_models: List[str] = None, base_url: str = ""):
        self.name = name
        self.default_models = default_models or ["gpt-4o", "gpt-3.5-turbo"]
        self.base_url = base_url

    def get_name(self) -> str:
        return self.name

    def list_default_models(self) -> List[str]:
        return self.default_models

    def generate_stream(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Generator[str, None, None]:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Please install the OpenAI package to use custom endpoints: `pip install openai`")
            
        # If no custom base_url is set, fallback to official OpenAI
        base_url = self.base_url if self.base_url else None
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        formatted_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
        
        completion = client.chat.completions.create(
            model=model_name,
            messages=formatted_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )
        
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# Global helper registry of built-in providers
PROVIDERS = {
    "gemini": GeminiProvider(),
    "groq": GroqProvider(),
    "deepseek": DeepSeekProvider(),
    "huggingface": HuggingFaceProvider()
}

def get_provider(provider_key: str, custom_config: Optional[Dict[str, Any]] = None) -> LLMProvider:
    """Retrieve a provider instance, either static built-in or dynamically constructed custom provider."""
    if provider_key in PROVIDERS:
        return PROVIDERS[provider_key]
    
    if custom_config:
        # Construct custom provider from stored config
        models = [m.strip() for m in custom_config.get("models", "").split(",") if m.strip()]
        return CustomOpenAIProvider(
            name=custom_config.get("name", "Custom Provider"),
            default_models=models,
            base_url=custom_config.get("base_url", "")
        )
        
    raise ValueError(f"Unknown LLM provider: {provider_key}")

"""Instructor-enhanced LLM client for robust structured outputs with automatic validation and retry."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel

from ..llm import LLMClient, LLMResponse
from .litellm_client import LiteLLMClient

logger = logging.getLogger(__name__)

# Instructor is a core dependency - always available
import instructor
from litellm import completion

T = TypeVar("T", bound=BaseModel)


class InstructorClient:
    """
    Wrapper around LiteLLM that adds Instructor's structured output capabilities.

    Provides automatic validation, intelligent retry on validation failures,
    and feeds validation errors back to the LLM for correction.

    Args:
        llm: Base LLMClient to wrap (typically LiteLLMClient)
        mode: Instructor mode - 'json' (default), 'md_json', 'tools', etc.
        max_retries: Maximum validation retries (default: 3)

    Example:
        >>> from ace.llm_providers.litellm_client import LiteLLMClient
        >>> from ace.llm_providers.instructor_client import InstructorClient
        >>>
        >>> base_llm = LiteLLMClient(model="gpt-4")
        >>> instructor_llm = InstructorClient(base_llm)
        >>>
        >>> # Use with Generator/Reflector/Curator
        >>> from ace import Generator, GeneratorOutput
        >>> generator = Generator(instructor_llm)

    Features:
        - Automatic Pydantic validation
        - Intelligent retry with error feedback
        - Works with any LiteLLM-compatible model
    """

    def __init__(
        self,
        llm: LLMClient,
        mode=instructor.Mode.MD_JSON,
        max_retries: int = 3,
    ):
        """
        Initialize Instructor client wrapper.

        Args:
            llm: Base LLM client (must be LiteLLMClient or compatible)
            mode: Instructor mode for structured output (default: instructor.Mode.MD_JSON)
                   MD_JSON works with all models including local ones; use Mode.JSON for OpenAI structured outputs
            max_retries: Maximum validation retries
        """

        self.llm = llm
        self.mode = mode
        self.max_retries = max_retries

        # Patch LiteLLM completion function with Instructor
        self.client = instructor.from_litellm(completion, mode=mode)
        logger.info(
            f"Initialized InstructorClient with mode={mode}, max_retries={max_retries}"
        )

    def complete(
        self,
        prompt: str,
        response_model: Optional[Type[T]] = None,
        system: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Standard completion that returns text (for backward compatibility).

        Args:
            prompt: User prompt
            response_model: Optional Pydantic model for structured output
            system: Optional system prompt
            **kwargs: Additional LLM parameters

        Returns:
            LLMResponse with text content
        """
        if response_model is not None:
            # Structured output requested - use complete_structured
            structured_output = self.complete_structured(
                prompt=prompt, response_model=response_model, system=system, **kwargs
            )
            # Convert to LLMResponse
            return LLMResponse(
                text=structured_output.model_dump_json(indent=2),
                raw={"structured_output": structured_output.model_dump()},
            )
        else:
            # Fall back to base LLM for unstructured output
            return self.llm.complete(prompt, system=system, **kwargs)

    def complete_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system: Optional[str] = None,
        **kwargs: Any,
    ) -> T:
        """
        Completion with structured output validation using Instructor.

        This is the core method that leverages Instructor's capabilities:
        - Automatic Pydantic validation
        - Intelligent retry on validation failures
        - Feeds validation errors back to LLM

        Args:
            prompt: User prompt
            response_model: Pydantic model class to validate against
            system: Optional system prompt
            **kwargs: Additional LLM parameters (temperature, max_tokens, etc.)

        Returns:
            Instance of response_model with validated data

        Raises:
            ValidationError: If validation fails after max_retries

        Example:
            >>> from ace.roles import GeneratorOutput
            >>> output = instructor_llm.complete_structured(
            ...     prompt="What is 2+2?",
            ...     response_model=GeneratorOutput
            ... )
            >>> print(output.final_answer)
            4
        """
        # Extract LiteLLM-compatible parameters from our LLMClient
        # Note: This assumes we're wrapping a LiteLLMClient
        model = getattr(self.llm, "config", None)
        if model and hasattr(model, "model"):
            model_name = model.model
        else:
            model_name = kwargs.pop("model", "gpt-3.5-turbo")

        # Build messages
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Merge parameters
        call_params = {
            "model": model_name,
            "messages": messages,
            "response_model": response_model,
            "max_retries": self.max_retries,
        }

        # Add LLM parameters
        if hasattr(self.llm, "config"):
            config = self.llm.config
            call_params.update(
                {
                    "temperature": kwargs.get("temperature", config.temperature),
                    "max_tokens": kwargs.get("max_tokens", config.max_tokens),
                }
            )
            # Only add top_p if explicitly set (not None)
            top_p_value = kwargs.get("top_p", config.top_p)
            if top_p_value is not None:
                call_params["top_p"] = top_p_value

            # Apply Claude parameter resolution to avoid temperature + top_p conflict
            sampling_priority = getattr(config, "sampling_priority", "temperature")
            call_params = LiteLLMClient._resolve_sampling_params(
                call_params, model_name, sampling_priority
            )

        # Add any additional kwargs
        call_params.update({k: v for k, v in kwargs.items() if k not in call_params})

        try:
            # Route through base LLM client to ensure callbacks (including Opik) are triggered
            # This is critical for token tracking and observability
            if hasattr(self.llm, 'complete') and isinstance(self.llm, LiteLLMClient):
                # Convert messages back to prompt format for base LLM
                prompt_parts = []
                system_prompt = None

                for msg in messages:
                    if msg.get("role") == "system":
                        system_prompt = msg["content"]
                    elif msg.get("role") == "user":
                        prompt_parts.append(msg["content"])

                combined_prompt = "\n\n".join(prompt_parts)

                # Extract base LLM parameters (remove Instructor-specific ones)
                base_params = {k: v for k, v in call_params.items()
                              if k not in ['messages', 'response_model', 'max_retries']}

                # Add system prompt if present
                if system_prompt:
                    base_params["system"] = system_prompt

                # Call through base LLM (this triggers Opik callbacks)
                raw_response = self.llm.complete(combined_prompt, **base_params)

                # Parse the response with Pydantic validation
                import json
                from pydantic import ValidationError

                try:
                    # Try to parse the raw response as JSON
                    text = raw_response.text.strip()
                    if text.startswith('{') and text.endswith('}'):
                        data = json.loads(text)
                        validated_response = response_model.model_validate(data)
                        logger.debug(f"Successfully validated {response_model.__name__} via base LLM")
                        return validated_response
                    else:
                        # If not valid JSON, fall back to Instructor
                        logger.debug(f"Base LLM response not JSON, falling back to Instructor for {response_model.__name__}")
                except (json.JSONDecodeError, ValidationError) as e:
                    # If validation fails, fall back to Instructor
                    logger.debug(f"Base LLM validation failed, falling back to Instructor: {e}")

            # Fallback: Use Instructor's patched completion
            response = self.client.chat.completions.create(**call_params)
            logger.debug(
                f"Instructor validation successful for {response_model.__name__}"
            )
            return response

        except Exception as e:
            logger.error(f"Instructor validation failed: {e}")
            raise


def wrap_with_instructor(
    llm: LLMClient, mode=instructor.Mode.MD_JSON, max_retries: int = 3
) -> InstructorClient:
    """
    Convenience function to wrap an LLM client with Instructor capabilities.

    Args:
        llm: Base LLM client to wrap
        mode: Instructor mode (default: instructor.Mode.MD_JSON for broad compatibility)
        max_retries: Maximum validation retries

    Returns:
        InstructorClient with automatic Pydantic validation

    Example:
        >>> from ace.llm_providers.litellm_client import LiteLLMClient
        >>> from ace.llm_providers.instructor_client import wrap_with_instructor
        >>>
        >>> base_llm = LiteLLMClient(model="gpt-4")
        >>> llm = wrap_with_instructor(base_llm)
        >>> generator = Generator(llm)  # Auto-validates
    """
    return InstructorClient(llm, mode=mode, max_retries=max_retries)

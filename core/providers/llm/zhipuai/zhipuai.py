
import os
import json
from abc import ABC, abstractmethod

from zai import ZhipuAiClient, core as zai_errors

from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class LLMProviderBase(ABC):
    @abstractmethod
    def response(self, session_id, dialogue, **kwargs):
        """LLM response generator"""
        pass

    def response_no_stream(self, system_prompt, user_prompt, **kwargs):
        try:
            # Construct the dialogue format
            dialogue = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            result = ""
            # The 'response' method is a generator, so we iterate through it
            for part in self.response("", dialogue, **kwargs):
                result += part
            return result

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in non-streaming response generation: {e}")
            return "【LLM service response exception】"

    def response_with_functions(self, session_id, dialogue, functions=None):
        """
        Default implementation for function calling (streaming).
        This should be overridden by providers that support function calls.

        Yields: A tuple of (text_token, function_call_info)
        """
        # For providers that don't support functions, just return the regular response
        # and None for the function call part.
        for token in self.response(session_id, dialogue):
            yield token, None


class LLMProvider(LLMProviderBase):
    """
    LLM Provider implementation for Zhipu AI (Z.ai).
    """

    def __init__(self, config):
        """
        Initializes the Zhipu AI client and sets configuration.

        Args:
            config (dict): A dictionary containing configuration settings.
                           Expected keys: 'model_name', and other optional API parameters.
        """
        # Initialize the Zhipu AI client. It automatically uses the ZAI_API_KEY environment variable.
        self.client = ZhipuAiClient(api_key=os.getenv("ZAI_API_KEY"))

        # Set default parameters for the API calls.
        # These can be overridden by the config or kwargs in method calls.
        self.params = {
            "model": config.get("model_name", "glm-4"),  # Use 'glm-4' as a robust default
            "temperature": config.get("temperature", 0.7),
            "top_p": config.get("top_p", 0.95)
        }
        logger.bind(tag=TAG).info(f"Zhipu AI Provider initialized with model: {self.params['model']}")

    def response(self, session_id, dialogue, **kwargs):
        """
        Generates a streaming response from the Zhipu AI model.

        Args:
            session_id (str): The ID for the session (not directly used by Zhipu API but kept for interface consistency).
            dialogue (list): A list of message dictionaries.
            **kwargs: Additional parameters to pass to the API, overriding defaults.

        Yields:
            str: Chunks of the response text as they are generated.
        """
        try:
            # Combine default parameters with any provided kwargs
            request_params = {**self.params, **kwargs}

            # Create a streaming chat completion request
            stream = self.client.chat.completions.create(
                messages=dialogue,
                stream=True,
                **request_params
            )

            # Yield each content chunk from the stream
            for chunk in stream:
                if chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except zai_errors.APIStatusError as e:
            logger.bind(tag=TAG).error(f"Zhipu AI API Error: {e.status_code} - {e.response}")
            yield "【LLM service API error】"
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in Zhipu AI stream generation: {e}")
            yield "【LLM service response exception】"

    def response_with_functions(self, session_id, dialogue, functions=None, **kwargs):
        """
        Generates a streaming response that can include function calls.

        Args:
            session_id (str): The ID for the session.
            dialogue (list): A list of message dictionaries.
            functions (list): A list of function definitions available to the model.
            **kwargs: Additional parameters to pass to the API.

        Yields:
            tuple: A tuple containing (text_chunk, function_call).
                   - text_chunk (str or None): A piece of the response text.
                   - function_call (dict or None): A completed function call request from the model.
        """
        if not functions:
            # If no functions are provided, fall back to the standard response method.
            for token in self.response(session_id, dialogue, **kwargs):
                yield token, None
            return

        try:
            # Format functions into the 'tools' structure required by the Zhipu API
            tools = [{"type": "function", "function": f} for f in functions]

            # Combine parameters and force tool_choice to 'auto'
            request_params = {**self.params, **kwargs, "tools": tools, "tool_choice": "auto"}

            stream = self.client.chat.completions.create(
                messages=dialogue,
                stream=True,
                **request_params
            )

            # This list will hold the tool call data as it's streamed
            tool_calls_aggregator = []

            for chunk in stream:
                delta = chunk.choices[0].delta

                # 1. Yield any text content immediately
                if delta and delta.content:
                    yield delta.content, None

                # 2. Aggregate tool call chunks
                if delta and delta.tool_calls:
                    for tool_chunk in delta.tool_calls:
                        # If this is a new tool call, prepare a placeholder
                        if len(tool_calls_aggregator) <= tool_chunk.index:
                            tool_calls_aggregator.append(
                                {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})

                        # Get the current tool call we are building
                        current_tool = tool_calls_aggregator[tool_chunk.index]

                        # Append argument chunks
                        if tool_chunk.function.arguments:
                            current_tool["function"]["arguments"] += tool_chunk.function.arguments

                        # Fill in other details as they arrive
                        if tool_chunk.id:
                            current_tool["id"] = tool_chunk.id
                        if tool_chunk.function.name:
                            current_tool["function"]["name"] = tool_chunk.function.name

                # 3. If the stream is finished due to a tool call, yield the aggregated tool call(s)
                if chunk.choices[0].finish_reason == 'tool_calls':
                    for tool_call in tool_calls_aggregator:
                        # Before yielding, ensure arguments is a valid JSON object, not a string
                        try:
                            tool_call['function']['arguments'] = json.loads(tool_call['function']['arguments'])
                        except json.JSONDecodeError:
                            # Handle cases where arguments are not valid JSON
                            logger.bind(tag=TAG).warning(
                                f"Failed to parse function call arguments: {tool_call['function']['arguments']}")
                        yield None, tool_call

        except zai_errors.APIStatusError as e:
            logger.bind(tag=TAG).error(f"Zhipu AI API Error (with functions): {e.status_code} - {e.response}")
            yield "【Zhipu LLM service API error】", None
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in Zhipu AI stream generation (with functions): {e}")
            yield "【Zhipu LLM service response exception】", None
import unittest
from unittest.mock import patch, MagicMock

import sys
sys.path.append('/root/GLM-Xiaozhi')

from core.providers.llm.zhipuai.zhipuai import LLMProvider
class TestParallelFunctionCalling(unittest.TestCase):
    def setUp(self):
        """Set up mock data that will be used in the test."""
        # This is the `functions` definition you would pass to the provider.
        self.mock_functions_schema = [
            {"name": "get_current_weather", "description": "Get weather"},
            {"name": "get_stock_price", "description": "Get stock price"}
        ]

        # This is the expected final output after the provider has processed the stream.
        self.expected_reconstructed_calls = [
            {
                'id': 'call_weather_123',
                'type': 'function',
                'function': {
                    'name': 'get_current_weather',
                    'arguments': {'location': 'Boston, MA', 'unit': 'fahrenheit'}
                }
            },
            {
                'id': 'call_stock_456',
                'type': 'function',
                'function': {
                    'name': 'get_stock_price',
                    'arguments': {'symbol': 'GOOG'}
                }
            }
        ]

    def _create_mock_api_stream(self):
        """
        Creates a fake generator that mimics the Zhipu AI API streaming response
        for a parallel function call scenario. Chunks for both calls are interleaved.
        """
        # Helper to create a mock stream chunk with the necessary nested objects
        def create_chunk(tool_calls=None, content=None, finish_reason=None):
            chunk = MagicMock()
            delta = MagicMock()
            delta.content, delta.tool_calls = content, tool_calls
            choice = MagicMock()
            choice.delta, choice.finish_reason = delta, finish_reason
            chunk.choices = [choice]
            return chunk

        # Helper to create the tool_call part of a chunk
        def create_tool_call(index, call_id=None, name=None, args=None):
            tool_call = MagicMock()
            tool_call.index, tool_call.id = index, call_id
            function = MagicMock()
            function.name, function.arguments = name, args
            tool_call.function = function
            return tool_call

        # A list of chunks simulating an interleaved stream for two function calls
        mock_stream_data = [
            # 1. Model starts the FIRST tool call (weather)
            create_chunk(tool_calls=[create_tool_call(index=0, call_id='call_weather_123', name='get_current_weather')]),
            # 2. Model starts the SECOND tool call (stock)
            create_chunk(tool_calls=[create_tool_call(index=1, call_id='call_stock_456', name='get_stock_price')]),
            # 3. Model sends argument fragments for the FIRST call
            create_chunk(tool_calls=[create_tool_call(index=0, args='{"location": "Boston, MA",')]),
            # 4. Model sends argument fragments for the SECOND call
            create_chunk(tool_calls=[create_tool_call(index=1, args='{"symbol": ')]),
            # 5. Model sends final arguments for the SECOND call
            create_chunk(tool_calls=[create_tool_call(index=1, args='"GOOG"}')]),
            # 6. Model sends final arguments for the FIRST call
            create_chunk(tool_calls=[create_tool_call(index=0, args='"unit": "fahrenheit"}')]),
            # 7. Model sends a final text message
            create_chunk(content="Certainly, fetching that data for you now."),
            # 8. Model signals the end of its turn because of tool calls
            create_chunk(finish_reason='tool_calls')
        ]

        yield from mock_stream_data

    @patch('zhipu_provider.ZhipuAiClient')  # This decorator intercepts the creation of a ZhipuAiClient
    def test_reconstructs_parallel_function_calls_from_stream(self, MockZhipuAiClient):
        """
        This is the main test. It checks if the provider correctly reassembles
        the interleaved stream of function call chunks.
        """
        # Arrange: Configure the mock client to return our fake stream
        mock_api_instance = MockZhipuAiClient.return_value
        mock_api_instance.chat.completions.create.return_value = self._create_mock_api_stream()

        # Act: Instantiate our provider and call the method we want to test
        provider = LLMProvider(config={})  # Config can be empty because the client is mocked
        dialogue = [{"role": "user", "content": "Get weather and stock price"}]
        generator = provider.response_with_functions(
            session_id="test_session_123",
            dialogue=dialogue,
            functions=self.mock_functions_schema
        )

        # Collect all the results from the generator
        text_parts = []
        function_calls = []
        for text, func in generator:
            if text:
                text_parts.append(text)
            if func:
                function_calls.append(func)
        full_text = "".join(text_parts)

        # Assert: Check if the collected results match what we expect
        self.assertEqual("Certainly, fetching that data for you now.", full_text)
        self.assertEqual(2, len(function_calls), "Should have found exactly two function calls")
        # assertCountEqual checks that two lists have the same items, regardless of order.
        # This is ideal for comparing lists of dictionaries.
        self.assertCountEqual(self.expected_reconstructed_calls, function_calls)


if __name__ == '__main__':
    unittest.main()
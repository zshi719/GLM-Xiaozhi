import os
import base64
from typing import Generator, Optional, Dict, Any
from config.logger import setup_logging
from core.providers.vllm.base import VLLMProviderBase
from zai import ZhipuAiClient
import zai.core

TAG = __name__
logger = setup_logging()


class VLLMProvider(VLLMProviderBase):
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize ZhipuAI Vision-Language Model Provider
        
        Args:
            config: Configuration dictionary containing:
                - api_key: ZhipuAI API key (optional if set in environment)
                - model_name: Vision model to use (default: glm-4v)
                - temperature: Temperature for generation (default: 0.7)
                - max_tokens: Maximum tokens to generate (default: 1000)
                - top_p: Top-p sampling (default: 0.95)
                - system_prompt: Optional system prompt for the model
        """
        # Get API key from config or environment
        api_key = config.get("api_key") or os.getenv("ZAI_API_KEY")
        if not api_key:
            raise ValueError("ZhipuAI API key not found in config or environment (ZAI_API_KEY)")
        
        # Initialize client
        self.client = ZhipuAiClient(api_key=api_key)
        
        # Model configuration - use glm-4v for vision tasks
        self.model_name = config.get("model_name", "glm-4v")
        
        # Optional system prompt
        self.system_prompt = config.get("system_prompt", "你是一个专业的图像分析助手，能够详细准确地理解和描述图像内容。")
        
        # Generation parameters with defaults
        self.param_defaults = {
            "temperature": config.get("temperature", 0.7),
            "max_tokens": config.get("max_tokens", 1000),
            "top_p": config.get("top_p", 0.95),
            "stream": True  # Always use streaming for better user experience
        }
        
        logger.bind(tag=TAG).info(f"ZhipuAI VLLM provider initialized with model: {self.model_name}")
    
    def response(self, question: str, base64_image: str) -> Generator[str, None, None]:
        """
        Generate streaming response for vision-language tasks
        
        Args:
            question: User's question about the image
            base64_image: Base64 encoded image string (with or without data URI prefix)
        
        Yields:
            str: Response tokens as they are generated
        """
        try:
            # Process base64 image
            if base64_image.startswith('data:'):
                # Extract actual base64 data if it includes data URI scheme
                # Format: data:image/jpeg;base64,actual_base64_data
                base64_data = base64_image.split(',')[1] if ',' in base64_image else base64_image
                # Extract media type
                media_type = "image/jpeg"  # Default
                if ';' in base64_image:
                    media_info = base64_image.split(';')[0]
                    if '/' in media_info:
                        media_type = media_info.split(':')[1] if ':' in media_info else "image/jpeg"
            else:
                # Raw base64 string
                base64_data = base64_image
                media_type = "image/jpeg"  # Default to JPEG
            
            # Validate base64 data
            try:
                # Try to decode to verify it's valid base64
                base64.b64decode(base64_data)
            except Exception as e:
                logger.bind(tag=TAG).error(f"Invalid base64 image data: {e}")
                yield "【图像数据格式错误：请提供有效的base64编码图像】"
                return
            
            # Construct messages with image
            messages = [
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": question
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{base64_data}"
                            }
                        }
                    ]
                }
            ]
            
            logger.bind(tag=TAG).debug(f"Processing vision request with question: {question[:50]}...")
            
            # Create chat completion with streaming
            response_stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                **self.param_defaults
            )
            
            # Stream the response
            full_response = ""
            for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_response += token
                    yield token
            
            logger.bind(tag=TAG).debug(f"Vision response completed, generated {len(full_response)} characters")
            
        except zai.core.APIStatusError as e:
            error_msg = f"API status error: {e}"
            logger.bind(tag=TAG).error(error_msg)
            yield f"【API状态错误: {str(e)}】"
        
        except zai.core.APITimeoutError as e:
            error_msg = f"API timeout error: {e}"
            logger.bind(tag=TAG).error(error_msg)
            yield "【请求超时，请稍后重试】"
        
        except Exception as e:
            error_msg = f"Unexpected error in ZhipuAI VLLM response: {e}"
            logger.bind(tag=TAG).error(error_msg)
            yield "【视觉模型服务响应异常】"
    
    def response_no_stream(self, question: str, base64_image: str) -> str:
        """
        Generate non-streaming response (convenience method)
        
        Args:
            question: User's question about the image
            base64_image: Base64 encoded image string
        
        Returns:
            str: Complete response text
        """
        try:
            result = ""
            for token in self.response(question, base64_image):
                result += token
            return result
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in non-streaming response: {e}")
            return "【视觉模型服务响应异常】"
    
    def analyze_image(self, base64_image: str, analysis_type: str = "general") -> Generator[str, None, None]:
        """
        Analyze image with predefined analysis types
        
        Args:
            base64_image: Base64 encoded image string
            analysis_type: Type of analysis to perform:
                - "general": General description
                - "detailed": Detailed analysis
                - "objects": Object detection and listing
                - "text": OCR/text extraction
                - "emotions": Emotion/sentiment analysis (for faces)
        
        Yields:
            str: Analysis results as tokens
        """
        analysis_prompts = {
            "general": "请简要描述这张图片的内容。",
            "detailed": "请详细分析这张图片，包括主要内容、细节、颜色、构图、氛围等各个方面。",
            "objects": "请识别并列出图片中所有可见的物体和元素。",
            "text": "请提取并识别图片中的所有文字内容。如果没有文字，请说明。",
            "emotions": "请分析图片中人物的表情和情绪。如果没有人物，请描述图片传达的整体情感氛围。"
        }
        
        prompt = analysis_prompts.get(analysis_type, analysis_prompts["general"])
        
        logger.bind(tag=TAG).info(f"Performing {analysis_type} analysis on image")
        
        for token in self.response(prompt, base64_image):
            yield token
    
    def compare_images(self, base64_image1: str, base64_image2: str, comparison_type: str = "differences") -> Generator[str, None, None]:
        """
        Compare two images
        
        Args:
            base64_image1: First base64 encoded image
            base64_image2: Second base64 encoded image
            comparison_type: Type of comparison:
                - "differences": Find differences
                - "similarities": Find similarities
                - "both": Both differences and similarities
        
        Yields:
            str: Comparison results as tokens
        """
        try:
            # Process both base64 images
            images_data = []
            for idx, base64_img in enumerate([base64_image1, base64_image2], 1):
                if base64_img.startswith('data:'):
                    base64_data = base64_img.split(',')[1] if ',' in base64_img else base64_img
                    media_type = "image/jpeg"
                    if ';' in base64_img:
                        media_info = base64_img.split(';')[0]
                        if '/' in media_info:
                            media_type = media_info.split(':')[1] if ':' in media_info else "image/jpeg"
                else:
                    base64_data = base64_img
                    media_type = "image/jpeg"
                
                images_data.append(f"data:{media_type};base64,{base64_data}")
            
            # Construct comparison prompt
            comparison_prompts = {
                "differences": "请仔细比较这两张图片，找出它们之间的所有差异。",
                "similarities": "请比较这两张图片，找出它们的共同点和相似之处。",
                "both": "请详细比较这两张图片，分析它们的相似之处和不同之处。"
            }
            
            prompt = comparison_prompts.get(comparison_type, comparison_prompts["both"])
            
            # Construct messages with both images
            messages = [
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": images_data[0]
                            }
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": images_data[1]
                            }
                        }
                    ]
                }
            ]
            
            logger.bind(tag=TAG).debug(f"Comparing two images with {comparison_type} analysis")
            
            # Create chat completion with streaming
            response_stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                **self.param_defaults
            )
            
            # Stream the response
            for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
        except Exception as e:
            error_msg = f"Error in image comparison: {e}"
            logger.bind(tag=TAG).error(error_msg)
            yield "【图像比较服务异常】"


import time
import os
import base64
import traceback
import asyncio
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.providers.asr.dto.dto import InterfaceType
from core.providers.asr.base import ASRProviderBase
import re
import time
import wave
import base64

import wave
import base64
from zai import ZhipuAiClient

TAG = __name__
logger = setup_logging()

# 用于指示 GLM-4-Voice 仅执行转录任务的系统提示词
SYSTEM_ASR_PROMPT = "你是一个语音转录助手。请准确复述用户在音频输入中所说的内容。只回应转录的文本，不要添加任何额外的词语、问候或评论。"

class ASRProvider(ASRProviderBase):
    """
    使用 ZhipuAI GLM-4-Voice 模型实现 ASR。
    注意：对于纯 ASR 任务，GLM-ASR 通常比 GLM-4-Voice 更快且成本更低。
    """
    def __init__(self, config: dict, delete_audio_file: bool = True):
        super().__init__()
        self.interface_type = InterfaceType.NON_STREAM
        self.output_dir = config.get("output_dir", "tmp/asr_output")
        self.delete_audio_file = delete_audio_file
        self.prompt = config.get("prompt", SYSTEM_ASR_PROMPT)
        self.client = ZhipuAiClient(api_key='d810b9919d1b499ea808f8243ce40832.DiCuCHF8M6gOqGBT')
        os.makedirs(self.output_dir, exist_ok=True)
        logger.bind(tag=TAG).info(f"GLM-4-Voice initialized")

    def save_audio_to_file(self, pcm_data: bytes, session_id: str) -> str:
        """保存PCM音频数据到WAV文件"""
        timestamp = int(time.time())
        file_path = os.path.join(self.output_dir, f"asr_input_{session_id}_{timestamp}.wav")
        
        # 确保pcm_data是bytes类型
        if not isinstance(pcm_data, bytes):
            raise TypeError(f"pcm_data must be bytes, got {type(pcm_data)}")
        
        # 检查数据长度
        if len(pcm_data) == 0:
            logger.bind(tag=TAG).warning("PCM数据为空")
            # 创建一个短的静默音频
            pcm_data = b'\x00' * 1600  # 100ms的静默音频 (16000Hz * 0.1s * 2 bytes/sample)
        
        try:
            with wave.open(file_path, 'wb') as wav_file:
                wav_file.setnchannels(1)  # 单声道
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(16000)  # 16kHz采样率
                wav_file.writeframes(pcm_data)
            
            logger.bind(tag=TAG).debug(f"音频文件已保存: {file_path}, 大小: {len(pcm_data)} bytes")
            return file_path
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"保存音频文件失败: {e}")
            raise

    async def speech_to_text(self, opus_data: List[bytes], session_id: str, audio_format="opus") -> Tuple[Optional[str], Optional[str]]:
        """
        将语音数据转换为文本
        模仿OpenAI ASR的处理方式
        """
        file_path = None
        try:
            start_time = time.time()
            
            # 处理输入数据格式
            if audio_format == "pcm":
                # 如果已经是PCM格式
                if isinstance(opus_data, list):
                    pcm_data = b''.join(opus_data) if all(isinstance(x, bytes) for x in opus_data) else b''
                else:
                    pcm_data = opus_data if isinstance(opus_data, bytes) else b''
            else:
                # 对于opus或其他格式，尝试使用基类的decode_opus方法（如果存在）
                if hasattr(super(), 'decode_opus') and callable(getattr(super(), 'decode_opus')):
                    pcm_data = super().decode_opus(opus_data)
                else:
                    # 如果没有预定义的decode_opus，简单处理
                    if isinstance(opus_data, list):
                        pcm_data = b''.join(opus_data) if all(isinstance(x, bytes) for x in opus_data) else b''
                    else:
                        pcm_data = opus_data if isinstance(opus_data, bytes) else b''
            
            # 确保pcm_data是bytes类型
            if not isinstance(pcm_data, bytes):
                logger.bind(tag=TAG).error(f"PCM数据类型错误: {type(pcm_data)}, 期望bytes")
                return None, None
                
                
            file_path = self.save_audio_to_file(pcm_data, session_id)
            
            logger.bind(tag=TAG).debug(
                f"音频文件保存耗时: {time.time() - start_time:.3f}s | 路径: {file_path}"
            )
            
            # 将WAV文件转换为Base64用于API调用
            
            with open(file_path, "rb") as f:
                audio_bytes = f.read()
            base64_voice = base64.b64encode(audio_bytes).decode("utf-8")

            response = self.client.chat.completions.create(
                model="glm-4-voice",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                        "type": "input_audio",
                                        "input_audio": {
                                            "data": base64_voice,
                                            "format": "wav"
                                        }
                                    }
                                ]
                            }
                        ],
                        stream=False
                    )

            if response and response.choices:
                    message = response.choices[0].message
                    transcript = message.content
            else:
                    transcript = None
            
            logger.bind(tag=TAG).debug(
                f"GLM ASR API调用耗时: {time.time() - start_time:.3f}s")

            if transcript:
                text = transcript.strip()
                logger.bind(tag=TAG).info(f"ASR结果: {text}")
                return text, file_path
            else:
                logger.bind(tag=TAG).error(f"ASR API返回空结果")
                return None, file_path

        except Exception as e:
            logger.bind(tag=TAG).error(f"ASR处理异常: {str(e)}")
            logger.bind(tag=TAG).error(f"Traceback: {traceback.format_exc()}")
            return None, file_path
        
        finally:
            # 清理临时文件
            if self.delete_audio_file and file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.bind(tag=TAG).debug(f"已清理临时文件: {file_path}")
                except Exception as e:
                    logger.bind(tag=TAG).warning(f"清理临时文件失败 {file_path}: {e}")

    def _extract_text_from_asr_response(self, resp) -> str:
        """从ASR响应中提取文本"""
        parts = []
        try:
            for item in resp:
                text = None
                if hasattr(item, "text"):
                    text = item.text
                elif hasattr(item, "message") and hasattr(item.message, "text"):
                    text = item.message.text
                elif isinstance(item, dict):
                    text = item.get("text") or (item.get("message") or {}).get("text")
                if text:
                    parts.append(str(text))
        except TypeError:
            # 不可迭代的情况
            if hasattr(resp, "text"):
                parts.append(str(resp.text))
            elif hasattr(resp, "message") and hasattr(resp.message, "text"):
                parts.append(str(resp.message.text))
            elif isinstance(resp, dict):
                text = resp.get("text") or (resp.get("message") or {}).get("text")
                if text:
                    parts.append(str(text))

        return " ".join(p for p in parts if p)

    async def text_to_speak(self, text: str, output_file: str) -> Optional[str]:
        """使用GLM-4-Voice将文本转换为语音"""
        try:
            def sync_call():
                return self.client.chat.completions.create(
                    model="glm-4-voice",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": text
                                }
                            ]
                        }
                    ],
                    stream=False
                )
            
            response = await asyncio.to_thread(sync_call)
            
            if response and response.choices:
                message = response.choices[0].message
                if hasattr(message, 'audio') and message.audio:
                    audio_data = message.audio.get('data')
                    if audio_data:
                        decoded_data = base64.b64decode(audio_data)
                        with open(output_file, "wb") as f:
                            f.write(decoded_data)
                        logger.bind(tag=TAG).info(f"TTS输出已保存到: {output_file}")
                        return output_file
                    
            logger.bind(tag=TAG).error(f"TTS API响应异常: {response}")
            return None
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"TTS处理失败: {str(e)}")
            return None
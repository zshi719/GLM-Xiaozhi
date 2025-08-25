import os
import json
import uuid
import requests
from config.logger import setup_logging
from datetime import datetime
import time
import os
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.providers.asr.dto.dto import InterfaceType
from core.providers.asr.base import ASRProviderBase

TAG = __name__
logger = setup_logging()

class ASRProvider(ASRProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.url = config.get("url")
        self.method = config.get("method", "GET")
        self.headers = config.get("headers", {})
        self.format = config.get("format", "wav")
        self.audio_file_type = config.get("format", "wav")
        self.output_file = config.get("output_dir", "tmp/")
        self.params = config.get("params")


    async def speech_to_text(self, opus_data: List[bytes], session_id: str, audio_format="opus") -> Tuple[Optional[str], Optional[str]]:
        file_path = None
        try:
            start_time = time.time()
            if audio_format == "pcm":
                pcm_data = opus_data
            else:
                pcm_data = self.decode_opus(opus_data)
            file_path = self.save_audio_to_file(pcm_data, session_id)

            logger.bind(tag=TAG).debug(
                f"音频文件保存耗时: {time.time() - start_time:.3f}s | 路径: {file_path}"
            )

            logger.bind(tag=TAG).info(f"file path: {file_path}")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }
            
            # 使用data参数传递模型名称
            data = {
                "model": self.model
            }


            with open(file_path, "rb") as audio_file:  # 使用with语句确保文件关闭
                files = {
                    "file": audio_file
                }

                start_time = time.time()
                response = requests.post(
                    self.api_url,
                    files=files,
                    data=data,
                    headers=headers
                )
                logger.bind(tag=TAG).debug(
                    f"语音识别耗时: {time.time() - start_time:.3f}s | 结果: {response.text}"
                )

            if response.status_code == 200:
                text = response.json().get("text", "")
                return text, file_path
            else:
                raise Exception(f"API请求失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"语音识别失败: {e}")
            return "", None
        finally:
            # 文件清理逻辑
            if self.delete_audio_file and file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.bind(tag=TAG).debug(f"已删除临时音频文件: {file_path}")
                except Exception as e:
                    logger.bind(tag=TAG).error(f"文件删除失败: {file_path} | 错误: {e}")
   

        file_path = None
        try:
            start_time = time.time()
            if audio_format == "pcm":
                pcm_data = opus_data
            else:
                pcm_data = self.decode_opus(opus_data)
            file_path = self.save_audio_to_file(pcm_data, session_id)

            logger.bind(tag=TAG).debug(
                f"音频文件保存耗时: {time.time() - start_time:.3f}s | 路径: {file_path}"
            )

            logger.bind(tag=TAG).info(f"file path: {file_path}")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }
            
            # 使用data参数传递模型名称
            data = {
                "model": self.model
            }


            with open(file_path, "rb") as audio_file:  # 使用with语句确保文件关闭
                files = {
                    "file": audio_file
                }

                start_time = time.time()
                response = requests.post(
                    self.api_url,
                    files=files,
                    data=data,
                    headers=headers
                )
                logger.bind(tag=TAG).debug(
                    f"语音识别耗时: {time.time() - start_time:.3f}s | 结果: {response.text}"
                )

            if response.status_code == 200:
                text = response.json().get("text", "")
                return text, file_path
            else:
                raise Exception(f"API请求失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"语音识别失败: {e}")
            return "", None
        finally:
            # 文件清理逻辑
            if self.delete_audio_file and file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.bind(tag=TAG).debug(f"已删除临时音频文件: {file_path}")
                except Exception as e:
                    logger.bind(tag=TAG).error(f"文件删除失败: {file_path} | 错误: {e}")
   
    
    async def text_to_speak(self, text, output_file):
        request_params = {}
        for k, v in self.params.items():
            if isinstance(v, str) and "{prompt_text}" in v:
                v = v.replace("{prompt_text}", text)
            request_params[k] = v

        if self.method.upper() == "POST":
            resp = requests.post(self.url, json=request_params, headers=self.headers)
        else:
            resp = requests.get(self.url, params=request_params, headers=self.headers)
        if resp.status_code == 200:
            if output_file:
                with open(output_file, "wb") as file:
                    file.write(resp.content)
            else:
                return resp.content
        else:
            error_msg = f"Custom TTS请求失败: {resp.status_code} - {resp.text}"
            logger.bind(tag=TAG).error(error_msg)
            raise Exception(error_msg)  # 抛出异常，让调用方捕获

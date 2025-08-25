import time
import os
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.providers.asr.dto.dto import InterfaceType
from core.providers.asr.base import ASRProviderBase
import re
import requests
from zai import ZhipuAiClient
from core.utils.util import check_model_key
from config.logger import setup_logging


TAG = __name__
logger = setup_logging()

class ASRProvider(ASRProviderBase):
    API_URL = "https://open.bigmodel.cn/api/paas/v4/audio/transcriptions"
    FORMAT = "wav" 

    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__()
        self.interface_type = InterfaceType.NON_STREAM
        self.api_key = config.get("api_key")
        self.output_dir = config.get("output_dir")
        self.delete_audio_file = delete_audio_file

        os.makedirs(self.output_dir, exist_ok=True)

    def _create_safe_request_id(self, session_id: str) -> str:
        """Creates an ASCII-safe request_id to prevent Unicode errors."""
        safe_session_id = re.sub(r'[^a-zA-Z0-9_-]', '', session_id)
        timestamp = int(time.time() * 1000)
        return f"{safe_session_id}_{timestamp}"

    async def speech_to_text(self, opus_data: List[bytes], session_id: str, audio_format="opus") -> Tuple[Optional[str], Optional[str]]:
        file_path = None
        try:
            # Step 1: Decode audio using the helper from the base class
            if audio_format == "pcm":
                pcm_data = opus_data
            else:
                pcm_data = self.decode_opus(opus_data)

            if not pcm_data:
                logger.bind(tag=TAG).warning("PCM data is empty after decoding.")
                return "", None

            file_path = self.save_audio_to_file(pcm_data, session_id)
            logger.bind(tag=TAG).debug(f"Temporary audio file saved to: {file_path}")

            # Step 3: Prepare the API request
            headers = { "Authorization": f"Bearer {self.api_key}" }
            data = {
                "request_id": self._create_safe_request_id(session_id)
            }

            # Step 4: Make the API call
            with open(file_path, "rb") as audio_file:
                files = { "file": audio_file }
                response = requests.post(self.API_URL, headers=headers, data=data, files=files)

            # Step 5: Process the response
            if response.status_code == 200:
                text = response.json().get("text", "")
                return text, file_path
            else:
                logger.bind(tag=TAG).error(f"API request failed: {response.status_code} - {response.text}")
                return "", None
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"Speech recognition failed: {e}")
            return "", None
        finally:
            if self.delete_audio_file and file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.bind(tag=TAG).error(f"File deletion failed: {file_path} | Error: {e}")
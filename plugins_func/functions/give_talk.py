# give_lecture.py

import difflib
import os
import random
import re
import time
import traceback
from pathlib import Path

# Core imports based on the provided structure
from core.handle.sendAudioHandle import send_stt_message
from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType, ContentType
from core.utils.dialogue import Message
from plugins_func.register import register_function, ToolType, ActionResponse, Action

TAG = __name__

# Cache for lecture files and configuration
LECTURE_CACHE = {}

# Function description for the LLM/Agent
give_lecture_function_desc = {
    "type": "function",
    "function": {
        "name": "give_lecture",
        "description": "播放讲座、听课、开始上课的方法。用于播放本地存储的讲座音频文件。",
        "parameters": {
            "type": "object",
            "properties": {
                "lecture_topic": {
                    "type": "string",
                    "description": "讲座的主题或文件名。如果用户没有指定具体主题则为'random'，明确指定时返回主题名称。示例: ```用户:播放关于人工智能的讲座\n参数：人工智能``` ```用户:随便放个讲座 \n参数：random ```",
                }
            },
            "required": ["lecture_topic"],
        },
    },
}


@register_function("give_lecture", give_lecture_function_desc, ToolType.SYSTEM_CTL)
def give_lecture(conn, lecture_topic: str):
    """
    Registered function entry point for giving a lecture.
    """
    try:
        # Determine the intent phrase
        lecture_intent = (
            f"播放讲座 {lecture_topic}" if lecture_topic != "random" else "随机播放讲座"
        )

        # Check event loop status
        if not conn.loop.is_running():
            conn.logger.bind(tag=TAG).error("事件循环未运行，无法提交任务")
            return ActionResponse(
                action=Action.RESPONSE, result="系统繁忙", response="请稍后再试"
            )

        # Submit the asynchronous task
        task = conn.loop.create_task(
            handle_lecture_command(conn, lecture_intent)
        )

        # Non-blocking callback handling
        def handle_done(f):
            try:
                f.result()
                conn.logger.bind(tag=TAG).info("讲座播放任务提交完成")
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"讲座播放失败: {e}")

        task.add_done_callback(handle_done)

        # Immediate response to the user
        return ActionResponse(
            action=Action.NONE, result="指令已接收", response="正在为您准备讲座"
        )
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"处理讲座意图错误: {e}")
        return ActionResponse(
            action=Action.RESPONSE, result=str(e), response="播放讲座时出错了"
        )


def _extract_lecture_topic(text):
    """Extract the lecture topic from user input."""
    # Keywords that might indicate a specific lecture request
    keywords = ["播放讲座", "开始上课", "听关于", "学习", "播放课程"]
    for keyword in keywords:
        if keyword in text:
            parts = text.split(keyword)
            if len(parts) > 1:
                # Simple extraction of the part following the keyword
                topic = parts[1].strip()
                # Remove potential trailing words like "的讲座" or "的课程" using regex
                topic = re.sub(r"(的讲座|的课程|的课)$", "", topic).strip()
                if topic:
                    return topic
    return None


def _find_best_match(potential_topic, lecture_files):
    """Find the best matching lecture file using difflib."""
    best_match = None
    highest_ratio = 0
    
    # Define a minimum similarity threshold (0.4 matches the original music implementation)
    MIN_SIMILARITY = 0.4

    for lecture_file in lecture_files:
        # Compare against the filename without extension
        topic_name = os.path.splitext(lecture_file)[0]
        ratio = difflib.SequenceMatcher(None, potential_topic, topic_name).ratio()
        
        if ratio > highest_ratio and ratio > MIN_SIMILARITY:
            highest_ratio = ratio
            best_match = lecture_file
    return best_match


def get_lecture_files(lecture_dir, lecture_ext):
    """Scans the directory recursively for files matching the extensions."""
    lecture_dir = Path(lecture_dir)
    lecture_files = []
    lecture_file_names = []
    
    # Defensive check: ensure directory exists before scanning
    if not lecture_dir.exists():
        return lecture_files, lecture_file_names

    for file in lecture_dir.rglob("*"):
        if file.is_file():
            ext = file.suffix.lower()
            if ext in lecture_ext:
                # Store relative path
                relative_path = str(file.relative_to(lecture_dir))
                lecture_files.append(relative_path)
                lecture_file_names.append(os.path.splitext(relative_path)[0])
                
    return lecture_files, lecture_file_names


def initialize_lecture_handler(conn):
    """Initializes configuration and scans the lecture directory."""
    global LECTURE_CACHE
    if LECTURE_CACHE == {}:
        # Default configuration
        default_dir = os.path.abspath("./lecture")
        default_ext = (".mp3", ".wav", ".m4a") # Common audio formats for lectures
        default_refresh = 300 # 5 minutes refresh interval

        # Load configuration from the main config file if the plugin is enabled
        plugin_key = "give_lecture"
        # Safely access plugins configuration
        plugins_config = conn.config.get("plugins", {})

        if plugin_key in plugins_config:
            config = plugins_config[plugin_key]
            LECTURE_CACHE["lecture_config"] = config
            LECTURE_CACHE["lecture_dir"] = os.path.abspath(
                config.get("lecture_dir", default_dir)
            )
            # Ensure extensions are loaded as a tuple if coming from config
            LECTURE_CACHE["lecture_ext"] = tuple(config.get(
                "lecture_ext", default_ext
            ))
            LECTURE_CACHE["refresh_time"] = config.get(
                "refresh_time", default_refresh
            )
        else:
            # Use defaults if plugin configuration is missing
            LECTURE_CACHE["lecture_dir"] = default_dir
            LECTURE_CACHE["lecture_ext"] = default_ext
            LECTURE_CACHE["refresh_time"] = default_refresh

        # Initial scan of lecture files
        LECTURE_CACHE["lecture_files"], LECTURE_CACHE["lecture_file_names"] = get_lecture_files(
            LECTURE_CACHE["lecture_dir"], LECTURE_CACHE["lecture_ext"]
        )
        LECTURE_CACHE["scan_time"] = time.time()
        conn.logger.bind(tag=TAG).info(f"Lecture handler initialized. Found {len(LECTURE_CACHE['lecture_files'])} lectures in {LECTURE_CACHE['lecture_dir']}.")
    return LECTURE_CACHE


async def handle_lecture_command(conn, text):
    """Handles the logic for finding a specific or random lecture."""
    initialize_lecture_handler(conn)
    global LECTURE_CACHE

    # Clean input text. Ensure Chinese characters are preserved by explicitly including the CJK range.
    # \w typically includes alphanumeric, \s includes whitespace. We remove other symbols.
    clean_text = re.sub(r"[^\w\s\u4e00-\u9fa5]", "", text).strip()
    conn.logger.bind(tag=TAG).debug(f"Handling lecture command: {clean_text}")

    # Check if the directory exists
    if not os.path.exists(LECTURE_CACHE["lecture_dir"]):
        conn.logger.bind(tag=TAG).error(f"Lecture directory not found: {LECTURE_CACHE['lecture_dir']}")
        # Provide immediate feedback to the user
        await send_stt_message(conn, "抱歉，没有找到讲座文件夹。")
        return False

    # Refresh the file list if scan time expired
    if time.time() - LECTURE_CACHE["scan_time"] > LECTURE_CACHE["refresh_time"]:
        conn.logger.bind(tag=TAG).info("Refreshing lecture file list...")
        LECTURE_CACHE["lecture_files"], LECTURE_CACHE["lecture_file_names"] = (
            get_lecture_files(LECTURE_CACHE["lecture_dir"], LECTURE_CACHE["lecture_ext"])
        )
        LECTURE_CACHE["scan_time"] = time.time()

    # Try to extract a specific topic
    potential_topic = _extract_lecture_topic(clean_text)
    
    # Check if a specific topic was intended and extracted (and it's not just the word 'random')
    if potential_topic and potential_topic.lower() != "random":
        conn.logger.bind(tag=TAG).debug(f"Searching for topic: {potential_topic}")
        best_match = _find_best_match(potential_topic, LECTURE_CACHE["lecture_files"])
        
        if best_match:
            conn.logger.bind(tag=TAG).info(f"找到最匹配的讲座: {best_match}")
            await play_local_lecture(conn, specific_file=best_match)
            return True
        else:
            conn.logger.bind(tag=TAG).info(f"未找到匹配的讲座: {potential_topic}。将尝试随机播放。")
            # Fallback to random if specific topic not found.
            
    # If no specific topic requested or topic not found, play randomly
    await play_local_lecture(conn)
    return True


def _get_random_lecture_prompt(lecture_name):
    """Generate a random introductory phrase for the lecture."""
    # Remove file extension
    clean_name = os.path.splitext(lecture_name)[0]
    prompts = [
        f"现在开始播放讲座，《{clean_name}》。",
        f"请准备好，即将开始的讲座是《{clean_name}》。",
        f"让我们开始学习，《{clean_name}》。",
        f"现在为您带来关于《{clean_name}》的讲座。",
        f"接下来，我们将探讨《{clean_name}》。",
        f"欢迎收听讲座，《{clean_name}》。",
    ]
    return random.choice(prompts)


async def play_local_lecture(conn, specific_file=None):
    """Plays the selected local lecture audio file."""
    global LECTURE_CACHE
    try:
        # Ensure directory exists (redundant check for safety)
        if not os.path.exists(LECTURE_CACHE["lecture_dir"]):
            # This should have been caught in handle_lecture_command.
            conn.logger.bind(tag=TAG).error(
                f"讲座目录不存在: " + LECTURE_CACHE["lecture_dir"]
            )
            return

        # Determine which file to play
        if specific_file:
            selected_lecture = specific_file
            lecture_path = os.path.join(LECTURE_CACHE["lecture_dir"], specific_file)
        else:
            # Random selection
            if not LECTURE_CACHE["lecture_files"]:
                conn.logger.bind(tag=TAG).error("未找到任何讲座音频文件。")
                await send_stt_message(conn, "抱歉，讲座库中没有文件。")
                return
            selected_lecture = random.choice(LECTURE_CACHE["lecture_files"])
            lecture_path = os.path.join(LECTURE_CACHE["lecture_dir"], selected_lecture)

        # Verify the selected file exists (it might have been deleted since the last scan)
        if not os.path.exists(lecture_path):
            conn.logger.bind(tag=TAG).error(f"选定的讲座文件不存在: {lecture_path}")
            # If the specific file is missing, report the error
            if specific_file:
                 # Report the clean name without extension
                 clean_name = os.path.splitext(specific_file)[0]
                 await send_stt_message(conn, f"抱歉，文件《{clean_name}》找不到了。")
            return

        # Generate and send the introductory text
        text = _get_random_lecture_prompt(selected_lecture)
        await send_stt_message(conn, text)
        # Update dialogue history
        conn.dialogue.put(Message(role="assistant", content=text))

        # Queue the TTS and the audio file for playback
        # This sequence follows the pattern established in play_music.py

        # Signal start of action if intent type is LLM
        if conn.intent_type == "intent_llm":
            conn.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=conn.sentence_id,
                    sentence_type=SentenceType.FIRST,
                    content_type=ContentType.ACTION,
                )
            )
        
        # Queue the introductory text
        conn.tts.tts_text_queue.put(
            TTSMessageDTO(
                sentence_id=conn.sentence_id,
                sentence_type=SentenceType.MIDDLE,
                content_type=ContentType.TEXT,
                content_detail=text,
            )
        )
        
        # Queue the lecture audio file
        conn.tts.tts_text_queue.put(
            TTSMessageDTO(
                sentence_id=conn.sentence_id,
                sentence_type=SentenceType.MIDDLE,
                content_type=ContentType.FILE,
                content_file=lecture_path,
            )
        )
        
        # Signal end of action if intent type is LLM
        if conn.intent_type == "intent_llm":
            conn.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=conn.sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )

    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"播放讲座失败: {str(e)}")
        conn.logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")
        await send_stt_message(conn, "播放讲座时发生了错误。")
# 1. SDK

## 1.1. SDK 安装说明
为方便用户使用，我们提供了 SDK 和原生 HTTP 来实现模型 API 的调用。建议您使用 SDK 进行调用以获得更好的编程体验。


安装 Python SDK
Python SDK 地址：https://github.com/zhipuai/zhipuai-sdk-python-v4

首先请通过如下方式进行安装 SDK 包：

pip install zhipuai
我们升级了最新的模型 GLM-4、GLM-3-Turbo，支持了 System Prompt、FunctionCall、Retrieval、Web_Search 等新功能。使用以上新功能需升级最新版本的 Python SDK。如您已安装老版本 SDK，请您更新到最新版 SDK。

pip install --upgrade zhipuai

SDK 用户鉴权指南
我们的所有 API 使用 API Key 进行身份验证。您可以访问API Keys 页面查找您将在请求中使用的 API Key。
本版本对鉴权方式进行了升级，历史已接入平台的用户可继续沿用老版本的鉴权方式。新版本的鉴权方法可参考以下详细描述：

【重要】安全提示
请注意保护您的密钥信息！不要与他人共享或在任何客户端代码（浏览器、应用程序）中公开您的 API Key。如您的 API Key 存在泄露风险，您可以通过删除该密钥来保护您的账户安全。

Python SDK 创建 Client
我们已经将接口鉴权封装到 SDK，您只需按照 SDK 调用示例填写 API Key 即可，示例如下：

from zhipuai import ZhipuAI

client = ZhipuAI(api_key="")  # 请填写您自己的API Key
response = client.chat.completions.create(
  model="glm-4-0520",  # 填写需要调用的模型编码
  messages=[
      {"role": "user", "content": "你好！你叫什么名字"},
  ],
  stream=True,
)
for chunk in response:
    print(chunk.choices[0].delta)

# 2. HTTP
HTTP 请求参数
模型服务支持标准的 HTTP 调用。

请求头
Content-Type: application/json
Authorization: 支持 API Key 和 token 两种鉴权方式
请求地址和参数
请参考各个模型接口的具体说明。

## 2.1. GLM-ASR
GLM-ASR 基于上下文理解将音频转录为符合语言习惯的文本，显著提升输出结果的流畅性和可读性。同时，模型在噪音环境中较当前模型有明显较好的表现，不会被非语言类噪声干扰。模型支持中文、英语以及各地方方言（东北官话、胶辽官话、北京官话、冀鲁官话、中原官话、江淮官话、兰银官话和西南官话）。

模型编码：glm-asr
限时免费至 5 月 12 日，查看 产品价格 ；
查看模型 速率限制；
查看您的 API Key；
同步调用
接口请求
传输方式	https
请求地址	https://open.bigmodel.cn/api/paas/v4/audio/transcriptions
调用方式	同步调用，等待系统执行完成并返回最终结果
字符编码	UTF-8
接口请求格式	Multipart/form-data
响应格式	JSON或标准Stream Event
接口请求类型	POST
开发语言	任意可发起 http 请求的开发语言
请求参数
参数名称	类型	是否必填	参数说明
model	String	是	要调用的模型编码。
file	File	是	需要转录的音频文件支持上传的音频文件格式：.wav / .mp3 规格限制：文件大小 ≤ 25 MB、音频时长 ≤ 60 秒
temperature	Float	否	采样温度，控制输出的随机性，必须为正数 取值范围是：[0.0,1.0]， 默认值为 0.95，值越大，会使输出更随机，更具创造性；值越小，输出会更加稳定或确定 建议您根据应用场景调整 top_p 或 temperature 参数，但不要同时调整两个参数
stream	Boolean	否	该参数在使用同步调用时应设置为false或省略。表示模型在生成所有内容后一次性返回所有内容。默认值为false。如果设置为true，模型将通过标准Event Stream逐块返回生成的内容。当Event Stream结束时，将返回一个data: [DONE]消息。
request_id	String	否	由用户端传递，需要唯一；用于区分每次请求的唯一标识符。如果用户端未提供，平台将默认生成。
user_id	String	否	终端用户的唯一ID，帮助平台对终端用户的非法活动、生成非法不当信息或其他滥用行为进行干预。ID长度要求：至少6个字符，最多128个字符。
响应参数
参数名称	类型	参数说明
id	String	任务 ID
created	Long	请求创建时间，是以秒为单位的 Unix 时间戳。
request_id	String	由用户端传递，需要唯一；用于区分每次请求的唯一标识符。如果用户端未提供，平台将默认生成。
model	String	模型名称
segments	List	分句ASR内容
  id	Long	分句序号
  start	Float	分句开始时间
  end	Float	分句结束时间
  text	String	分句识别内容
text	String	音频转录的完整内容
请求示例
from zhipuai import ZhipuAI

client = ZhipuAI()  # 填写您自己的APIKey
with open("asr1.wav", "rb") as audio_file:
    transcriptResponse = client.audio.transcriptions.create(
        model="glm-asr",
        file=audio_file,
        stream=False
    )
    for item in transcriptResponse:
        print(item)
响应示例
{
    "created": 1744008189,
    "id": "202504071443089343b5d8093b48ff",
    "request_id": "202504071443089343b5d8093b48ff",
    "segments": [
        {
            "end": 3.5,
            "id": 0,
            "start": 0.2,
            "text": "这里的天气怎么样？你能看见什么？"
        }
    ],
    "text": "这里的天气怎么样？你能看见什么？"
}
流式输出
响应参数
参数名称	类型	参数说明
id	String	任务 ID
created	Long	请求创建时间，是以秒为单位的 Unix 时间戳。
model	String	模型名称
choices	List	当前对话的模型输出内容
type	String	音频转录事件类型，transcript.text.delta表示正在转录，transcript.text.done表示转录完成
delta	String	模型增量返回的音频转录信息
请求示例
from zhipuai import ZhipuAI

client = ZhipuAI()  # 填写您自己的APIKey
with open("asr1.wav", "rb") as audio_file:
    transcriptResponse = client.audio.transcriptions.create(
        model="glm-asr",
        file=audio_file,
        stream=True
    )
    for item in transcriptResponse:
        print(item)
响应示例
data: {"id":"2025040715115189eb9f01684645ef","created":1744009911,"model":"glm-asr","delta":"这里的","type":"transcript.text.delta"}
data: {"id":"2025040715115189eb9f01684645ef","created":1744009911,"model":"glm-asr","delta":"天气","type":"transcript.text.delta"}
data: {"id":"2025040715115189eb9f01684645ef","created":1744009911,"model":"glm-asr","delta":"怎么样","type":"transcript.text.delta"}
....
data: {"id":"2025040715115189eb9f01684645ef","created":1744009911,"model":"glm-asr","type":"transcript.text.done","text":"这里的天气怎么样？你能看见什么？"}
data: [DONE]



## 2.2. GLM-4-Voice
GLM-4-Voice 是智谱 AI 推出的端到端语音模型。GLM-4-Voice 能够直接理解和生成中英文语音，进行实时语音对话，并且能够遵循用户的指令要求改变语音的情感、语调、语速、方言等属性。

模型编码：glm-4-voice；
欢迎在 体验中心 体验模型能力；
查看 产品价格 ；
查看模型 速率限制；
查看您的 API Key；
同步调用
接口请求

传输方式	https
请求地址	https://open.bigmodel.cn/api/paas/v4/chat/completions
调用方式	同步调用，等待模型执行完成并返回最终结果或 SSE 调用
字符编码	UTF-8
接口请求格式	JSON
响应格式	JSON 或标准 Stream Event
接口请求类型	POST
开发语言	任意可发起 http 请求的开发语言
请求参数
参数名称	类型	是否必填	参数说明
model	String	是	调用的模型编码。 模型编码：glm-4-voice
messages	List<Object>	是	调用语言模型时，将当前对话信息列表作为提示输入给模型， 按照 json 数组形式进行传参。比如，语音对话参数：{ "role": "user", "content": [ { "type": "text", "text": "给我讲个冷笑话" }, { "type": "input_audio", "input_audio": { "data": "<base64_string>", "format": "wav" } } ] }
request_id	String	否	由用户端传参，需保证唯一性；用于区分每次请求的唯一标识，用户端不传时平台会默认生成。
do_sample	Boolean	否	do_sample 为 true 时启用采样策略，do_sample 为 false 时采样策略 temperature、top_p 将不生效。默认值为 true。
stream	Boolean	否	该参数在使用同步调用时应设置为false或省略。表示模型在生成所有内容后一次性返回所有内容。默认值为false。如果设置为true，模型将通过标准Event Stream逐块返回生成的内容。当Event Stream结束时，将返回一个data: [DONE]消息。
temperature	Float	否	采样温度，控制输出的随机性，必须为正数 取值范围是：[0.0,1.0]， 默认值为 0.8，值越大，会使输出更随机，更具创造性；值越小，输出会更加稳定或确定 建议您根据应用场景调整 top_p 或 temperature 参数，但不要同时调整两个参数
top_p	Float	否	用温度取样的另一种方法，称为核取样 取值范围是：[0.0, 1.0]，默认值为 0.6 模型考虑具有 top_p 概率质量 tokens 的结果 例如：0.1 意味着模型解码器只考虑从前 10% 的概率的候选集中取 tokens 建议您根据应用场景调整 top_p 或 temperature 参数，但不要同时调整两个参数
max_tokens	Integer	否	模型输出最大 tokens，最大输出为4095，默认值为1024
stop	List	否	模型遇到stop指定的字符时会停止生成。目前仅支持单个stop词，格式为[“stop_word1”]。
user_id	String	否	终端用户的唯一ID，协助平台对终端用户的违规行为、生成违法及不良信息或其他滥用行为进行干预。ID长度要求：最少6个字符，最多128个字符。 了解更多
Message 格式
System Message 格式

参数名称	类型	是否必填	参数说明
role	String	是	消息的角色信息，此时应为system
content	String	是	消息内容
User message 格式

参数名称	类型	是否必填	参数说明
role	String	是	消息的角色信息，此时应为user
content	List<Object>	是	消息内容。
 type	String	是	文本类型：text
语音类型：input_audio
 text	String	是	type是text 时补充
 input_audio	Object	是	type是input_audio 时补充，仅glm-4-voice支持语音输入
  data	String	是	语音文件的base64编码。音频最长不超过 10 分钟。1s音频=12.5 Tokens,向上取整。
  format	String	是	语音文件的格式，支持wav和mp3
Assistant message 格式

参数名称	类型	是否必填	参数说明
role	String	是	消息的角色信息，此时应为assistant
content	String	是	消息内容
audio	Object	是	语音消息
 id	String	是	语音消息id，用于多轮对话
响应参数
参数名称	类型	参数说明
id	String	任务 ID
created	Long	请求创建时间，是以秒为单位的 Unix 时间戳。
model	String	模型名称
choices	List	当前对话的模型输出内容
 index	Integer	结果下标
 finish_reason	String	模型推理终止的原因。stop代表推理自然结束或触发停止词。 tool_calls 代表模型命中函数。 length代表到达 tokens 长度上限。 sensitive 代表模型推理内容被安全审核接口拦截。请注意，针对此类内容，请用户自行判断并决定是否撤回已公开的内容。 network_error 代表模型推理异常。
 message	Object	模型返回的文本信息
  role	String	当前对话的角色，目前默认为 assistant（模型）
  content	String	当前对话的内容。命中函数时此字段为null，未命中函数时返回模型推理结果。
  audio	Object	当前对话的音频内容
   id	String	当前对话的音频内容id，可用户多轮对话输入
   data	String	当前对话的音频内容base64编码
   expires_at	String	当前对话的音频内容过期时间
usage	Object	结束时返回本次模型调用的 tokens 数量统计
 prompt_tokens	Integer	用户输入的 tokens 数量
 completion_tokens	Integer	模型输出的 tokens 数量
 total_tokens	Integer	总 tokens 数量，音频计算规则：1 秒音频=12.5 Tokens
content_filter	List	返回内容安全的相关信息
 role	String	安全生效环节，包括
role = assistant 模型推理，
role = user 用户输入，
role = history 历史上下文
 level	Integer	严重程度 level 0-3，level 0表示最严重，3表示轻微
请求示例
import wave
import base64

from zhipuai import ZhipuAI

def save_audio_as_wav(audio_data, filepath):
    with wave.open(filepath, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(44100)
        wav_file.writeframes(audio_data)
    print(f"Audio saved to {filepath}")


client = ZhipuAI(api_key="YOUR API KEY") # 请填写您的 API KEY（YOUR API KEY）

response = client.chat.completions.create(
    model="glm-4-voice",  # 请填写您要调用的模型名称
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "你好"
                },
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": "<base64_string>",
                        "format":"wav"
                    }
                }
            ]
        },
    ],
    max_tokens=1024,
    stream=False
)
print(response)
# 3. 获取 audio 数据
audio_data = response.choices[0].message.audio['data']
decoded_data = base64.b64decode(audio_data)
# 4. 将解码的数据写入WAV文件
with open("output.wav", 'wb') as wav_file:
    wav_file.write(decoded_data)
响应示例
{
    "created": 1703487403,
    "id": "8239375684858666781",
    "model": "glm-4-voice",
    "request_id": "8239375684858666781",
    "choices": [
        {
            "finish_reason": "stop",
            "index": 0,
            "message": {
                "content": "为什么数学书总是很不高兴？因为它有太多的问题！",
                "role": "assistant",
                "audio": {
                    "id": "c6d3b522-e6e5-4f90-b215-29ecd2a529d5",
                    "data": "<base64_string>",
                    "expires_at": 1735011068
                }
            }
        }
    ],
    "usage": {
        "completion_tokens": 217,
        "prompt_tokens": 31,
        "total_tokens": 248
    }
}
流式输出
参数名称	类型	参数说明
id	String	智谱 AI 开放平台生成的任务订单号，调用请求结果接口时请使用此订单号
created	Long	请求创建时间，是以秒为单位的 Unix 时间戳。
choices	List	当前对话的模型输出内容
 index	Integer	结果下标
 finish_reason	String	模型推理终止的原因。stop代表推理自然结束或触发停止词。 length代表到达 tokens 长度上限。 sensitive 代表模型推理内容被安全审核接口拦截。请注意，针对此类内容，请用户自行判断并决定是否撤回已公开的内容。 network_error 代表模型推理异常。
 delta	Object	模型增量返回的文本信息
  role	String	当前对话的角色，目前默认为 assistant（模型）
  content	String	当前对话的内容
  audio	Object	当前对话的音频内容
   id	String	当前对话的音频内容id，可用户多轮对话输入
   data	String	当前对话的音频内容base64编码
   expires_at	String	当前对话的音频内容过期时间
usage	Object	结束时返回本次模型调用的 tokens 数量统计
 prompt_tokens	Integer	用户输入的 tokens 数量
 completion_tokens	Integer	模型输出的 tokens 数量
 total_tokens	Integer	总 tokens 数量
content_filter	List	返回内容安全的相关信息
 role	String	安全生效环节，包括
role = assistant 模型推理，
role = user 用户输入，
role = history 历史上下文
 level	Integer	严重程度 level 0-3，level 0表示最严重，3表示轻微
请求示例
import wave
import base64

from zhipuai import ZhipuAI

def save_audio_as_wav(audio_data, filepath):
    with wave.open(filepath, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(44100)
        wav_file.writeframes(audio_data)
    print(f"Audio saved to {filepath}")


client = ZhipuAI(api_key="YOUR API KEY") # 填写您自己的APIKey

response = client.chat.completions.create(
    model="glm-4-voice",  # 请填写您要调用的模型名称
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": "<base64_string>",
                        "format":"wav"
                }
            }
        ]
        },
    ],
    max_tokens=1024,
    stream=True
)

i = 1
for chunk in response:
    print(chunk.choices[0].delta)
    delta = chunk.choices[0].delta
    audio = chunk.choices[0].delta.audio
    if audio is not None:
        filename = "output" + str(i) + ".wav"
        audio_value_data = audio.data
        if audio_value_data is not None:
            decoded_data = base64.b64decode(audio_value_data)
            # 将解码的数据写入WAV文件
            with open(filename, 'wb') as wav_file:
                wav_file.write(decoded_data)
                i = i + 1
    else:
        content = delta.content
        print(content)
响应示例
data: {"id":"8313807536837492492","created":1706092316,"model":"glm-4-voice","choices":[{"index":0,"delta":{"role":"assistant","content":"好啊！有一天，一只小乌龟慢悠悠地在路上走"}}]}


data: {"id":"8313807536837492492","created":1706092316,"model":"glm-4-voice","choices":[{"index":0,"delta":{"role":"assistant","content":"突然，一只兔子飞快地跑过来，撞到了小乌龟的身上。小乌龟站起来，拍拍身上的土","audio":{"id":"c6d3b522-e6e5-4f90-b215-29ecd2a529d5","data":"<base64_string>","expires_at":1735011068}}}]}

data: {"id":"8313807536837492492","created":1705476637,"model":"glm-4-voice","choices":[{"index":0,"finish_reason":"stop","delta":{"role":"assistant","content":""}}],"usage":{"prompt_tokens":1037,"completion_tokens":37,"total_tokens":1074}}
多轮对话
音频对话实现多轮对话，目前只支持只支持通过audio.id的格式拼接，格式如下：

import wave
import base64

from zhipuai import ZhipuAI
def save_audio_as_wav(audio_data, filepath):
    with wave.open(filepath, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(44100)
        wav_file.writeframes(audio_data)
    print(f"Audio saved to {filepath}")


client = ZhipuAI(api_key="YOUR API KEY") # 填写您自己的APIKey

response = client.chat.completions.create(
    model="glm-4-voice",  # 请填写您要调用的模型名称
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": "<base64_string>",
                        "format":"wav"
                    }
                }
            ]
        },
        {
            "role": "assistant",
            "audio": {
                "id": "dc85d58d-b339-488e-ad95-2f45119517ff"
            }
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "不好笑，再讲一个"
                }
            ]
        },
    ],
    max_tokens=1024,
    stream=False
)
print(response)
# 5. 获取 audio 数据
audio_data = response.choices[0].message.audio['data']
decoded_data = base64.b64decode(audio_data)
# 6. 将解码的数据写入WAV文件
with open("output.wav", 'wb') as wav_file:
    wav_file.write(decoded_data)

## TTS

| TTS模块 | 平均耗时   | 测试句子数 |
| ------- | ---------- | ---------- |
| EdgeTTS | 0.837秒/句 | 3          |
| CogTTS  | 0.778秒/句 | 3          |
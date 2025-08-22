"""AutoGLM控制函数"""

import aiohttp
from plugins_func.register import register_function, ToolType, Action, ActionResponse


# 正确的函数注册方式 - 不要传递 parameters 参数
@register_function(
    name="autoglm_control",
    desc={
        "type": "function",
        "function": {
            "name": "autoglm_control",
            "description": "控制AutoGLM移动自动化代理执行任务",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["start_task", "get_status", "stop_task"],
                        "description": "要执行的操作：start_task(开始任务), get_status(获取状态), stop_task(停止任务)"
                    },
                    "task_description": {
                        "type": "string",
                        "description": "任务描述，当action为start_task时必需"
                    },
                    "task_id": {
                        "type": "string",
                        "description": "任务ID，当action为get_status或stop_task时必需"
                    }
                },
                "required": ["action"]
            }
        }
    },
    type=ToolType.MCP_CLIENT
)
async def autoglm_control(conn, action: str, task_description: str = None, task_id: str = None):
    """控制AutoGLM移动自动化代理"""

    try:
        config = conn.config.get("autoglm", {})
        if not config.get("enabled", False):
            return ActionResponse(
                action=Action.ERROR,
                response="AutoGLM功能未启用"
            )

        base_url = config.get("base_url", "http://8.141.113.229/mcp/http/")
        api_key = config.get("api_key")

        if not base_url or not api_key:
            return ActionResponse(
                action=Action.ERROR,
                response="AutoGLM配置不完整"
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            if action == "start_task":
                if not task_description:
                    return ActionResponse(
                        action=Action.ERROR,
                        response="开始任务需要提供task_description"
                    )

                url = f"{base_url.rstrip('/')}/api/v1/tasks"
                data = {
                    "description": task_description,
                    "type": "mobile_automation"
                }

                async with session.post(url, json=data, headers=headers) as resp:
                    if resp.status == 201:
                        result = await resp.json()
                        task_id = result.get("task_id")
                        return ActionResponse(
                            action=Action.RESPONSE,
                            response=f"任务已创建，ID: {task_id}"
                        )
                    else:
                        error_text = await resp.text()
                        return ActionResponse(
                            action=Action.ERROR,
                            response=f"创建任务失败: {error_text}"
                        )

            elif action == "get_status":
                if not task_id:
                    return ActionResponse(
                        action=Action.ERROR,
                        response="获取状态需要提供task_id"
                    )

                url = f"{base_url.rstrip('/')}/api/v1/tasks/{task_id}/status"

                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        status = result.get("status", "unknown")
                        progress = result.get("progress", 0)
                        return ActionResponse(
                            action=Action.RESPONSE,
                            response=f"任务状态: {status}, 进度: {progress}%"
                        )
                    else:
                        error_text = await resp.text()
                        return ActionResponse(
                            action=Action.ERROR,
                            response=f"获取状态失败: {error_text}"
                        )

            elif action == "stop_task":
                if not task_id:
                    return ActionResponse(
                        action=Action.ERROR,
                        response="停止任务需要提供task_id"
                    )

                url = f"{base_url.rstrip('/')}/api/v1/tasks/{task_id}/stop"

                async with session.post(url, headers=headers) as resp:
                    if resp.status == 200:
                        return ActionResponse(
                            action=Action.RESPONSE,
                            response="任务已停止"
                        )
                    else:
                        error_text = await resp.text()
                        return ActionResponse(
                            action=Action.ERROR,
                            response=f"停止任务失败: {error_text}"
                        )

            else:
                return ActionResponse(
                    action=Action.ERROR,
                    response=f"不支持的操作: {action}"
                )

    except Exception as e:
        return ActionResponse(
            action=Action.ERROR,
            response=f"AutoGLM控制出错: {str(e)}"
        )

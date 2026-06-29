"""
DeepSeek API 客户端 — 使用 OpenAI 兼容接口
支持思考模式（DeepSeek-V4-Pro reasoning）
"""
import logging
from openai import OpenAI

from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    LLM_TEMPERATURE, LLM_TIMEOUT, LLM_MAX_RETRIES,
)

logger = logging.getLogger(__name__)


class LLMClient:
    """DeepSeek API 客户端，支持思考模式与自动重试。"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.base_url = base_url or DEEPSEEK_BASE_URL
        self.model = model or DEEPSEEK_MODEL

        if not self.api_key:
            raise ValueError(
                "DeepSeek API key 未设置。"
                "请将密钥写入同目录下的 apikey.txt，或设置环境变量 DEEPSEEK_API_KEY。"
            )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=LLM_TIMEOUT,
            max_retries=LLM_MAX_RETRIES,
        )

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = None,
        stream: bool = False,
        thinking: bool = True,
    ) -> str:
        """
        调用 DeepSeek API 生成回复。

        重试由 OpenAI SDK 内置的 max_retries 处理（连接错误/429/5xx），
        非 retryable 错误（401/400 等）会立即抛出，不做无意义重试。

        Args:
            system_prompt: 系统提示词
            user_message: 用户输入
            temperature: 生成温度
            stream: 是否流式输出
            thinking: 是否启用思考模式（参数抽取等简单任务可关闭以加速）

        Returns:
            生成的文本内容
        """
        temperature = temperature if temperature is not None else LLM_TEMPERATURE

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        logger.info("调用 DeepSeek API...")

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        if thinking:
            kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
            kwargs["reasoning_effort"] = "high"

        response = self.client.chat.completions.create(**kwargs)

        if stream:
            return self._handle_stream(response)

        # 非流式：提取内容
        content = response.choices[0].message.content

        # 记录思考内容（如果有）
        if hasattr(response.choices[0].message, "reasoning_content"):
            reasoning = response.choices[0].message.reasoning_content
            if reasoning:
                logger.debug(f"思考过程:\n{reasoning[:500]}...")

        logger.info("API 调用成功")
        return content

    def generate_with_history(
        self,
        system_prompt: str,
        messages: list,
        temperature: float = None,
    ) -> str:
        """
        带对话历史的生成（用于验证失败后的自我修正）。

        Args:
            system_prompt: 系统提示词
            messages: 对话历史 [{"role": ..., "content": ...}, ...]
            temperature: 生成温度

        Returns:
            生成的文本内容
        """
        temperature = temperature if temperature is not None else LLM_TEMPERATURE

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        response = self.client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            temperature=temperature,
            stream=False,
            extra_body={"thinking": {"type": "enabled"}},
            reasoning_effort="high",
        )
        return response.choices[0].message.content

    @staticmethod
    def _handle_stream(stream_response) -> str:
        """处理流式响应，收集完整内容。"""
        content_parts = []
        for chunk in stream_response:
            delta = chunk.choices[0].delta
            if delta.content:
                print(delta.content, end="", flush=True)
                content_parts.append(delta.content)
        print()  # 换行
        return "".join(content_parts)

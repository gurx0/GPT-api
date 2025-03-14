import aiohttp
import base64
import logging
import os
from providers.response import parse_response

logger = logging.getLogger(__name__)

class AnthropicAPI:
    """
        Args: 
            api_key (str): Your API key for acces model
            model (str): claude-3-haiku-20240307, claude-3-sonnet-20240229, claude-3-opus-20240229, claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022, claude-3-7-sonnet-20250219
            base_url (str): Base URL API. Defaults to "https://api.proxyapi.ru"
            max_tokens (int, optional): Max generate new tokens. Defaults to 1024
    """
    def __init__(
            self,
            api_key: str,
            model:str,
            base_url:str = "https://api.proxyapi.ru",
            max_tokens: int = 1024,
        ):
        self.max_tokens = max_tokens
        # <DATA> #
        self.url = f"{base_url}/anthropic/v1/messages"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Anthropic-Version": "2023-06-01"
        }
        self.body = {
            "model": model,
            "messages": [],
            "max_tokens": max_tokens
        }
        self.context = self.ContextHandler(self)

    class ContextHandler:
        def __init__(self, parent):
            self.parent = parent

        def add(self, text: str, image:bytes=None, model:bool=False) -> None:
            """Добавить сообщение пользователя к истории"""
            role = "assistant" if model else "user"
            if image:
                img_base64= base64.b64encode(image).decode('utf-8')
                content = [
                    {"type": "image", "source": {"type": "base64","media_type": "image/jpeg","data": img_base64}},
                    {"type": "text", "text": text}
                ]
            else:
                content = text 
            self.parent.body['messages'].append(
                {"role": role, "content": content}
            )
        
        def set(self, messages: list) -> None:
            """Установить полную историю сообщений"""
            self.parent.body['messages'] = messages
        
        def clear(self) -> None:
            """Очистите историю диалога"""
            self.parent.body['messages'] = []      

    async def send(self) -> tuple:
        logger.debug(self.url)
        logger.debug(self.headers)
        logger.debug(self.body)
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.url, headers=self.headers, json=self.body) as response:
                    logger.info(f"Status: {response.status}")
                    if response.status == 200:
                        response_data = await response.json()
                        return parse_response(response_data)

            except aiohttp.ClientError as e:
                logger.error("Client error: %s", e)
            except Exception as e:
                logger.error(f"Exception error: {str(e)}")
            return None
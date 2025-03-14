import aiohttp
import base64
import logging
import os
from providers.response import parse_response

logger = logging.getLogger(__name__)


class GeminiAPI:
    """
        Args: 
            api_key (str): Your API key for acces model
            model (str): gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash
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
        self.url = f"{base_url}/google/v1/models/{model}:generateContent"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        self.body = {"contents": []}
        self.context = self.ContextHandler(self)

    class ContextHandler:
        def __init__(self, parent):
            self.parent = parent

        def add(self, text: str, model:bool=False) -> None:
            """Добавить сообщение к истории"""
            role = "model" if model else "user"
            self.parent.body['contents'].append({"role": role, "parts": [{"text": text}]})

        def set(self, messages: list) -> None:
            """Установить полную историю сообщений"""
            self.parent.body = {"contents": messages}
        
        def clear(self) -> None:
            """Очистите историю диалога"""
            self.parent.body = {"contents": []}

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
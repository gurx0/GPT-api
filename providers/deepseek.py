import aiohttp
import base64
import logging
import os
import json
from providers.response import parse_response
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


class DeepSeekAPI:
    """
        Args: 
            api_key (str): Your API key for acces model
            model (str): deepseek-chat, deepseek-reasoner
            base_url (str): Base URL API. Defaults to "https://api.proxyapi.ru"
            max_tokens (int, optional): Max generate new tokens. Defaults to 1024
    """
    def __init__(
            self,
            base_url:str,
            api_key: str,
            model:str,
            max_tokens: int = 1024,
        ):
        self.max_tokens = max_tokens
        # <DATA> #
        self.url = f"{base_url}/deepseek/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
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

        def add(self, text: str, image=None, model:bool=False) -> None:
            """Добавить сообщение пользователя к истории"""
            role = "assistant" if model else "user"
            self.parent.body['messages'].append(
                {"role": role, "content": text}
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
        self.body['stream'] = False
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
        
    async def stream(self) -> AsyncGenerator[dict, None]:
        logger.debug(self.url)
        logger.debug(self.headers)
        self.body['stream'] = True
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.url, headers=self.headers, json=self.body) as response:
                    logger.info(f"Status: {response.status}")
                    if response.status != 200:
                        try:
                            error = await response.json()
                            yield {"error": error, "status": response.status}
                            return
                        except:
                            text = await response.text()
                            yield {"error": text, "status": response.status}
                            return

                    # Стримим ответ построчно
                    buffer = ""
                    async for chunk in response.content.iter_any():
                        if not chunk:
                            continue

                        # Декодируем и добавляем в буфер
                        buffer += chunk.decode('utf-8', errors='replace')                        
                        # Разделяем события по двойным переносам строк
                        while "\n\n" in buffer:
                            event, buffer = buffer.split("\n\n", 1)
                            
                            # Убираем префикс 'data: ' и парсим JSON
                            if event.startswith('data:'):
                                json_str = event[5:].strip()
                                if json_str == "[DONE]":
                                    continue
                                
                                try:
                                    data = json.loads(json_str)
                                    yield parse_response(data)
                                except json.JSONDecodeError as e:
                                    logger.error(f"JSON decode error: {e}")
                                    logger.debug(f"Raw data: {json_str}")
                                except Exception as e:
                                    logger.error(f"Error parsing response: {e}")

            except aiohttp.ClientError as e:
                logger.error("Client error: %s", e)
                yield {"error": str(e)}
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                yield {"error": str(e)}

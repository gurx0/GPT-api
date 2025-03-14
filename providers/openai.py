import aiohttp
import base64
import logging
import os
import json
from typing import AsyncGenerator
from providers.response import parse_response


logger = logging.getLogger(__name__)

class OpenaiAPI:
    """
        Args: 
            api_key (str): Your API key for acces model
            model (str): gpt-3.5-turbo, gpt-4, gpt-4-turbo, gpt-4o, gpt-4o-audio-preview, gpt-4o-mini, gpt-4o-mini-audio-preview, o1, o1-mini, o3-mini
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
        self.url = f"{base_url}/openai/v1/chat/completions"
        self.url_audio = f"{base_url}/openai/v1/audio/speech"
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

        def add(self, text:str, image:bytes=None, detail:str="low", model:bool=False) -> None:
            """Добавить сообщение к истории"""
            role = "assistant" if model else "user"
            if image:
                img_base64= base64.b64encode(image).decode('utf-8')
                content = [
                    {"type": "text", "text": text}, 
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + img_base64, "detail": "high"}}
                ]
            else:
                content = text 
            self.parent.body['messages'].append(
                {"role": role, "content": content}
            )

        def add_audio(self, data:str) -> None:
            """Добавить аудио к истории"""
            self.parent.body['messages'].append({
                "role": "assistant",
                "audio": {
                    "id": data
                }
            })
        
        def set(self, messages: list) -> None:
            """Установить полную историю сообщений"""
            self.parent.body['messages'] = messages
        
        def clear(self) -> None:
            """Очистите историю диалога"""
            self.parent.body['messages'] = []

    async def send(self) -> tuple:
        logger.debug(self.url)
        logger.debug(self.headers)
        self.body['stream'] = False
        if self.body['model'] in ['gpt-4o-mini-audio-preview', 'gpt-4o-audio-preview']:
            self.body["modalities"] = ["text", "audio"]
            self.body["audio"] = { "voice": "shimmer", "format": "wav" }
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

class OpenaiAudioAPI:
    """
        Args: 
            api_key (str): Your API key for acces model
            base_url (str): Base URL API. Defaults to "https://api.proxyapi.ru"
            voice (str): alloy, echo, fable, onyx, nova, shimmer
    """
    def __init__(
            self,
            base_url:str,
            api_key: str,
            voice:str="onyx"
        ):
        # <DATA> #
        self.url = f"{base_url}/openai/v1/audio/"
        self.api_key = api_key
        self.voice = voice
    
    async def stt(self, audio_path: str, orig_lang=False) -> tuple:
        url = self.url + ("transcriptions" if orig_lang else "translations")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        form_data = aiohttp.FormData()
        form_data.add_field(
            'file',
            open(audio_path, 'rb'),
            filename=os.path.basename(audio_path),
            content_type='audio/mpeg'
        )
        form_data.add_field('model', 'whisper-1')
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, data=form_data) as response:
                    logger.info(f"Status: {response.status}")
                    if response.status == 200:
                        response_data = await response.json()
                        text = response_data['text']
                        logger.info(text)
                        return text              
            except aiohttp.ClientError as e:
                logger.error("Client error: %s", e)
            except Exception as e:
                logger.error(f"Exception error: {str(e)}")
            return None
    
    async def tts(self, text:str, model:str="tts-1", voice:str=None):
        """alloy, echo, fable, onyx, nova, shimmer"""
        if voice is None:
            voice = self.voice
            
        url = self.url + "speech"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        } 
        body = {
            "model": model,
            "input": text,
            "voice": voice
        }
        logger.debug(url)
        logger.debug(headers)
        logger.debug(body)
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, json=body) as response:
                    logger.info(response.status)
                    if response.status == 200:
                        chunks = []
                        async for chunk in response.content.iter_chunked(1024):
                            chunks.append(chunk)
                        return chunks

            except aiohttp.ClientError as e:
                logger.error("Client error: %s", e)
            except Exception as e:
                logger.error(f"Exception error: {str(e)}")
    

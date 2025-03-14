from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class AudioContent:
    id: Optional[str] = None
    data: Optional[str] = None
    transcript: Optional[str] = None

@dataclass
class UnifiedResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    finish_reason: str
    total_tokens: Optional[int] = None
    audio: Optional[AudioContent] = None
    raw_data: Optional[Dict[str, Any]] = None

def parse_response(response: dict) -> UnifiedResponse:
    content = ""
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    model = "unknown"
    finish_reason = "ongoing"
    audio_obj = None
    
    # Gemini API
    if 'candidates' in response:
        candidate = response['candidates'][0]
        content = candidate['content']['parts'][0]['text']
        usage = response.get('usageMetadata', {})
        prompt_tokens = usage.get('promptTokenCount', 0)
        completion_tokens = usage.get('candidatesTokenCount', 0)
        model = response.get('modelVersion', 'gemini-unknown')
        finish_reason = candidate.get('finishReason', 'unknown')
    
    # Anthropic API
    elif 'type' in response and response.get('role') == 'assistant':
        content = response['content'][0]['text']
        usage = response.get('usage', {})
        prompt_tokens = usage.get('input_tokens', 0)
        completion_tokens = usage.get('output_tokens', 0)
        model = response.get('model', 'claude-unknown')
        finish_reason = response.get('stop_reason', 'unknown')
    
    # DeepSeek/OpenAI API
    if 'choices' in response:
        model = response.get('model', 'unknown-model')
        current_usage = response.get('usage') or {}
        
        # Обрабатываем все choices
        for choice in response.get('choices', []):
            # Потоковые чанки с delta
            delta = choice.get('delta', {})
            if delta:
                content += delta.get('content', '')

            # Обычные ответы и аудио
            elif 'message' in choice:
                message = choice.get('message', {})
                if 'audio' in message:
                    audio_data = message.get('audio', {})
                    audio_obj = AudioContent(
                        id=audio_data.get('id'),
                        data=audio_data.get('data'),
                        transcript=audio_data.get('transcript')
                    )
                    content = audio_obj.transcript or ''
                else:
                    content = message.get('content', '')
                
                finish_reason = choice.get('finish_reason', 'unknown')

        # Обработка usage
        prompt_tokens = current_usage.get('prompt_tokens', 0)
        completion_tokens = current_usage.get('completion_tokens', 0)
        total_tokens = current_usage.get('total_tokens', 0)

    total_tokens = None
    # Для Gemini
    if 'usageMetadata' in response:
        gemini_usage = response['usageMetadata'] or {}
        total_tokens = gemini_usage.get('totalTokenCount', 0)

    # Для OpenAI/DeepSeek
    if not total_tokens and 'usage' in response:
        openai_usage = response['usage'] or {}
        total_tokens = openai_usage.get('total_tokens', 0)

    # Общий случай для Anthropic и других
    if not total_tokens:
        total_tokens = prompt_tokens + completion_tokens
    
    if finish_reason is None:
        finish_reason = "unknow"

    return UnifiedResponse(
        content=content.strip(),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        model=model,
        finish_reason=finish_reason.lower(),
        audio=audio_obj,
        raw_data=response
    )
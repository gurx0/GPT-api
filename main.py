import logging
import asyncio
import base64
import pyaudio
import wave
import io
from playsound import playsound
import cv2
import keyboard
from env import BASE_URL, API_KEY
from providers import UnifiedResponse, OpenaiAudioAPI, OpenaiAPI, DeepSeekAPI, GeminiAPI, AnthropicAPI

AUDIO_IN = False
AUDIO_OUT = False

logging.root.setLevel(logging.NOTSET)
logging.basicConfig(
    level="DEBUG",
    format="%(asctime)s - %(name)s >> %(levelname)s [ %(message)s ]",
    datefmt='%d-%b-%y %H:%M:%S',
    force=True,
    handlers=[
        logging.FileHandler("data/root.log"),
        logging.StreamHandler()
    ]
)

py_audio = pyaudio.PyAudio()

def capture_photo(filename='data/photo.jpg'):
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        logging.error("Ошибка: не удалось открыть веб-камеру")
        return

    ret, frame = cap.read()

    if not ret:
        logging.error("Ошибка: не удалось захватить изображение")
    else:
        cv2.imwrite(filename, frame)

    cap.release()

def play(audio_base64:str=None, audio_bytes_list:list=None):
    chunk = 1024
    if not (audio_base64 is None):
        audio_bytes = base64.b64decode(audio_base64)
        audio_stream = io.BytesIO(audio_bytes)
        audio = wave.open(audio_stream, "rb")
        stream = py_audio.open(format=py_audio.get_format_from_width(audio.getsampwidth()),
                        channels=audio.getnchannels(),
                        rate=audio.getframerate(),
                        output=True)
        data = audio.readframes(chunk)
        while data:
            stream.write(data)
            data = audio.readframes(chunk)
        stream.stop_stream()
        stream.close()

    if not (audio_bytes_list is None):
        with open("data/response.mp3", "wb") as f:
            for data in audio_bytes_list:
                f.write(data)
        playsound("data/response.mp3")


def record_audio(filename):
    chunk = 1024  # Размер блока
    format = pyaudio.paInt16  # Формат записи
    channels = 1  # Моно
    rate = 44100  # Частота
    stream = py_audio.open(format=format,channels=channels,rate=rate,input=True,frames_per_buffer=chunk)
    print("Нажмите и удерживайте 'r' для записи, отпустите для завершения.")
    frames = []
    while True:
        if keyboard.is_pressed('r'):
            data = stream.read(chunk)
            frames.append(data)
        else:
            if frames:
                break

    stream.stop_stream()
    stream.close()
    wf = wave.open(filename, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(py_audio.get_sample_size(format))
    wf.setframerate(rate)
    wf.writeframes(b''.join(frames))
    wf.close()

from RealtimeTTS import TextToAudioStream, SystemEngine, AzureEngine, ElevenlabsEngine
engine = SystemEngine() # replace with your TTS engine
stream = TextToAudioStream(engine)

async def ag_text(g):
    async for chunk in g:
        yield chunk.content


async def main():
    audio_model = OpenaiAudioAPI(base_url=BASE_URL, api_key=API_KEY)
    model = DeepSeekAPI(base_url=BASE_URL, api_key=API_KEY, model="deepseek-chat")
    while True:
        try:
            path_photo = None
            photo = None
            if AUDIO_IN:
                path_audio = "data/request.wav"
                path_photo = "data/request.jpg"
                record_audio(path_audio)
                capture_photo(path_photo)
                request = await audio_model.stt(path_audio)
            else: 
                request = input("Введите запрос: ")

            if path_photo:
                with open(path_photo, "rb") as f:
                    photo = f.read()

            model.context.add(request, image=photo)
            stream.feed(ag_text(model.stream()))
            stream.play_async()

            continue
            logging.info(response.content)
            logging.info(response.model)
            if response.audio:
                logging.info(response.audio.id)
                logging.info(response.model)
                play(audio_base64=response.audio.data)
                model.context.add_audio(response.audio.id)
            else:
                model.context.add(response.content, model=True)
                if AUDIO_OUT:
                    sound_bytes = await audio_model.tts(response.content, voice="onyx")
                    play(audio_bytes_list=sound_bytes)

        except KeyboardInterrupt:
            break

asyncio.run(main())
py_audio.terminate()
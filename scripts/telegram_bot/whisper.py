"""
Transcripción de voz con Groq Whisper large-v3-turbo.
Convierte archivos de audio (ogg/mp3/wav) a texto.
"""
import os, httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

GROQ_KEY = os.getenv('GROQ_API_KEY', '')
GROQ_URL = 'https://api.groq.com/openai/v1/audio/transcriptions'
MODELO   = 'whisper-large-v3-turbo'


def transcribir(audio_bytes: bytes, nombre_archivo: str = 'audio.ogg') -> str | None:
    """
    Transcribe audio con Groq Whisper.

    Args:
        audio_bytes: bytes del archivo de audio
        nombre_archivo: nombre del archivo (extensión importa para detección de formato)

    Returns:
        Texto transcrito, o None si falla.
    """
    if not GROQ_KEY:
        return None

    try:
        resp = httpx.post(
            GROQ_URL,
            headers={'Authorization': f'Bearer {GROQ_KEY}'},
            files={'file': (nombre_archivo, audio_bytes, 'audio/ogg')},
            data={
                'model':           MODELO,
                'language':        'es',
                'response_format': 'text',
            },
            timeout=30
        )
        resp.raise_for_status()
        return resp.text.strip()
    except Exception as e:
        return None

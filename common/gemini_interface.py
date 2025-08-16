from google import genai
import os
import json
import time
import random

# Suponiendo que tienes la API Key en una variable de entorno
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

client = genai.Client(api_key=API_KEY)

# Modelos disponibles (esto es un ejemplo, consulta la documentación de Gemini)
GENERATION_MODEL = "gemini-2.5-flash-preview-04-17" # O el modelo que prefieras

def ask_gemini(prompt: str, task_hint: str = "", max_retries: int = 8, base_delay: float = 1.0):
    """
    Función genérica para hacer una pregunta a Gemini con reintentos automáticos.
    task_hint es para ayudar a seleccionar una respuesta mock durante el desarrollo.
    max_retries: número máximo de reintentos
    base_delay: tiempo base de espera en segundos
    """
    print(f"\n\n-------------------------------------------------------------------")
    print(f"\n--- Pregunta a Gemini ({task_hint if task_hint else 'general'}) ---")
    print(f"Prompt: {prompt}") # Imprime solo una parte del prompt para brevedad
    print(f"\n-------------------------------------------------------------------")
    
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(model=GENERATION_MODEL, contents=prompt)
            response_text = response.text

            if not response.text:
                # Manejar el caso de que no haya contenido o la respuesta esté bloqueada.
                print("Advertencia: Respuesta vacía o bloqueada por configuración de seguridad.")
                response_text = "No se pudo obtener respuesta del LLM."

            print(f"\n-------------------------------------------------------------------")
            print(f"Respuesta de Gemini: {response_text}")
            print(f"\n-------------------------------------------------------------------\n\n")
            return response_text
            
        except Exception as e:
            print(f"Error al llamar a la API de Gemini (intento {attempt + 1}/{max_retries + 1}): {e}")
            
            if attempt < max_retries:
                # Calcular delay con backoff exponencial y jitter
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"Reintentando en {delay:.2f} segundos...")
                time.sleep(delay)
            else:
                print("Se agotaron todos los reintentos.")
                return f"Error después de {max_retries + 1} intentos: {e}"
    
def parse_gemini_json_response(response_text: str) -> dict:
    """
    Toma el texto de la respuesta de Gemini que venga de la forma: ```json``` y lo parsea como JSON.
    """
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        try:
            return json.loads(response_text[response_text.find('```json')+7:response_text.rfind('```')+len('```')-3])
        except json.JSONDecodeError:
            print(f"Error al parsear la respuesta JSON de Gemini: {response_text}")
            return None
        
def ask_gemini_json(prompt: str, task_hint: str = "", config: dict = None, max_retries: int = 8, base_delay: float = 1.0):
    """
    Función para hacer una pregunta a Gemini y obtener una respuesta en formato JSON con reintentos automáticos.
    max_retries: número máximo de reintentos
    base_delay: tiempo base de espera en segundos
    """
    print(f"\n\n-------------------------------------------------------------------")
    print(f"\n--- Pregunta a Gemini JSON ({task_hint if task_hint else 'general'}) ---")
    print(f"Prompt: {prompt}")
    print(f"\n-------------------------------------------------------------------")
    
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=GENERATION_MODEL,
                contents=prompt,
                config=config
            )
            response_text = response.text
            if not response_text:
                print("Advertencia: Respuesta vacía o bloqueada por configuración de seguridad.")
                print(f"Respuesta: {response.text}")
                return None

            print(f"\n-------------------------------------------------------------------")
            print(f"Respuesta JSON de Gemini: {response_text}")
            print(f"\n-------------------------------------------------------------------\n\n")
            
            return json.loads(response_text)
            
        except Exception as e:
            print(f"Error al llamar a la API de Gemini (intento {attempt + 1}/{max_retries + 1}): {e}")
            
            if attempt < max_retries:
                # Calcular delay con backoff exponencial y jitter
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"Reintentando en {delay:.2f} segundos...")
                time.sleep(delay)
            else:
                print("Se agotaron todos los reintentos.")
                return None
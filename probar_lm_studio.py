from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)

respuesta = client.chat.completions.create(
    model="Qwen2.5-VL-3B-Instruct",
    messages=[
        {
            "role": "system",
            "content": "Eres un tutor educativo."
        },
        {
            "role": "user",
            "content": "Genera una pregunta de seleccion multiple sobre derivadas con 4 opciones y di cual es la correcta."
        }
    ],
    temperature=0.7
)

print(respuesta.choices[0].message.content)
from groq import Groq
from config.settings import GROQ_API_KEY, MODEL_NAME

client = Groq(api_key=GROQ_API_KEY)

def generate_explanation(prompt: str, max_tokens: int = 800):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content
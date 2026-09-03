import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_llm(temperature: float = 0.2) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:20128/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "ganti-dengan-api-key"),
        model=os.getenv("MODEL_NAME", "ganti-dengan-model"),
        temperature=temperature,
    )

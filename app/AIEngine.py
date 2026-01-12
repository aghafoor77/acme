import os

from dotenv import load_dotenv
from openai import AzureOpenAI


class AIEngine:
    def __init__(self):
        load_dotenv()
        self.AZURE_OPENAI_KEY = os.environ["AZURE_OPENAI_KEY"]
        self.AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
        self.AZURE_OPENAI_API_VERSION = os.environ["AZURE_OPENAI_API_VERSION"]
        self.AZURE_OPENAI_ENGINE = os.environ["AZURE_OPENAI_ENGINE"]

    def create_ai_cient(self):
        # Initialize OpenAI client
        client = AzureOpenAI(
            api_version=self.AZURE_OPENAI_API_VERSION,
            azure_endpoint=self.AZURE_OPENAI_ENDPOINT,
            api_key=self.AZURE_OPENAI_KEY,
        )
        return client

    def generate_with_llm(self, prompt, client):
        """Generate text with GPT-4 given a prompt."""
        response = client.chat.completions.create(
            model=self.AZURE_OPENAI_ENGINE,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior security expert specializing in API testing. "
                        "Your job is to generate rigorous vulnerability test cases for REST APIs, "
                        "You provide the output in a ready-to-use Postman collection format "
                    ),
                },
                {"role": "user", "content": prompt},
                {
                    "role": "user",
                    "content": "Generate only postman collection without any other description and explaination",
                },
            ],
            temperature=0.7,
            max_tokens=5000,
        )
        return response.choices[0].message.content.strip()

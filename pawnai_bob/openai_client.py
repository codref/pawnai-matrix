import json
import logging
from openai import OpenAI

log = logging.getLogger(__name__)


class OpenAIClient:
    """OpenAI-compatible client that routes queries through the PawnAgent litellm proxy."""

    def __init__(self, settings: dict, room_id: str) -> None:
        self.session_id = room_id
        self.llm_model = settings.get('openai.default_llm_model', 'pawn-agent')
        self.prompt = settings.get('openai.default_prompt', '')
        self.context_length = settings.get('openai.default_context_length', 1500)
        self.chat_mode = 'default'

        self._openai = OpenAI(
            base_url=settings.get('openai.url', 'http://localhost:4000'),
            api_key=settings.get('openai.api_key') or 'none',
        )
        self.chat_engine = self

    def chat(self, message: str) -> str:
        response = self._openai.chat.completions.create(
            model=self.llm_model,
            messages=[{'role': 'user', 'content': message}],
            user=self.session_id,
        )
        return response.choices[0].message.content

    def reset_chat_engine(self):
        self._openai.chat.completions.create(
            model=self.llm_model,
            messages=[{'role': 'user', 'content': '/reset'}],
            user=self.session_id,
        )

    def set_prompt(self, prompt: str):
        self.prompt = prompt

    def set_llm_model(self, model: str):
        self.llm_model = model

    def set_context_length(self, token_limit: int):
        self.context_length = token_limit

    def set_chat_mode(self, mode: str):
        self.chat_mode = mode

    def toJSON(self) -> str:
        return json.dumps({
            'llm_model': self.llm_model,
            'prompt': self.prompt,
            'context_length': self.context_length,
            'chat_mode': self.chat_mode,
        }, indent=2)

    def fromJSON(self, json_string: str):
        obj = json.loads(json_string)
        self.llm_model = obj.get('llm_model', self.llm_model)
        self.prompt = obj.get('prompt', self.prompt)
        self.context_length = obj.get('context_length', self.context_length)
        self.chat_mode = obj.get('chat_mode', self.chat_mode)
        return self

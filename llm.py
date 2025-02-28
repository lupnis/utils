from httpx import Client, Timeout, URL
from openai import DEFAULT_MAX_RETRIES, NotGiven, NOT_GIVEN, OpenAI, Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from typing import Dict, List, Mapping, Optional, Union


class OpenAILLM:
    def __init__(self, *,
                 base_url: Optional[Union[str, URL]] = None,
                 api_key: Optional[str] = None,
                 default_model_name: Optional[str] = "x",
                 organization: Optional[str] = None,
                 project: Optional[str] = None,
                 websocket_base_url: Optional[Union[str, URL]] = None,
                 timeout: Optional[Union[float, Timeout,
                                         None, NotGiven]] = NOT_GIVEN,
                 max_retries: Optional[int] = DEFAULT_MAX_RETRIES,
                 default_headers: Optional[Mapping[str, str]] = None,
                 default_query: Optional[Mapping[str, object]] = None,
                 http_client: Optional[Client] = None,
                 _strict_response_validation: Optional[bool] = False):
        self.model = OpenAI(
            base_url=base_url,
            api_key=api_key,
            organization=organization,
            project=project,
            websocket_base_url=websocket_base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
            default_query=default_query,
            http_client=http_client,
            _strict_response_validation=_strict_response_validation
        )
        self.default_model_name = default_model_name

    async def chatStream(self, messages: List[Dict[str, str]], model: Optional[str] = None, **kwargs):
        completion_result = self.model.chat.completions.create(
            model=model if model else self.default_model_name,
            messages=messages,
            stream=True,
            **kwargs
        )
        for shard in completion_result:
            response_shard = await self._standard_stream_response(shard)
            yield response_shard
        return

    async def chatNoStream(self, messages: List[Dict[str, str]], model: Optional[str] = None, **kwargs):
        completion_result = self.model.chat.completions.create(
            model=model if model else self.default_model_name,
            messages=messages,
            stream=False,
            **kwargs
        )
        return await self._standard_no_stream_response(completion_result)

    def chat(self, messages: List[Dict[str, str]], model: Optional[str] = None, stream: Optional[bool] = False, **kwargs):
        if stream:
            return self.chatStream(messages=messages, model=model, **kwargs)
        else:
            return self.chatNoStream(messages=messages, model=model, **kwargs)

    async def _standard_stream_response(self, resp: Stream[ChatCompletionChunk]):
        return {
            "id": resp.id,
            "model": resp.model,
            "choices": [
                {
                    "index": choice.index,
                    "delta": {
                        "role": choice.delta.role,
                        "content": choice.delta.content
                    },
                    "finish_reason": choice.finish_reason
                }
                for choice in resp.choices
            ]
        }

    async def _standard_no_stream_response(self, resp: ChatCompletion):
        return {
            "id": resp.id,
            "object": resp.object,
            "created": resp.created,
            "model": resp.model,
            "choices": [
                {
                    "index": choice.index,
                    "message": {
                        "role": choice.message.role,
                        "content": choice.message.content,
                        "tool_calls": choice.message.tool_calls
                    },
                    "finish_reason": choice.finish_reason
                } for choice in resp.choices
            ],
            "usage": {
                "prompt_tokens": resp.usage.prompt_tokens,
                "completion_tokens": resp.usage.completion_tokens,
                "total_tokens": resp.usage.total_tokens
            }
        }

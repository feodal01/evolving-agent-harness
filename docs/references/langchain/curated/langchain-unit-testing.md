# Unit testing
Source: https://docs.langchain.com/oss/python/langchain/test/unit-testing

Test agent logic without API calls using fake chat models and in-memory persistence.

Unit tests exercise small, deterministic pieces of your agent in isolation. By replacing the real LLM with an in-memory fake (AKA fixture), you can script exact responses (text, tool calls, and errors) so tests are fast, free, and repeatable without API keys.

## Mock chat model

LangChain provides [`GenericFakeChatModel`](https://reference.langchain.com/python/langchain-core/language_models/fake_chat_models/GenericFakeChatModel) for mocking text responses. It accepts an iterator of responses ([`AIMessage`](https://reference.langchain.com/python/langchain-core/messages/ai/AIMessage) objects or strings) and returns one per invocation. It supports both regular and streaming usage.

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

model = GenericFakeChatModel(messages=iter([
    AIMessage(content="", tool_calls=[ToolCall(name="foo", args={"bar": "baz"}, id="call_1")]),
    "bar"
]))

model.invoke("hello")

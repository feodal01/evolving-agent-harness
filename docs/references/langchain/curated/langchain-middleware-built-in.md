# Prebuilt middleware
Source: https://docs.langchain.com/oss/python/langchain/middleware/built-in

Prebuilt middleware for common agent use cases

LangChain and [Deep Agents](/oss/python/deepagents/overview) provide prebuilt middleware for common use cases. Each middleware is production-ready and configurable for your specific needs.

## Provider-agnostic middleware

The following middleware work with any LLM provider:

| Middleware                              | Description                                                                  |
| --------------------------------------- | ---------------------------------------------------------------------------- |
| [Summarization](#summarization)         | Automatically summarize conversation history when approaching token limits.  |
| [Human-in-the-loop](#human-in-the-loop) | Pause execution for human approval of tool calls.                            |
| [Model call limit](#model-call-limit)   | Limit the number of model calls to prevent excessive costs.                  |
| [Tool call limit](#tool-call-limit)     | Control tool execution by limiting call counts.                              |
| [Model fallback](#model-fallback)       | Automatically fallback to alternative models when primary fails.             |
| [PII detection](#pii-detection)         | Detect and handle Personally Identifiable Information (PII).                 |
| [To-do list](#to-do-list)               | Equip agents with task planning and tracking capabilities.                   |
| [LLM tool selector](#llm-tool-selector) | Use an LLM to select relevant tools before calling main model.               |
| [Tool retry](#tool-retry)               | Automatically retry failed tool calls with exponential backoff.              |
| [Model retry](#model-retry)             | Automatically retry failed model calls with exponential backoff.             |
| [LLM tool emulator](#llm-tool-emulator) | Emulate tool execution using an LLM for testing purposes.                    |
| [Context editing](#context-editing)     | Manage conversation context by trimming or clearing tool uses.               |
| [Shell tool](#shell-tool)               | Expose a persistent shell session to agents for command execution.           |
| [File search](#file-search)             | Provide Glob and Grep search tools over filesystem files.                    |
| [Filesystem](#filesystem-middleware)    | Provide agents with a filesystem for storing context and long-term memories. |
| [Subagent](#subagent)                   | Add the ability to spawn subagents.                                          |

### Summarization

Automatically summarize conversation history when approaching token limits, preserving recent messages while compressing older context. Summarization is useful for the following:

* Long-running conversations that exceed context windows.
* Multi-turn dialogues with extensive history.
* Applications where preserving full conversation context matters.

**API reference:** [`SummarizationMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/SummarizationMiddleware)

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[your_weather_tool, your_calculator_tool],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger=("tokens", 4000),
            keep=("messages", 20),
        ),
    ],
)
```

<Accordion title="Configuration options">
  <Tip>
    The `fraction` conditions for `trigger` and `keep` (shown below) rely on a chat model's [profile data](/oss/python/langchain/models#model-profiles) if using `langchain>=1.1`. If data are not available, use another condition or specify manually:

    ```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
    from langchain.chat_models import init_chat_model

    custom_profile = {
        "max_input_tokens": 100_000,
        # ...
    }
    model = init_chat_model("gpt-5.4", profile=custom_profile)
    ```
  </Tip>

  <ParamField type="string | BaseChatModel">
    Model for generating summaries. Can be a model identifier string (e.g., `'openai:gpt-5.4-mini'`) or a `BaseChatModel` instance. See [`init_chat_model`](https://reference.langchain.com/python/langchain/chat_models/base/init_chat_model) for more information.
  </ParamField>

  <ParamField type="ContextSize | list[ContextSize] | None">
    Condition(s) for triggering summarization. Can be:

    * A single [`ContextSize`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/ContextSize) tuple (specified condition must be met)
    * A list of [`ContextSize`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/ContextSize) tuples (any condition must be met - OR logic)

    Condition should be one of the following:

    * `fraction` (float): Fraction of model's context size (0-1)
    * `tokens` (int): Absolute token count
    * `messages` (int): Message count

    At least one condition must be specified. If not provided, summarization will not trigger automatically.

    See the API reference for [`ContextSize`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/ContextSize) for more information.
  </ParamField>

  <ParamField type="ContextSize">
    How much context to preserve after summarization. Specify exactly one of:

    * `fraction` (float): Fraction of model's context size to keep (0-1)
    * `tokens` (int): Absolute token count to keep
    * `messages` (int): Number of recent messages to keep

    See the API reference for [`ContextSize`](https://reference.langchain.com/python/langchain/agents/middleware/summarization/ContextSize) for more information.
  </ParamField>

  <ParamField type="function">
    Custom token counting function. Defaults to character-based counting.
  </ParamField>

  <ParamField type="string">
    Custom prompt template for summarization. Uses built-in template if not specified. The template should include `{messages}` placeholder where conversation history will be inserted.
  </ParamField>

  <ParamField type="number">
    Maximum number of tokens to include when generating the summary. Messages will be trimmed to fit this limit before summarization.
  </ParamField>

  <ParamField type="string">
    **Deprecated:** Use `summary_prompt` to provide the full prompt instead.
  </ParamField>

  <ParamField type="number">
    **Deprecated:** Use `trigger: ("tokens", value)` instead. Token threshold for triggering summarization.
  </ParamField>

  <ParamField type="number">
    **Deprecated:** Use `keep: ("messages", value)` instead. Recent messages to preserve.
  </ParamField>
</Accordion>

<Accordion title="Full example">
  The summarization middleware monitors message token counts and automatically summarizes older messages when thresholds are reached.

  **Trigger conditions** control when summarization runs:

  * Single condition object (specified must be met)
  * Array of conditions (any condition must be met - OR logic)
  * Each condition can use `fraction` (of model's context size), `tokens` (absolute count), or `messages` (message count)

  **Keep condition** control how much context to preserve (specify exactly one):

  * `fraction` - Fraction of model's context size to keep
  * `tokens` - Absolute token count to keep
  * `messages` - Number of recent messages to keep

  ```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  from langchain.agents import create_agent
  from langchain.agents.middleware import SummarizationMiddleware


  # Single condition: trigger if tokens >= 4000
  agent = create_agent(
      model="gpt-5.4",
      tools=[your_weather_tool, your_calculator_tool],
      middleware=[
          SummarizationMiddleware(
              model="gpt-5.4-mini",
              trigger=("tokens", 4000),
              keep=("messages", 20),
          ),
      ],
  )

  # Multiple conditions: trigger if number of tokens >= 3000 OR messages >= 6
  agent2 = create_agent(
      model="gpt-5.4",
      tools=[your_weather_tool, your_calculator_tool],
      middleware=[
          SummarizationMiddleware(
              model="gpt-5.4-mini",
              trigger=[
                  ("tokens", 3000),
                  ("messages", 6),
              ],
              keep=("messages", 20),
          ),
      ],
  )

  # Using fractional limits
  agent3 = create_agent(
      model="gpt-5.4",
      tools=[your_weather_tool, your_calculator_tool],
      middleware=[
          SummarizationMiddleware(
              model="gpt-5.4-mini",
              trigger=("fraction", 0.8),
              keep=("fraction", 0.3),
          ),
      ],
  )
  ```
</Accordion>

### Human-in-the-loop

Pause agent execution for human approval, editing, or rejection of tool calls before they execute. [Human-in-the-loop](/oss/python/langchain/human-in-the-loop) is useful for the following:

* High-stakes operations requiring human approval (e.g. database writes, financial transactions).
* Compliance workflows where human oversight is mandatory.
* Long-running conversations where human feedback guides the agent.

**API reference:** [`HumanInTheLoopMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/human_in_the_loop/HumanInTheLoopMiddleware)

<Warning>
  Human-in-the-loop middleware requires a [checkpointer](/oss/python/langgraph/persistence#checkpoints) to maintain state across interruptions.
</Warning>

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver


def your_read_email_tool(email_id: str) -> str:
    """Mock function to read an email by its ID."""
    return f"Email content for ID: {email_id}"

def your_send_email_tool(recipient: str, subject: str, body: str) -> str:
    """Mock function to send an email."""
    return f"Email sent to {recipient} with subject '{subject}'"

agent = create_agent(
    model="gpt-5.4",
    tools=[your_read_email_tool, your_send_email_tool],
    checkpointer=InMemorySaver(),
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "your_send_email_tool": {
                    "allowed_decisions": ["approve", "edit", "reject"],
                },
                "your_read_email_tool": False,
            }
        ),
    ],
)
```

<Tip>
  For complete examples, configuration options, and integration patterns, see the [Human-in-the-loop documentation](/oss/python/langchain/human-in-the-loop).
</Tip>

<Callout icon="player-play">
  Watch this [video guide](https://www.youtube.com/watch?v=SpfT6-YAVPk) demonstrating Human-in-the-loop middleware behavior.
</Callout>

### Model call limit

Limit the number of model calls to prevent infinite loops or excessive costs. Model call limit is useful for the following:

* Preventing runaway agents from making too many API calls.
* Enforcing cost controls on production deployments.
* Testing agent behavior within specific call budgets.

**API reference:** [`ModelCallLimitMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/model_call_limit/ModelCallLimitMiddleware)

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model="gpt-5.4",
    checkpointer=InMemorySaver(),  # Required for thread limiting
    tools=[],
    middleware=[
        ModelCallLimitMiddleware(
            thread_limit=10,
            run_limit=5,
            exit_behavior="end",
        ),
    ],
)
```

<Callout icon="player-play">
  Watch this [video guide](https://www.youtube.com/watch?v=nJEER0uaNkE) demonstrating Model Call Limit middleware behavior.
</Callout>

<Accordion title="Configuration options">
  <ParamField type="number">
    Maximum model calls across all runs in a thread. Defaults to no limit.
  </ParamField>

  <ParamField type="number">
    Maximum model calls per single invocation. Defaults to no limit.
  </ParamField>

  <ParamField type="string">
    Behavior when limit is reached. Options: `'end'` (graceful termination) or `'error'` (raise exception)
  </ParamField>
</Accordion>

### Tool call limit

Control agent execution by limiting the number of tool calls, either globally across all tools or for specific tools. Tool call limits are useful for the following:

* Preventing excessive calls to expensive external APIs.
* Limiting web searches or database queries.
* Enforcing rate limits on specific tool usage.
* Protecting against runaway agent loops.

**API reference:** [`ToolCallLimitMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/tool_call_limit/ToolCallLimitMiddleware)

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[search_tool, database_tool],
    middleware=[
        # Global limit
        ToolCallLimitMiddleware(thread_limit=20, run_limit=10),
        # Tool-specific limit
        ToolCallLimitMiddleware(
            tool_name="search",
            thread_limit=5,
            run_limit=3,
        ),
    ],
)
```

<Callout icon="player-play">
  Watch this [video guide](https://www.youtube.com/watch?v=6gYlaJJ8t0w) demonstrating Tool Call Limit middleware behavior.
</Callout>

<Accordion title="Configuration options">
  <ParamField type="string">
    Name of specific tool to limit. If not provided, limits apply to **all tools globally**.
  </ParamField>

  <ParamField type="number">
    Maximum tool calls across all runs in a thread (conversation). Persists across multiple invocations with the same thread ID. Requires a checkpointer to maintain state. `None` means no thread limit.
  </ParamField>

  <ParamField type="number">
    Maximum tool calls per single invocation (one user message → response cycle). Resets with each new user message. `None` means no run limit.

    **Note:** At least one of `thread_limit` or `run_limit` must be specified.
  </ParamField>

  <ParamField type="string">
    Behavior when limit is reached:

    * `'continue'` (default) - Block exceeded tool calls with error messages, let other tools and the model continue. The model decides when to end based on the error messages.
    * `'error'` - Raise a `ToolCallLimitExceededError` exception, stopping execution immediately
    * `'end'` - Stop execution immediately with a `ToolMessage` and AI message for the exceeded tool call. Only works when limiting a single tool; raises `NotImplementedError` if other tools have pending calls.
  </ParamField>
</Accordion>

<Accordion title="Full example">
  Specify limits with:

  * **Thread limit** - Max calls across all runs in a conversation (requires checkpointer)
  * **Run limit** - Max calls per single invocation (resets each turn)

  Exit behaviors:

  * `'continue'` (default) - Block exceeded calls with error messages, agent continues
  * `'error'` - Raise exception immediately
  * `'end'` - Stop with ToolMessage + AI message (single-tool scenarios only)

  ```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  from langchain.agents import create_agent
  from langchain.agents.middleware import ToolCallLimitMiddleware


  global_limiter = ToolCallLimitMiddleware(thread_limit=20, run_limit=10)
  search_limiter = ToolCallLimitMiddleware(tool_name="search", thread_limit=5, run_limit=3)
  database_limiter = ToolCallLimitMiddleware(tool_name="query_database", thread_limit=10)
  strict_limiter = ToolCallLimitMiddleware(tool_name="scrape_webpage", run_limit=2, exit_behavior="error")

  agent = create_agent(
      model="gpt-5.4",
      tools=[search_tool, database_tool, scraper_tool],
      middleware=[global_limiter, search_limiter, database_limiter, strict_limiter],
  )
  ```
</Accordion>

### Model fallback

Automatically fallback to alternative models when the primary model fails. Model fallback is useful for the following:

* Building resilient agents that handle model outages.
* Cost optimization by falling back to cheaper models.
* Provider redundancy across OpenAI, Anthropic, etc.

**API reference:** [`ModelFallbackMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/model_fallback/ModelFallbackMiddleware)

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langchain.agents import create_agent
from langchain.agents.middleware import ModelFallbackMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[],
    middleware=[
        ModelFallbackMiddleware(
            "gpt-5.4-mini",
            "claude-3-5-sonnet-20241022",
        ),
    ],
)
```

<Callout icon="player-play">
  Watch this [video guide](https://www.youtube.com/watch?v=8rCRO0DUeIM) demonstrating Model Fallback middleware behavior.
</Callout>

<Accordion title="Configuration options">
  <ParamField type="string | BaseChatModel">
    First fallback model to try when the primary model fails. Can be a model identifier string (e.g., `'openai:gpt-5.4-mini'`) or a `BaseChatModel` instance.
  </ParamField>

  <ParamField type="string | BaseChatModel">
    Additional fallback models to try in order if previous models fail
  </ParamField>
</Accordion>

### PII detection

Detect and handle Personally Identifiable Information (PII) in conversations using configurable strategies. PII detection is useful for the following:

* Healthcare and financial applications with compliance requirements.
* Customer service agents that need to sanitize logs.
* Any application handling sensitive user data.

**API reference:** [`PIIMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/pii/PIIMiddleware)

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware

agent = create_agent(
    model="gpt-5.4",
    tools=[],
    middleware=[
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        PIIMiddleware("credit_card", strategy="mask", apply_to_input=True),
    ],
)
```

#### Custom PII types

You can create custom PII types by providing a `detector` parameter. This allows you to detect patterns specific to your use case beyond the built-in types.

**Three ways to create custom detectors:**

1. **Regex pattern string** - Simple pattern matching

2. **Custom function** - Complex detection logic with validation

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware
import re

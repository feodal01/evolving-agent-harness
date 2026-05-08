# Tools
Source: https://docs.langchain.com/oss/python/langchain/tools



Tools extend what [agents](/oss/python/langchain/agents) can do—letting them fetch real-time data, execute code, query external databases, and take actions in the world.

Under the hood, tools are callable functions with well-defined inputs and outputs that get passed to a [chat model](/oss/python/langchain/models). The model decides when to invoke a tool based on the conversation context, and what input arguments to provide.

<Tip>
  For details on how models handle tool calls, see [Tool calling](/oss/python/langchain/models#tool-calling). Trace tool calls and debug errors with [LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-langchain-tools)—follow the [tracing quickstart](/langsmith/trace-with-langchain) to get set up.
</Tip>

## Create tools

### Basic tool definition

The simplest way to create a tool is with the [`@tool`](https://reference.langchain.com/python/langchain-core/tools/convert/tool) decorator. By default, the function's docstring becomes the tool's description that helps the model understand when to use it:

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langchain.tools import tool

@tool
def search_database(query: str, limit: int = 10) -> str:
    """Search the customer database for records matching the query.

    Args:
        query: Search terms to look for
        limit: Maximum number of results to return
    """
    return f"Found {limit} results for '{query}'"
```

Type hints are **required** as they define the tool's input schema. The docstring should be informative and concise to help the model understand the tool's purpose.

<Note>
  **Server-side tool use:** Some chat models feature built-in tools (web search, code interpreters) that are executed server-side. See [Server-side tool use](#server-side-tool-use) for details.
</Note>

<Warning>
  Prefer `snake_case` for tool names (e.g., `web_search` instead of `Web Search`). Some model providers have issues with or reject names containing spaces or special characters with errors. Sticking to alphanumeric characters, underscores, and hyphens helps to improve compatibility across providers.
</Warning>

### Customize tool properties

#### Custom tool name

By default, the tool name comes from the function name. Override it when you need something more descriptive:

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
@tool("web_search")  # Custom name
def search(query: str) -> str:
    """Search the web for information."""
    return f"Results for: {query}"

print(search.name)  # web_search
```

#### Custom tool description

Override the auto-generated tool description for clearer model guidance:

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
@tool("calculator", description="Performs arithmetic calculations. Use this for any math problems.")
def calc(expression: str) -> str:
    """Evaluate mathematical expressions."""
    return str(eval(expression))
```

### Advanced schema definition

Define complex inputs with Pydantic models or JSON schemas:

<CodeGroup>
  ```python Pydantic model theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  from pydantic import BaseModel, Field
  from typing import Literal

  class WeatherInput(BaseModel):
      """Input for weather queries."""
      location: str = Field(description="City name or coordinates")
      units: Literal["celsius", "fahrenheit"] = Field(
          default="celsius",
          description="Temperature unit preference"
      )
      include_forecast: bool = Field(
          default=False,
          description="Include 5-day forecast"
      )

  @tool(args_schema=WeatherInput)
  def get_weather(location: str, units: str = "celsius", include_forecast: bool = False) -> str:
      """Get current weather and optional forecast."""
      temp = 22 if units == "celsius" else 72
      result = f"Current weather in {location}: {temp} degrees {units[0].upper()}"
      if include_forecast:
          result += "\nNext 5 days: Sunny"
      return result
  ```

  ```python JSON Schema theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  weather_schema = {
      "type": "object",
      "properties": {
          "location": {"type": "string"},
          "units": {"type": "string"},
          "include_forecast": {"type": "boolean"}
      },
      "required": ["location", "units", "include_forecast"]
  }

  @tool(args_schema=weather_schema)
  def get_weather(location: str, units: str = "celsius", include_forecast: bool = False) -> str:
      """Get current weather and optional forecast."""
      temp = 22 if units == "celsius" else 72
      result = f"Current weather in {location}: {temp} degrees {units[0].upper()}"
      if include_forecast:
          result += "\nNext 5 days: Sunny"
      return result
  ```
</CodeGroup>

### Reserved argument names

The following parameter names are reserved and cannot be used as tool arguments. Using these names will cause runtime errors.

| Parameter name | Purpose                                                                |
| -------------- | ---------------------------------------------------------------------- |
| `config`       | Reserved for passing `RunnableConfig` to tools internally              |
| `runtime`      | Reserved for `ToolRuntime` parameter (accessing state, context, store) |

To access runtime information, use the [`ToolRuntime`](https://reference.langchain.com/python/langchain/tools/#langchain.tools.ToolRuntime) parameter instead of naming your own arguments `config` or `runtime`.

## Access context

Tools are most powerful when they can access runtime information like conversation history, user data, and persistent memory. This section covers how to access and update this information from within your tools.

Tools can access runtime information through the [`ToolRuntime`](https://reference.langchain.com/python/langchain/tools/#langchain.tools.ToolRuntime) parameter, which provides:

| Component          | Description                                                                                                                 | Use case                                                    |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| **State**          | Short-term memory - mutable data that exists for the current conversation (messages, counters, custom fields)               | Access conversation history, track tool call counts         |
| **Context**        | Immutable configuration passed at invocation time (user IDs, session info)                                                  | Personalize responses based on user identity                |
| **Store**          | Long-term memory - persistent data that survives across conversations                                                       | Save user preferences, maintain knowledge base              |
| **Stream Writer**  | Emit real-time updates during tool execution                                                                                | Show progress for long-running operations                   |
| **Execution Info** | Identity and retry information for the current execution (thread ID, run ID, attempt number)                                | Access thread/run IDs, adjust behavior based on retry state |
| **Server Info**    | Server-specific metadata when running on LangGraph Server (assistant ID, graph ID, authenticated user)                      | Access assistant ID, graph ID, or authenticated user info   |
| **Config**         | [`RunnableConfig`](https://reference.langchain.com/python/langchain-core/runnables/config/RunnableConfig) for the execution | Access callbacks, tags, and metadata                        |
| **Tool Call ID**   | Unique identifier for the current tool invocation                                                                           | Correlate tool calls for logs and model invocations         |

```mermaid theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
graph LR
    %% Runtime Context
    subgraph "🔧 Tool Runtime Context"
        A[Tool Call] --> B[ToolRuntime]
        B --> C[State Access]
        B --> D[Context Access]
        B --> E[Store Access]
        B --> F[Stream Writer]
    end

    %% Available Resources
    subgraph "📊 Available Resources"
        C --> G[Messages]
        C --> H[Custom State]
        D --> I[User ID]
        D --> J[Session Info]
        E --> K[Long-term Memory]
        E --> L[User Preferences]
    end

    %% Tool Capabilities
    subgraph "⚡ Enhanced Tool Capabilities"
        M[Context-Aware Tools]
        N[Stateful Tools]
        O[Memory-Enabled Tools]
        P[Streaming Tools]
    end

    %% Connections
    G --> M
    H --> N
    I --> M
    J --> M
    K --> O
    L --> O
    F --> P

    classDef trigger fill:#F6FFDB,stroke:#6E8900,stroke-width:2px,color:#2E3900
    classDef process fill:#E5F4FF,stroke:#006DDD,stroke-width:2px,color:#030710
    classDef output fill:#EBD0F0,stroke:#885270,stroke-width:2px,color:#441E33
    classDef neutral fill:#F2FAFF,stroke:#40668D,stroke-width:2px,color:#2F4B68

    class A trigger
    class B,C,D,E,F process
    class G,H,I,J,K,L neutral
    class M,N,O,P output
```

### Short-term memory (State)

State represents short-term memory that exists for the duration of a conversation. It includes the message history and any custom fields you define in your [graph state](/oss/python/langgraph/graph-api#state).

<Info>
  Add `runtime: ToolRuntime` to your tool signature to access state. This parameter is automatically injected and hidden from the LLM - it won't appear in the tool's schema.
</Info>

#### Access state

Tools can access the current conversation state using `runtime.state`:

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langchain.tools import tool, ToolRuntime
from langchain.messages import HumanMessage

@tool
def get_last_user_message(runtime: ToolRuntime) -> str:
    """Get the most recent message from the user."""
    messages = runtime.state["messages"]

    # Find the last human message
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message.content

    return "No user messages found"

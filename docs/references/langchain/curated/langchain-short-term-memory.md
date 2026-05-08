# Short-term memory
Source: https://docs.langchain.com/oss/python/langchain/short-term-memory



## Overview

Memory is a system that remembers information about previous interactions. For AI agents, memory is crucial because it lets them remember previous interactions, learn from feedback, and adapt to user preferences. As agents tackle more complex tasks with numerous user interactions, this capability becomes essential for both efficiency and user satisfaction.

Short term memory lets your application remember previous interactions within a single thread or conversation.

<Note>
  A thread organizes multiple interactions in a session, similar to the way email groups messages in a single conversation.
</Note>

Conversation history is the most common form of short-term memory. Long conversations pose a challenge to today's LLMs; a full history may not fit inside an LLM's context window, resulting in an context loss or errors.

Even if your model supports the full context length, most LLMs still perform poorly over long contexts. They get "distracted" by stale or off-topic content, all while suffering from slower response times and higher costs.

Chat models accept context using [messages](/oss/python/langchain/messages), which include instructions (a system message) and inputs (human messages). In chat applications, messages alternate between human inputs and model responses, resulting in a list of messages that grows longer over time. Because context windows are limited, many applications can benefit from using techniques to remove or "forget" stale information.

<Tip>
  Need to remember information **across** conversations? Use [long-term memory](/oss/python/langchain/long-term-memory) to store and recall user-specific or application-level data across different threads and sessions.
</Tip>

## Usage

To add short-term memory (thread-level persistence) to an agent, you need to specify a `checkpointer` when creating an agent.

<Info>
  LangChain's agent manages short-term memory as a part of your agent's state.

  By storing these in the graph's state, the agent can access the full context for a given conversation while maintaining separation between different threads.

  State is persisted to a database (or memory) using a checkpointer so the thread can be resumed at any time.

  Short-term memory updates when the agent is invoked or a step (like a tool call) is completed, and the state is read at the start of each step.
</Info>

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver  # [!code highlight]


agent = create_agent(
    "gpt-5.4",
    tools=[get_user_info],
    checkpointer=InMemorySaver(),  # [!code highlight]
)

agent.invoke(
    {"messages": [{"role": "user", "content": "Hi! My name is Bob."}]},
    {"configurable": {"thread_id": "1"}},  # [!code highlight]
)
```

### In production

In production, use a checkpointer backed by a database:

```shell theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
pip install langgraph-checkpoint-postgres
```

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langchain.agents import create_agent

from langgraph.checkpoint.postgres import PostgresSaver  # [!code highlight]


DB_URI = "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable"
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup() # auto create tables in PostgreSQL
    agent = create_agent(
        "gpt-5.4",
        tools=[get_user_info],
        checkpointer=checkpointer,  # [!code highlight]
    )
```

<Note>
  For more checkpointer options including SQLite, Postgres, and Azure Cosmos DB, see the [list of checkpointer libraries](/oss/python/langgraph/persistence#checkpointer-libraries) in the Persistence documentation.
</Note>

## Customizing agent memory

By default, agents use [`AgentState`](https://reference.langchain.com/python/langchain/agents/middleware/types/AgentState) to manage short term memory, specifically the conversation history via a `messages` key.

You can extend [`AgentState`](https://reference.langchain.com/python/langchain/agents/middleware/types/AgentState) to add additional fields. Custom state schemas are passed to [`create_agent`](https://reference.langchain.com/python/langchain/agents/factory/create_agent) using the [`state_schema`](https://reference.langchain.com/python/langchain/middleware/#langchain.agents.middleware.AgentMiddleware.state_schema) parameter.

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langchain.agents import create_agent, AgentState
from langgraph.checkpoint.memory import InMemorySaver


class CustomAgentState(AgentState):  # [!code highlight]
    user_id: str  # [!code highlight]
    preferences: dict  # [!code highlight]

agent = create_agent(
    "gpt-5.4",
    tools=[get_user_info],
    state_schema=CustomAgentState,  # [!code highlight]
    checkpointer=InMemorySaver(),
)

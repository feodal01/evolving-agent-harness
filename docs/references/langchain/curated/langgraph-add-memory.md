# Memory
Source: https://docs.langchain.com/oss/python/langgraph/add-memory



AI applications need [memory](/oss/python/concepts/memory) to share context across multiple interactions. In LangGraph, you can add two types of memory:

* [Add short-term memory](#add-short-term-memory) as a part of your agent's [state](/oss/python/langgraph/graph-api#state) to enable multi-turn conversations.
* [Add long-term memory](#add-long-term-memory) to store user-specific or application-level data across sessions.

## Add short-term memory

**Short-term** memory (thread-level [persistence](/oss/python/langgraph/persistence)) enables agents to track multi-turn conversations. To add short-term memory:

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langgraph.checkpoint.memory import InMemorySaver  # [!code highlight]
from langgraph.graph import StateGraph

checkpointer = InMemorySaver()  # [!code highlight]

builder = StateGraph(...)
graph = builder.compile(checkpointer=checkpointer)  # [!code highlight]

graph.invoke(
    {"messages": [{"role": "user", "content": "hi! i am Bob"}]},
    {"configurable": {"thread_id": "1"}},  # [!code highlight]
)
```

### Use in production

In production, use a checkpointer backed by a database:

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:  # [!code highlight]
    builder = StateGraph(...)
    graph = builder.compile(checkpointer=checkpointer)  # [!code highlight]
```

<Accordion title="Example: using Postgres checkpointer">
  ```
  pip install -U "psycopg[binary,pool]" langgraph langgraph-checkpoint-postgres
  ```

  <Tip>
    You need to call `checkpointer.setup()` the first time you're using Postgres checkpointer
  </Tip>

  <Tabs>
    <Tab title="Sync">
      ```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
      from langchain.chat_models import init_chat_model
      from langgraph.graph import StateGraph, MessagesState, START
      from langgraph.checkpoint.postgres import PostgresSaver  # [!code highlight]

      model = init_chat_model(model="claude-haiku-4-5-20251001")

      DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"
      with PostgresSaver.from_conn_string(DB_URI) as checkpointer:  # [!code highlight]
          # checkpointer.setup()

          def call_model(state: MessagesState):
              response = model.invoke(state["messages"])
              return {"messages": response}

          builder = StateGraph(MessagesState)
          builder.add_node(call_model)
          builder.add_edge(START, "call_model")

          graph = builder.compile(checkpointer=checkpointer)  # [!code highlight]

          config = {
              "configurable": {
                  "thread_id": "1"  # [!code highlight]
              }
          }

          for chunk in graph.stream(
              {"messages": [{"role": "user", "content": "hi! I'm bob"}]},
              config,  # [!code highlight]
              stream_mode="values"
          ):
              chunk["messages"][-1].pretty_print()

          for chunk in graph.stream(
              {"messages": [{"role": "user", "content": "what's my name?"}]},
              config,  # [!code highlight]
              stream_mode="values"
          ):
              chunk["messages"][-1].pretty_print()
      ```
    </Tab>

    <Tab title="Async">
      ```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
      from langchain.chat_models import init_chat_model
      from langgraph.graph import StateGraph, MessagesState, START
      from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # [!code highlight]

      model = init_chat_model(model="claude-haiku-4-5-20251001")

      DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"
      async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:  # [!code highlight]
          # await checkpointer.setup()

          async def call_model(state: MessagesState):
              response = await model.ainvoke(state["messages"])
              return {"messages": response}

          builder = StateGraph(MessagesState)
          builder.add_node(call_model)
          builder.add_edge(START, "call_model")

          graph = builder.compile(checkpointer=checkpointer)  # [!code highlight]

          config = {
              "configurable": {
                  "thread_id": "1"  # [!code highlight]
              }
          }

          async for chunk in graph.astream(
              {"messages": [{"role": "user", "content": "hi! I'm bob"}]},
              config,  # [!code highlight]
              stream_mode="values"
          ):
              chunk["messages"][-1].pretty_print()

          async for chunk in graph.astream(
              {"messages": [{"role": "user", "content": "what's my name?"}]},
              config,  # [!code highlight]
              stream_mode="values"
          ):
              chunk["messages"][-1].pretty_print()
      ```
    </Tab>
  </Tabs>
</Accordion>

<Accordion title="Example: using MongoDB checkpointer">
  ```
  pip install -U pymongo langgraph langgraph-checkpoint-mongodb
  ```

  <Tip>
    **Setup**
    To use the [MongoDB checkpointer](https://pypi.org/project/langgraph-checkpoint-mongodb/), you will need a MongoDB cluster. Follow [this guide](https://www.mongodb.com/docs/guides/atlas/cluster/) to create a cluster if you don't already have one.
  </Tip>

  <Tabs>
    <Tab title="Sync">
      ```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
      from langchain.chat_models import init_chat_model
      from langgraph.graph import StateGraph, MessagesState, START
      from langgraph.checkpoint.mongodb import MongoDBSaver  # [!code highlight]

      model = init_chat_model(model="claude-haiku-4-5-20251001")

      MONGODB_URI = "localhost:27017"
      with MongoDBSaver.from_conn_string(MONGODB_URI) as checkpointer:  # [!code highlight]

          def call_model(state: MessagesState):
              response = model.invoke(state["messages"])
              return {"messages": response}

          builder = StateGraph(MessagesState)
          builder.add_node(call_model)
          builder.add_edge(START, "call_model")

          graph = builder.compile(checkpointer=checkpointer)  # [!code highlight]

          config = {
              "configurable": {
                  "thread_id": "1"  # [!code highlight]
              }
          }

          for chunk in graph.stream(
              {"messages": [{"role": "user", "content": "hi! I'm bob"}]},
              config,  # [!code highlight]
              stream_mode="values"
          ):
              chunk["messages"][-1].pretty_print()

          for chunk in graph.stream(
              {"messages": [{"role": "user", "content": "what's my name?"}]},
              config,  # [!code highlight]
              stream_mode="values"
          ):
              chunk["messages"][-1].pretty_print()
      ```
    </Tab>

    <Tab title="Async">
      ```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
      from langchain.chat_models import init_chat_model
      from langgraph.graph import StateGraph, MessagesState, START
      from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver  # [!code highlight]

      model = init_chat_model(model="claude-haiku-4-5-20251001")

      MONGODB_URI = "localhost:27017"
      async with AsyncMongoDBSaver.from_conn_string(MONGODB_URI) as checkpointer:  # [!code highlight]

          async def call_model(state: MessagesState):
              response = await model.ainvoke(state["messages"])
              return {"messages": response}

          builder = StateGraph(MessagesState)
          builder.add_node(call_model)
          builder.add_edge(START, "call_model")

          graph = builder.compile(checkpointer=checkpointer)  # [!code highlight]

          config = {
              "configurable": {
                  "thread_id": "1"  # [!code highlight]
              }
          }

          async for chunk in graph.astream(
              {"messages": [{"role": "user", "content": "hi! I'm bob"}]},
              config,  # [!code highlight]
              stream_mode="values"
          ):
              chunk["messages"][-1].pretty_print()

          async for chunk in graph.astream(
              {"messages": [{"role": "user", "content": "what's my name?"}]},
              config,  # [!code highlight]
              stream_mode="values"
          ):
              chunk["messages"][-1].pretty_print()
      ```
    </Tab>
  </Tabs>
</Accordion>

<Accordion title="Example: using Redis checkpointer">
  ```
  pip install -U langgraph langgraph-checkpoint-redis
  ```

  <Tip>
    You need to call `checkpointer.setup()` the first time you're using Redis checkpointer.
  </Tip>

  <Tabs>
    <Tab title="Sync">
      ```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
      from langchain.chat_models import init_chat_model
      from langgraph.graph import StateGraph, MessagesState, START
      from langgraph.checkpoint.redis import RedisSaver  # [!code highlight]

      model = init_chat_model(model="claude-haiku-4-5-20251001")

      DB_URI = "redis://localhost:6379"
      with RedisSaver.from_conn_string(DB_URI) as checkpointer:  # [!code highlight]
          # checkpointer.setup()

          def call_model(state: MessagesState):
              response = model.invoke(state["messages"])
              return {"messages": response}

          builder = StateGraph(MessagesState)
          builder.add_node(call_model)
          builder.add_edge(START, "call_model")

          graph = builder.compile(checkpointer=checkpointer)  # [!code highlight]

          config = {
              "configurable": {
                  "thread_id": "1"  # [!code highlight]
              }
          }

          for chunk in graph.stream(
              {"messages": [{"role": "user", "content": "hi! I'm bob"}]},
              config,  # [!code highlight]
              stream_mode="values"
          ):
              chunk["messages"][-1].pretty_print()

          for chunk in graph.stream(
              {"messages": [{"role": "user", "content": "what's my name?"}]},
              config,  # [!code highlight]
              stream_mode="values"
          ):
              chunk["messages"][-1].pretty_print()
      ```
    </Tab>

    <Tab title="Async">
      ```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
      from langchain.chat_models import init_chat_model
      from langgraph.graph import StateGraph, MessagesState, START
      from langgraph.checkpoint.redis.aio import AsyncRedisSaver  # [!code highlight]

      model = init_chat_model(model="claude-haiku-4-5-20251001")

      DB_URI = "redis://localhost:6379"
      async with AsyncRedisSaver.from_conn_string(DB_URI) as checkpointer:  # [!code highlight]
          # await checkpointer.asetup()

          async def call_model(state: MessagesState):
              response = await model.ainvoke(state["messages"])
              return {"messages": response}

          builder = StateGraph(MessagesState)
          builder.add_node(call_model)
          builder.add_edge(START, "call_model")

          graph = builder.compile(checkpointer=checkpointer)  # [!code highlight]

          config = {
              "configurable": {
                  "thread_id": "1"  # [!code highlight]
              }
          }

          async for chunk in graph.astream(
              {"messages": [{"role": "user", "content": "hi! I'm bob"}]},
              config,  # [!code highlight]
              stream_mode="values"
          ):
              chunk["messages"][-1].pretty_print()

          async for chunk in graph.astream(
              {"messages": [{"role": "user", "content": "what's my name?"}]},
              config,  # [!code highlight]
              stream_mode="values"
          ):
              chunk["messages"][-1].pretty_print()
      ```
    </Tab>
  </Tabs>
</Accordion>

### Use in subgraphs

If your graph contains [subgraphs](/oss/python/langgraph/use-subgraphs), you only need to provide the checkpointer when compiling the parent graph. LangGraph will automatically propagate the checkpointer to the child subgraphs.

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langgraph.graph import START, StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from typing import TypedDict

class State(TypedDict):
    foo: str

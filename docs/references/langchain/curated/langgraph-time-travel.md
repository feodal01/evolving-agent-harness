# Use time-travel
Source: https://docs.langchain.com/oss/python/langgraph/use-time-travel

Replay past executions and fork to explore alternative paths in LangGraph

## Overview

LangGraph supports time travel through [checkpoints](/oss/python/langgraph/persistence#checkpoints):

* **[Replay](#replay)**: Retry from a prior checkpoint.
* **[Fork](#fork)**: Branch from a prior checkpoint with modified state to explore an alternative path.

Both work by resuming from a prior checkpoint. Nodes before the checkpoint are not re-executed (results are already saved). Nodes after the checkpoint re-execute, including any LLM calls, API requests, and [interrupts](/oss/python/langgraph/interrupts) (which may produce different results).

## Replay

Invoke the graph with a prior checkpoint's config to replay from that point.

<Warning>
  Replay re-executes nodes—it doesn't just read from cache. LLM calls, API requests, and [interrupts](/oss/python/langgraph/interrupts) fire again and may return different results. Replaying from the final checkpoint (no `next` nodes) is a no-op.
</Warning>

<img alt="Replay" />

Use [`get_state_history`](https://reference.langchain.com/python/langgraph/graphs/#langgraph.graph.state.CompiledStateGraph.get_state_history) to find the checkpoint you want to replay from, then call [`invoke`](https://reference.langchain.com/python/langgraph/graphs/#langgraph.graph.state.CompiledStateGraph.invoke) with that checkpoint's config:

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langgraph.graph import StateGraph, START
from langgraph.checkpoint.memory import InMemorySaver
from typing_extensions import TypedDict, NotRequired
from langchain_core.utils.uuid import uuid7

class State(TypedDict):
    topic: NotRequired[str]
    joke: NotRequired[str]


def generate_topic(state: State):
    return {"topic": "socks in the dryer"}


def write_joke(state: State):
    return {"joke": f"Why do {state['topic']} disappear? They elope!"}


checkpointer = InMemorySaver()
graph = (
    StateGraph(State)
    .add_node("generate_topic", generate_topic)
    .add_node("write_joke", write_joke)
    .add_edge(START, "generate_topic")
    .add_edge("generate_topic", "write_joke")
    .compile(checkpointer=checkpointer)
)

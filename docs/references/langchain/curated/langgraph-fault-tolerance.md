# Fault tolerance
Source: https://docs.langchain.com/oss/python/langgraph/fault-tolerance

Configure per-node timeouts, retries, and error handlers in LangGraph.

When a node fails—from a slow external API, a transient network error, or an unhandled exception—LangGraph gives you three composable mechanisms to respond:

* [**Retries**](#retries) — automatically re-run failed attempts based on exception type and backoff settings
* [**Timeouts**](#timeouts) — cap how long a single attempt may run
* [**Error handling**](#error-handling) — run a recovery function after all retries are exhausted

These compose in a fixed order: when a node attempt raises any exception (including [`NodeTimeoutError`](https://reference.langchain.com/python/langgraph/errors/NodeTimeoutError) from a timeout), the retry policy decides whether to retry. Only after retries are exhausted does the error handler run.

For stopping a run cleanly at a superstep boundary and resuming later, see [Graceful shutdown](/oss/python/langgraph/durable-execution#graceful-shutdown).

<Note>
  Per-node timeouts and node-level error handlers require `langgraph>=1.2`, currently in alpha.
</Note>

```mermaid theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
%%{init:{'theme':'base','themeVariables':{'lineColor':'#40668D','primaryColor':'#E5F4FF','primaryTextColor':'#030710','primaryBorderColor':'#006DDD'}}}%%
flowchart LR
    start([Attempt starts]) --> exec[Run node]
    exec -->|"success"| done([Continue graph])
    exec -->|"any exception<br/>including NodeTimeoutError"| retry{retry_policy<br/>matches?}
    retry -->|"yes, attempts left"| exec
    retry -->|"exhausted or absent"| handler{error_handler?}
    handler -->|"yes"| run_handler["Invoke handler<br/>with NodeError"]
    run_handler --> route([Update state +<br/>Command goto])
    handler -->|"no"| bubble([Exception<br/>bubbles up])

    classDef process fill:#E5F4FF,stroke:#006DDD,stroke-width:2px,color:#030710
    classDef decision fill:#FDF3FF,stroke:#7E65AE,stroke-width:2px,color:#504B5F
    classDef alert fill:#F8E8E6,stroke:#B27D75,stroke-width:2px,color:#634643
    classDef output fill:#EBD0F0,stroke:#885270,stroke-width:2px,color:#441E33

    class exec,run_handler process
    class retry,handler decision
    class bubble alert
    class done,route,start output
```

## Retries

A retry policy automatically re-runs a failed node attempt based on exception type and backoff settings. Pass `retry_policy=` to [`add_node`](https://reference.langchain.com/python/langgraph/graph/state/StateGraph/add_node):

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langgraph.types import RetryPolicy

builder.add_node(
    "call_api",
    call_api,
    retry_policy=RetryPolicy(max_attempts=3),
)
```

### Default behavior

By default, `retry_on` uses `default_retry_on`, which retries on **any** exception except the following (and their subclasses):

* `ValueError`
* `TypeError`
* `ArithmeticError`
* `ImportError`
* `LookupError`
* `NameError`
* `SyntaxError`
* `RuntimeError`
* `ReferenceError`
* `StopIteration`
* `StopAsyncIteration`
* `OSError`

For exceptions from popular HTTP libraries such as `requests` and `httpx`, it only retries on 5xx status codes. [`NodeTimeoutError`](https://reference.langchain.com/python/langgraph/errors/NodeTimeoutError) is retryable by default.

### Parameters

| Parameter          | Type                                                                          | Default            | Description                                                                      |
| ------------------ | ----------------------------------------------------------------------------- | ------------------ | -------------------------------------------------------------------------------- |
| `max_attempts`     | `int`                                                                         | `3`                | Maximum number of attempts, including the first.                                 |
| `initial_interval` | `float`                                                                       | `0.5`              | Seconds before the first retry.                                                  |
| `backoff_factor`   | `float`                                                                       | `2.0`              | Multiplier applied to the interval after each retry.                             |
| `max_interval`     | `float`                                                                       | `128.0`            | Maximum seconds between retries.                                                 |
| `jitter`           | `bool`                                                                        | `True`             | Add random jitter to the interval.                                               |
| `retry_on`         | `type[Exception] \| Sequence[type[Exception]] \| Callable[[Exception], bool]` | `default_retry_on` | Exceptions to retry on, or a callable returning `True` for retryable exceptions. |

### Custom retry logic

Pass a callable or exception type to `retry_on`. Import `default_retry_on` to extend the default behavior:

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langgraph.types import RetryPolicy, default_retry_on

def custom_retry_on(exc: BaseException) -> bool:
    if isinstance(exc, MyCustomError):
        return False
    return default_retry_on(exc)

builder.add_node(
    "call_api",
    call_api,
    retry_policy=RetryPolicy(max_attempts=3, retry_on=custom_retry_on),
)
```

### Inspect retry state

Use `runtime.execution_info` inside a node to inspect the current attempt number. This is useful for switching to a fallback when the primary call keeps failing:

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from langgraph.types import RetryPolicy
from typing_extensions import TypedDict

class State(TypedDict):
    result: str

def my_node(state: State, runtime: Runtime) -> State:
    if runtime.execution_info.node_attempt > 1:  # [!code highlight]
        return {"result": call_fallback_api()}
    return {"result": call_primary_api()}

builder = StateGraph(State)
builder.add_node("my_node", my_node, retry_policy=RetryPolicy(max_attempts=3))
builder.add_edge(START, "my_node")
builder.add_edge("my_node", END)
```

`execution_info` exposes the following fields:

| Attribute                 | Type            | Description                                                                            |
| ------------------------- | --------------- | -------------------------------------------------------------------------------------- |
| `node_attempt`            | `int`           | Current attempt number (1-indexed). `1` on the first try, `2` on the first retry, etc. |
| `node_first_attempt_time` | `float \| None` | Unix timestamp of when the first attempt started. Constant across retries.             |
| `thread_id`               | `str \| None`   | Thread ID for the current execution. `None` without a checkpointer.                    |
| `run_id`                  | `str \| None`   | Run ID for the current execution. `None` when not provided in config.                  |
| `checkpoint_id`           | `str`           | Checkpoint ID for the current execution.                                               |
| `task_id`                 | `str`           | Task ID for the current execution.                                                     |

`execution_info` is available even without a retry policy—`node_attempt` defaults to `1`.

## Timeouts

<Note>
  Requires `langgraph>=1.2`, currently in alpha.
</Note>

The `timeout=` parameter on [`add_node`](https://reference.langchain.com/python/langgraph/graph/state/StateGraph/add_node) caps how long a single node attempt may run. Pass a number (seconds), a `timedelta`, or a [`TimeoutPolicy`](https://reference.langchain.com/python/langgraph/types/TimeoutPolicy) for separate run and idle limits:

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from datetime import timedelta
from langgraph.types import TimeoutPolicy

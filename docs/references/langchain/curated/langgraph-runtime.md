# LangGraph runtime
Source: https://docs.langchain.com/oss/python/langgraph/pregel



[`Pregel`](https://reference.langchain.com/python/langgraph/pregel/main/Pregel) implements LangGraph's runtime, managing the execution of LangGraph applications.

Compiling a [StateGraph](https://reference.langchain.com/python/langgraph/graph/state/StateGraph) or creating an [`@entrypoint`](https://reference.langchain.com/python/langgraph/func/entrypoint) produces a [`Pregel`](https://reference.langchain.com/python/langgraph/pregel/main/Pregel) instance that can be invoked with input.

This guide explains the runtime at a high level and provides instructions for directly implementing applications with Pregel.

> **Note:** The [`Pregel`](https://reference.langchain.com/python/langgraph/pregel/main/Pregel) runtime is named after [Google's Pregel algorithm](https://research.google/pubs/pub37252/), which describes an efficient method for large-scale parallel computation using graphs.

## Overview

In LangGraph, Pregel combines [**actors**](https://en.wikipedia.org/wiki/Actor_model) and **channels** into a single application. **Actors** read data from channels and write data to channels. Pregel organizes the execution of the application into multiple steps, following the **Pregel Algorithm**/**Bulk Synchronous Parallel** model.

Each step consists of three phases:

* **Plan**: Determine which **actors** to execute in this step. For example, in the first step, select the **actors** that subscribe to the special **input** channels; in subsequent steps, select the **actors** that subscribe to channels updated in the previous step.
* **Execution**: Execute all selected **actors** in parallel, until all complete, or one fails, or a timeout is reached. During this phase, channel updates are invisible to actors until the next step.
* **Update**: Update the channels with the values written by the **actors** in this step.

Repeat until no **actors** are selected for execution, or a maximum number of steps is reached.

## Actors

An **actor** is a `PregelNode`. It subscribes to channels, reads data from them, and writes data to them. It can be thought of as an **actor** in the Pregel algorithm. `PregelNodes` implement LangChain's Runnable interface.

## Channels

Channels are used to communicate between actors (PregelNodes). Each channel has a value type, an update type, and an update function—which takes a sequence of updates and modifies the stored value. Channels can be used to send data from one chain to another, or to send data from a chain to itself in a future step.

### LastValue

[`LastValue`](https://reference.langchain.com/python/langgraph/channels/last_value/LastValue) is the default channel type. It stores the last value written to it, overwriting any previous value. Use it for input and output values, or for passing data from one step to the next.

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langgraph.channels import LastValue

channel: LastValue[int] = LastValue(int)
```

### Topic

[`Topic`](https://reference.langchain.com/python/langgraph/channels/topic/Topic) is a configurable PubSub channel useful for sending multiple values between actors or accumulating output across steps. It can be configured to deduplicate values or to accumulate all values written during a run.

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from langgraph.channels import Topic

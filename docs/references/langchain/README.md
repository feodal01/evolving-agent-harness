# LangChain And LangGraph Offline References

Downloaded on 2026-05-08 from the official LangChain documentation.

Raw files:

- `llms.txt`: official index from `https://docs.langchain.com/llms.txt`.
- `llms-full.txt`: full markdown dump from `https://docs.langchain.com/llms-full.txt`.
- `langgraph-llms.txt`: LangGraph index from `https://langchain-ai.github.io/langgraph/llms.txt`.
- `manifest.json`: source URLs, byte sizes, and SHA-256 digests.

Curated Python references for meta-agent work live in `curated/`.

Start with these files when evolving the agent:

- `curated/concepts-products.md`: when choosing LangChain vs LangGraph vs Deep Agents.
- `curated/langchain-agents.md`: `create_agent`, agent loop, model/tool composition.
- `curated/langchain-tools.md`: tool definitions and schemas.
- `curated/langchain-context-engineering.md`: controlling what the model sees.
- `curated/langchain-middleware-overview.md`, `curated/langchain-middleware-built-in.md`, `curated/langchain-middleware-custom.md`: model/tool middleware and execution control.
- `curated/langchain-short-term-memory.md`, `curated/langchain-long-term-memory.md`: memory patterns.
- `curated/langchain-structured-output.md`: structured output contracts.
- `curated/langchain-streaming.md`: streaming agent progress.
- `curated/langchain-agent-evals.md`, `curated/langchain-unit-testing.md`: testing agent trajectories.
- `curated/langgraph-overview.md`, `curated/langgraph-thinking.md`: when to move from a simple agent loop to an explicit graph.
- `curated/langgraph-add-memory.md`: checkpointers and stores.
- `curated/langgraph-fault-tolerance.md`: retries, timeouts, and error handling.
- `curated/langgraph-time-travel.md`: replaying and forking past executions.

Use `llms-full.txt` only when the curated references do not contain the needed detail.

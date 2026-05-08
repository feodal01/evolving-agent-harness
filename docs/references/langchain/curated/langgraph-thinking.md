# Thinking in LangGraph
Source: https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph

Learn how to think about building agents with LangGraph

When you build an agent with LangGraph, you will first break it apart into discrete steps called **nodes**. Then, you will describe the different decisions and transitions from each of your nodes. Finally, you connect nodes together through a shared **state** that each node can read from and write to.

In this walkthrough, we'll guide you through the thought process of building a customer support email agent with LangGraph.

## Start with the process you want to automate

Imagine that you need to build an AI agent that handles customer support emails. Your product team has given you these requirements:

```txt theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
The agent should:

- Read incoming customer emails
- Classify them by urgency and topic
- Search relevant documentation to answer questions
- Draft appropriate responses
- Escalate complex issues to human agents
- Schedule follow-ups when needed

Example scenarios to handle:

1. Simple product question: "How do I reset my password?"
2. Bug report: "The export feature crashes when I select PDF format"
3. Urgent billing issue: "I was charged twice for my subscription!"
4. Feature request: "Can you add dark mode to the mobile app?"
5. Complex technical issue: "Our API integration fails intermittently with 504 errors"
```

To implement an agent in LangGraph, you will usually follow the same five steps.

## Step 1: Map out your workflow as discrete steps

Start by identifying the distinct steps in your process. Each step will become a **node** (a function that does one specific thing). Then, sketch how these steps connect to each other.

```mermaid theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
flowchart TD
    A[START] --> B[Read Email]
    B --> C[Classify Intent]

    C -.-> D[Doc Search]
    C -.-> E[Bug Track]
    C -.-> F[Human Review]

    D --> G[Draft Reply]
    E --> G
    F --> G

    G -.-> H[Human Review]
    G -.-> I[Send Reply]

    H --> J[END]
    I --> J[END]

    classDef process fill:#E5F4FF,stroke:#006DDD,stroke-width:2px,color:#030710
    class A,B,C,D,E,F,G,H,I,J process
```

The arrows in this diagram show possible paths, but the actual decision of which path to take happens inside each node.

Now that we've identified the components in our workflow, let's understand what each node needs to do:

* `Read Email`: Extract and parse the email content
* `Classify Intent`: Use an LLM to categorize urgency and topic, then route to appropriate action
* `Doc Search`: Query your knowledge base for relevant information
* `Bug Track`: Create or update issue in tracking system
* `Draft Reply`: Generate an appropriate response
* `Human Review`: Escalate to human agent for approval or handling
* `Send Reply`: Dispatch the email response

<Tip>
  Notice that some nodes make decisions about where to go next (`Classify Intent`, `Draft Reply`, `Human Review`), while others always proceed to the same next step (`Read Email` always goes to `Classify Intent`, `Doc Search` always goes to `Draft Reply`).
</Tip>

## Step 2: Identify what each step needs to do

For each node in your graph, determine what type of operation it represents and what context it needs to work properly.

<CardGroup>
  <Card title="LLM steps" icon="brain" href="#llm-steps">
    Use when you need to understand, analyze, generate text, or make reasoning decisions
  </Card>

  <Card title="Data steps" icon="database" href="#data-steps">
    Use when you need to retrieve information from external sources
  </Card>

  <Card title="Action steps" icon="bolt" href="#action-steps">
    Use when you need to perform external actions
  </Card>

  <Card title="User input steps" icon="user" href="#user-input-steps">
    Use when you need human intervention
  </Card>
</CardGroup>

### LLM steps

When a step needs to understand, analyze, generate text, or make reasoning decisions:

<AccordionGroup>
  <Accordion title="Classify intent">
    * Static context (prompt): Classification categories, urgency definitions, response format
    * Dynamic context (from state): Email content, sender information
    * Desired outcome: Structured classification that determines routing
  </Accordion>

  <Accordion title="Draft reply">
    * Static context (prompt): Tone guidelines, company policies, response templates
    * Dynamic context (from state): Classification results, search results, customer history
    * Desired outcome: Professional email response ready for review
  </Accordion>
</AccordionGroup>

### Data steps

When a step needs to retrieve information from external sources:

<AccordionGroup>
  <Accordion title="Document search">
    * Parameters: Query built from intent and topic
    * Retry strategy: Yes, with exponential backoff for transient failures
    * Caching: Could cache common queries to reduce API calls
  </Accordion>

  <Accordion title="Customer history lookup">
    * Parameters: Customer email or ID from state
    * Retry strategy: Yes, but with fallback to basic info if unavailable
    * Caching: Yes, with time-to-live to balance freshness and performance
  </Accordion>
</AccordionGroup>

### Action steps

When a step needs to perform an external action:

<AccordionGroup>
  <Accordion title="Send reply">
    * When to execute node: After approval (human or automated)
    * Retry strategy: Yes, with exponential backoff for network issues
    * Should not cache: Each send is a unique action
  </Accordion>

  <Accordion title="Bug track">
    * When to execute node: Always when intent is "bug"
    * Retry strategy: Yes, critical to not lose bug reports
    * Returns: Ticket ID to include in response
  </Accordion>
</AccordionGroup>

### User input steps

When a step needs human intervention:

<AccordionGroup>
  <Accordion title="Human review node">
    * Context for decision: Original email, draft response, urgency, classification
    * Expected input format: Approval boolean plus optional edited response
    * When triggered: High urgency, complex issues, or quality concerns
  </Accordion>
</AccordionGroup>

## Step 3: Design your state

State is the shared [memory](/oss/python/concepts/memory) accessible to all nodes in your agent. Think of it as the notebook your agent uses to keep track of everything it learns and decides as it works through the process.

### What belongs in state?

Ask yourself these questions about each piece of data:

<CardGroup>
  <Card title="Include in state" icon="check">
    Does it need to persist across steps? If yes, it goes in state.
  </Card>

  <Card title="Don't store" icon="code">
    Can you derive it from other data? If yes, compute it when needed instead of storing it in state.
  </Card>
</CardGroup>

For our email agent, we need to track:

* The original email and sender info (can't reconstruct these later)
* Classification results (needed by multiple later/downstream nodes)
* Search results and customer data (expensive to re-fetch)
* The draft response (needs to persist through review)
* Execution metadata (for debugging and recovery)

### Keep state raw, format prompts on-demand

<Tip>
  A key principle: your state should store raw data, not formatted text. Format prompts inside nodes when you need them.
</Tip>

This separation means:

* Different nodes can format the same data differently for their needs
* You can change prompt templates without modifying your state schema
* Debugging is clearer—you see exactly what data each node received
* Your agent can evolve without breaking existing state

Let's define our state:

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
from typing import TypedDict, Literal

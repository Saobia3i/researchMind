# LinkedIn Post

I recently built **ResearchMind**, a full-stack AI research system focused on one question:

**How can we make AI-generated research more transparent, verifiable, and cost-aware?**

AI tools can already generate answers with sources. But I wanted to go deeper than that.

A source link does not always tell us whether a specific claim is truly supported, whether different models disagree, whether the system used shallow retrieval or a structured workflow, or how much the reasoning process cost.

So I built ResearchMind as a research workflow system, not just another chatbot.

The project currently supports four research modes:

**1. Quick Research**

For lightweight questions, the system returns a structured response with a title, summary, key points, confidence score, and follow-up questions.

**2. ReAct Agent**

This mode uses a reasoning + acting loop where the agent can decide when to call tools such as web search, knowledge-base search, or calculator. The full trace is visible in the UI, including thoughts, actions, inputs, and observations.

**3. Team Research**

I used LangGraph to build a planner -> researcher -> evidence grader -> writer workflow. The planner decomposes the query, the researcher gathers evidence, a relevance gate filters off-topic chunks, and the writer creates a final report from only the filtered evidence.

This was an important reliability improvement: the system now reports how many evidence chunks were retrieved vs. kept for each sub-topic, and if no relevant evidence is found, the report has to say that instead of filling the gap with unsupported prose.

**4. Deep Consensus**

This is the part I enjoyed building the most.

Instead of trusting one model response, Deep Consensus retrieves evidence, asks available model providers for independent opinions, extracts important claims, verifies those claims against evidence, builds a disagreement map, and then synthesizes the final answer.

It also shows reliability notes when something is missing or weak. For example, if only one model provider runs, the system does not pretend that true multi-model consensus happened. It marks the output as a single-model audit.

Some of the things I focused on:

- claim-level verification
- relevance-gated Team Research synthesis
- model disagreement mapping
- evidence graph generation
- ReAct tool usage
- LangGraph orchestration
- Pinecone-based RAG
- DuckDuckGo/DDGS web retrieval
- provider abstraction for Gemini, OpenRouter, Groq, OpenAI, and Perplexity
- cost-aware routing and budget control
- stage-level token budgets
- evidence deduplication and prompt compaction
- per-sub-topic evidence audit counts
- early-stop provider routing when strong agreement is reached
- token and cost tracking
- session memory
- graceful handling of missing API keys
- transparent UI for traces, skipped providers, and reliability notes

Tech stack:

- FastAPI
- Python
- LangGraph
- Gemini API
- OpenRouter API
- Groq API
- Pinecone
- DDGS / DuckDuckGo search
- Next.js
- React
- TypeScript
- Tailwind CSS

One design decision I made intentionally: the default workflow is free-friendly. It uses Gemini + OpenRouter + Groq by default. OpenAI and Perplexity are implemented as optional adapters, but they are not required for the default flow.

This project taught me a lot about the difference between building an AI demo and building an AI system.

A demo can stop at "the model answered."

A system needs to ask:

- What evidence was used?
- Which claims are actually supported?
- Was the retrieved evidence relevant to the specific sub-topic?
- Where is the answer weak?
- Did models disagree?
- Which providers were skipped?
- How much did the run cost?
- How many tokens were saved before calling the models?
- Can the user inspect the reasoning path?

ResearchMind is still evolving. Next, I want to improve contradiction detection, richer source quality scoring, persistent audit history, Redis-backed memory, and evaluation workflows.

GitHub: [add your GitHub repository link here]

#AI #LLM #RAG #LangGraph #FastAPI #NextJS #TypeScript #GenerativeAI #MachineLearning #SoftwareEngineering #OpenToWork

---

## Shorter Version

I built **ResearchMind**, a full-stack AI research system that goes beyond simply returning answers with sources.

The goal was to make AI research more transparent, verifiable, and cost-aware.

ResearchMind includes:

- ReAct tool-calling agent
- LangGraph planner -> researcher -> evidence grader -> writer workflow
- Deep Consensus mode with model opinions, claim verification, disagreement mapping, and evidence graph
- per-sub-topic evidence relevance counts for Team Research
- Gemini + OpenRouter + Groq default provider flow
- optional OpenAI and Perplexity adapters
- Pinecone RAG
- token and cost tracking
- token optimization reports
- session memory
- skipped-provider and reliability reporting

The most important lesson from this project:

AI systems should not only answer. They should show how much confidence we should place in the answer.

GitHub: [add your GitHub repository link here]

#AI #LLM #RAG #LangGraph #FastAPI #NextJS #GenerativeAI #OpenToWork

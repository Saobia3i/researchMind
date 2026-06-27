import logging
import re
from app.core.llm import client
from app.tools import TOOLS, TOOL_DESCRIPTIONS

logger = logging.getLogger(__name__)

REACT_SYSTEM_PROMPT = f"""
You are a highly capable AI research assistant. You solve complex research tasks by reasoning step-by-step and calling tools when necessary.

You have access to the following tools:
{TOOL_DESCRIPTIONS}

You MUST follow the ReAct (Reasoning and Acting) loop pattern. Every response must contain only ONE step of the loop. Specifically, you must output your thoughts, decide on an action, and wait for the observation.

Format your responses exactly like this:

Thought: Write your reasoning about what to do next.
Action: the name of the tool to use (must be one of: [web_search, calculate, kb_search])
Action Input: the exact query or expression to send to the tool (no wrapping quotes or brackets unless they are part of the query/expression)

Once you receive the Observation from the user/system, you will continue with another Thought and Action (if needed), or output your final answer:

Thought: I now have all the information required to answer the question.
Final Answer: The final, complete, and comprehensive answer to the user's original question.

Guidelines:
1. Always start your response with "Thought:".
2. Only output ONE Action per turn. Never output the "Observation:" yourself; the system will provide it.
3. Be precise with tool names.
4. If you have gathered all necessary information, conclude directly with "Thought: I now have..." followed by "Final Answer:".
"""


def parse_action(text: str) -> tuple[str | None, str | None]:
    """
    Parses the LLM output for Action: and Action Input:
    """
    action_match = re.search(r"Action:\s*(.*)", text)
    action_input_match = re.search(r"Action Input:\s*(.*)", text)

    action = action_match.group(1).strip() if action_match else None
    action_input = (
        action_input_match.group(1).strip() if action_input_match else None
    )

    # Clean action input if the LLM wrapped it in quotes/parentheses
    if action_input:
        if (
            action_input.startswith('"')
            and action_input.endswith('"')
            or action_input.startswith("'")
            and action_input.endswith("'")
        ):
            action_input = action_input[1:-1]
        if action_input.startswith("(") and action_input.endswith(")"):
            action_input = action_input[1:-1]

    return action, action_input


def run_react_agent(
    query: str,
    history: list[dict] | None = None,
    max_iterations: int = 6,
) -> dict:
    """
    Runs the ReAct reasoning loop.

    Args:
        query: The user's current question.
        history: Optional prior conversation history. Each item should be
                 {"role": "user"|"assistant", "content": "..."}
                 Injected after the system prompt so the agent has context.
        max_iterations: Maximum tool-use + reasoning loops before forcing exit.

    Returns:
        A dict containing:
            - query: The original query
            - steps: List of {step, thought, action, action_input, observation}
            - final_answer: The agent's final answer string
            - usage: {prompt_tokens, completion_tokens, total_tokens} aggregated
    """
    logger.info(f"Starting ReAct Agent for query: '{query}'")

    # Build message list: system prompt → optional history → current question
    messages: list[dict] = [
        {"role": "system", "content": REACT_SYSTEM_PROMPT},
    ]

    if history:
        # Inject prior turns so the agent is aware of conversation context
        for msg in history[-10:]:  # Limit to last 10 messages to control tokens
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": f"Question: {query}"})

    steps = []
    final_answer = None
    total_prompt_tokens = 0
    total_completion_tokens = 0

    for i in range(max_iterations):
        logger.info(f"Agent iteration {i + 1}/{max_iterations}")

        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.0,
                max_tokens=1024,
            )
            response_text = response.choices[0].message.content.strip()

            # Accumulate token usage across all loop iterations
            if response.usage:
                total_prompt_tokens += response.usage.prompt_tokens
                total_completion_tokens += response.usage.completion_tokens

        except Exception as e:
            logger.error(f"Error calling Groq in ReAct loop: {e}")
            raise RuntimeError(f"LLM generation failed: {e}")

        logger.info(f"LLM Response:\n{response_text}")
        messages.append({"role": "assistant", "content": response_text})

        # Check for Final Answer
        if "Final Answer:" in response_text:
            parts = response_text.split("Final Answer:")
            final_answer = parts[-1].strip()
            steps.append(
                {
                    "step": i + 1,
                    "thought": parts[0].replace("Thought:", "").strip(),
                    "action": None,
                    "action_input": None,
                    "observation": None,
                }
            )
            break

        # Parse Action and Action Input
        action, action_input = parse_action(response_text)
        thought = (
            response_text.split("Action:")[0]
            .replace("Thought:", "")
            .strip()
        )

        if not action or not action_input:
            logger.warning(
                "Could not parse Action/Action Input from LLM response. Forcing final answer."
            )
            final_answer = response_text
            steps.append(
                {
                    "step": i + 1,
                    "thought": "Unable to parse tool call; terminating.",
                    "action": None,
                    "action_input": None,
                    "observation": None,
                }
            )
            break

        # Check if the tool exists
        if action not in TOOLS:
            observation = (
                f"Error: Tool '{action}' is not registered. "
                f"Available tools are: {list(TOOLS.keys())}"
            )
        else:
            try:
                observation = TOOLS[action](action_input)
            except Exception as e:
                observation = f"Error executing tool '{action}': {str(e)}"

        logger.info(f"Tool Observation: {observation}")

        steps.append(
            {
                "step": i + 1,
                "thought": thought,
                "action": action,
                "action_input": action_input,
                "observation": observation,
            }
        )
        messages.append(
            {"role": "user", "content": f"Observation: {observation}"}
        )

    if final_answer is None:
        final_answer = (
            "Agent timed out or failed to reach a final answer within the iteration limit."
        )

    return {
        "query": query,
        "steps": steps,
        "final_answer": final_answer,
        "usage": {
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens,
        },
    }

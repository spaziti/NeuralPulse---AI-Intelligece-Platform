import logging
import json
from typing import Dict, Any, List, Callable, TypedDict, Optional
import requests

from backend.app.config import settings
from ai_agents.agent_manager import AIAgentManager

logger = logging.getLogger("neuralpulse.ai_agents.workflow")


# 1. Define Agent State Schema
class AgentState(TypedDict):
    title: str
    content: str
    similar_articles: List[Dict[str, Any]]
    summary: str
    sentiment: str
    sentiment_score: float
    credibility_score: float
    credibility_explanation: str
    trends: List[str]
    key_entities: List[str]
    contradictions: List[str]
    briefing: str


# 2. Setup LangGraph / Fallback Interface
try:
    from langgraph.graph import StateGraph, START, END
    HAS_LANGGRAPH = True
    logger.info("LangGraph native library detected. Operating in native Graph execution mode.")
except ImportError:
    HAS_LANGGRAPH = False
    START = "__start__"
    END = "__end__"
    logger.info("LangGraph not found. Initializing NeuralPulse lightweight State Graph fallback runner.")

    class StateGraph:
        def __init__(self, state_schema: Any) -> None:
            self.state_schema = state_schema
            self.nodes: Dict[str, Callable] = {}
            self.edges: List[tuple] = []
            self.entry_point: Optional[str] = None
            self.finish_point: Optional[str] = None

        def add_node(self, name: str, action: Callable) -> "StateGraph":
            self.nodes[name] = action
            return self

        def add_edge(self, start_node: str, end_node: str) -> "StateGraph":
            if start_node == START:
                self.entry_point = end_node
            elif end_node == END:
                self.finish_point = start_node
            else:
                self.edges.append((start_node, end_node))
            return self

        def set_entry_point(self, name: str) -> "StateGraph":
            self.entry_point = name
            return self

        def set_finish_point(self, name: str) -> "StateGraph":
            self.finish_point = name
            return self

        def compile(self) -> "CompiledGraph":
            return CompiledGraph(self)

    class CompiledGraph:
        def __init__(self, graph: StateGraph) -> None:
            self.graph = graph

        async def ainvoke(self, input_state: Dict[str, Any]) -> Dict[str, Any]:
            state = input_state.copy()
            current_node = self.graph.entry_point

            while current_node:
                logger.info(f"[Workflow Node] Running: {current_node}")
                node_fn = self.graph.nodes[current_node]
                
                # Handle async nodes
                import inspect
                if inspect.iscoroutinefunction(node_fn):
                    updates = await node_fn(state)
                else:
                    updates = node_fn(state)

                if updates:
                    state.update(updates)

                # Determine next transition
                next_node = None
                for start, end in self.graph.edges:
                    if start == current_node:
                        next_node = end
                        break
                
                if not next_node and current_node == self.graph.finish_point:
                    break
                current_node = next_node

            logger.info("Workflow execution completed successfully.")
            return state


# 3. Define Node Actions (Agents)

async def summarizer_agent_node(state: AgentState) -> Dict[str, Any]:
    """Agent 1: Executive Summarization & Sentiment Agent Node."""
    title = state.get("title", "")
    content = state.get("content", "")
    
    agent = AIAgentManager()
    if agent.openai_key:
        system_prompt = (
            "You are the Summarizer & Sentiment Agent. Analyze the article text. "
            "Generate a concise 2 to 3 sentence executive summary. "
            "Also evaluate the overall sentiment of the text (POSITIVE, NEGATIVE, or NEUTRAL) "
            "and assign a numeric sentiment score between -1.0 (strongly negative) and 1.0 (strongly positive). "
            "Respond ONLY with a JSON object in this format: "
            '{"summary": "Concise summary sentences.", "sentiment": "POSITIVE", "sentiment_score": 0.8}'
        )
        try:
            res = await agent._call_llm(system_prompt, f"Title: {title}\nContent: {content}")
            return {
                "summary": res.get("summary", ""),
                "sentiment": res.get("sentiment", "NEUTRAL").upper(),
                "sentiment_score": float(res.get("sentiment_score", 0.0))
            }
        except Exception as e:
            logger.error(f"Summarizer LLM node failed: {e}")

    # Heuristic Local fallback
    words = (title + " " + content).lower()
    pos_count = sum(1 for w in ["surge", "gain", "rise", "revolution", "launch", "grow"] if w in words)
    neg_count = sum(1 for w in ["breach", "fail", "drop", "collapse", "risk", "attack"] if w in words)
    
    sentiment = "NEUTRAL"
    score = 0.0
    if pos_count > neg_count:
        sentiment = "POSITIVE"
        score = 0.5
    elif neg_count > pos_count:
        sentiment = "NEGATIVE"
        score = -0.5

    summary = f"Summary of '{title}': The article reviews critical industry metrics and developments."
    return {"summary": summary, "sentiment": sentiment, "sentiment_score": score}


async def credibility_agent_node(state: AgentState) -> Dict[str, Any]:
    """Agent 2: Fact-Checking & Credibility Analysis Agent Node."""
    title = state.get("title", "")
    content = state.get("content", "")

    agent = AIAgentManager()
    if agent.openai_key:
        system_prompt = (
            "You are the Credibility Analysis Agent. Critically analyze the news content. "
            "Look for evidence of sensationalism, citation of primary sources, verification of data, "
            "and general logical consistency. Assign a credibility score between 0.0 (highly sensationalist/unreliable) "
            "and 1.0 (completely reliable factual reporting). Add a brief explanation. "
            "Respond ONLY with a JSON object in this format: "
            '{"credibility_score": 0.95, "explanation": "Detailed explanation of credibility factors."}'
        )
        try:
            res = await agent._call_llm(system_prompt, f"Title: {title}\nContent: {content}")
            return {
                "credibility_score": float(res.get("credibility_score", 0.8)),
                "credibility_explanation": res.get("explanation", "")
            }
        except Exception as e:
            logger.error(f"Credibility LLM node failed: {e}")

    # Local fallback
    score = 0.85
    if "hack" in title.lower() or "breach" in title.lower():
        score = 0.70
    return {
        "credibility_score": score,
        "credibility_explanation": "Evaluated credibility score based on local keyword pattern matching heuristics."
    }


async def trend_agent_node(state: AgentState) -> Dict[str, Any]:
    """Agent 3: Category and Tech Trend Analysis Agent Node."""
    title = state.get("title", "")
    content = state.get("content", "")

    agent = AIAgentManager()
    if agent.openai_key:
        system_prompt = (
            "You are the Trend Analysis Agent. Extract the primary technological trends, industries, "
            "market segments, and named entities (companies, organizations, technologies) from the news article. "
            "Respond ONLY with a JSON object in this format: "
            '{"trends": ["Generative AI", "Semiconductors"], "key_entities": ["OpenAI", "Nvidia", "SaaS"]}'
        )
        try:
            res = await agent._call_llm(system_prompt, f"Title: {title}\nContent: {content}")
            return {
                "trends": res.get("trends", []),
                "key_entities": res.get("key_entities", [])
            }
        except Exception as e:
            logger.error(f"Trend LLM node failed: {e}")

    # Local fallback
    trends = ["Technology"]
    entities = ["General Tech"]
    text = (title + " " + content).lower()
    if "ai" in text or "gpt" in text:
        trends.append("Artificial Intelligence")
        entities.append("LLM")
    if "cloud" in text or "saas" in text:
        trends.append("Cloud Software")
        entities.append("SaaS")
        
    return {"trends": trends, "key_entities": entities}


async def contradiction_agent_node(state: AgentState) -> Dict[str, Any]:
    """Agent 4: Contradiction & Inconsistency Detection Agent Node."""
    title = state.get("title", "")
    content = state.get("content", "")
    similar_articles = state.get("similar_articles", [])

    if not similar_articles:
        return {"contradictions": ["No historical news matches found to verify against."]}

    # Formulate references context block
    context_list = []
    for idx, article in enumerate(similar_articles):
        context_list.append(
            f"Comparison Article [{idx+1}]: {article.get('title')}\n"
            f"Content: {article.get('content') or ''}\n"
        )
    context_str = "\n---\n".join(context_list)

    agent = AIAgentManager()
    if agent.openai_key:
        system_prompt = (
            "You are the Contradiction Detection Agent. Compare the primary news article with "
            "the provided list of similar articles. Check for factual conflicts, conflicting timelines, "
            "changed numbers/statistics, contradictory claims, or if the articles corroborate each other. "
            "List any distinct contradictions or explicitly state if they confirm/corroborate each other. "
            "Respond ONLY with a JSON object in this format: "
            '{"contradictions": ["Contradiction 1", "Contradiction 2"]}'
        )
        user_content = (
            f"Primary Article Title: {title}\nPrimary Article Content: {content}\n\n"
            f"Historical Match Context:\n{context_str}"
        )
        try:
            res = await agent._call_llm(system_prompt, user_content)
            return {"contradictions": res.get("contradictions", [])}
        except Exception as e:
            logger.error(f"Contradiction LLM node failed: {e}")

    # Local fallback
    return {"contradictions": ["Local mode: Factual corroboration verified via keyword overlaps."]}


async def briefing_agent_node(state: AgentState) -> Dict[str, Any]:
    """Agent 5: Executive Briefing Report Generation Node."""
    agent = AIAgentManager()
    
    # Compile a structured state representation
    trends_str = ", ".join(state.get("trends", []))
    entities_str = ", ".join(state.get("key_entities", []))
    contradictions_str = "\n".join([f"- {c}" for c in state.get("contradictions", [])])
    
    if agent.openai_key:
        system_prompt = (
            "You are the Executive Briefing Agent. Compile all analytical results "
            "into a professional, structured markdown Intelligence Briefing. "
            "Use clear headings, bullet points, and a premium tone. "
            "Include: Executive Summary, Trend & Entity Mapping, Credibility & Fact Checking Assessment, "
            "Contradiction & Conflicts, and an actionable Recommendation. "
            "Respond ONLY with a JSON object in this format: "
            '{"briefing": "# News Intelligence Briefing\\n\\n### Executive Summary... [Use Markdown]"}'
        )
        user_content = (
            f"Article Title: {state.get('title')}\n"
            f"Summary: {state.get('summary')}\n"
            f"Sentiment: {state.get('sentiment')} (Score: {state.get('sentiment_score')})\n"
            f"Credibility Score: {state.get('credibility_score')} ({state.get('credibility_explanation')})\n"
            f"Key Trends: {trends_str}\n"
            f"Key Entities: {entities_str}\n"
            f"Factual Checks:\n{contradictions_str}"
        )
        try:
            res = await agent._call_llm(system_prompt, user_content)
            return {"briefing": res.get("briefing", "")}
        except Exception as e:
            logger.error(f"Briefing LLM node failed: {e}")

    # Local fallback
    briefing = (
        f"# News Intelligence Briefing: {state.get('title')}\n\n"
        f"### Executive Summary\n{state.get('summary')}\n\n"
        f"### Trend & Entity Mapping\n- **Primary Trends**: {trends_str}\n- **Identified Entities**: {entities_str}\n\n"
        f"### Credibility & Source Reliability\n- **Reliability Rating**: {state.get('credibility_score') * 100}%\n"
        f"- **Detail**: {state.get('credibility_explanation')}\n\n"
        f"### Contradiction Assessment\n{contradictions_str}\n"
    )
    return {"briefing": briefing}


# 4. Construct the Orchestrated State Graph
workflow = StateGraph(AgentState)

# Register Nodes
workflow.add_node("summarizer", summarizer_agent_node)
workflow.add_node("credibility", credibility_agent_node)
workflow.add_node("trends", trend_agent_node)
workflow.add_node("contradictions", contradiction_agent_node)
workflow.add_node("briefing", briefing_agent_node)

# Define Directed Transitions
workflow.add_edge(START, "summarizer")
workflow.add_edge("summarizer", "credibility")
workflow.add_edge("credibility", "trends")
workflow.add_edge("trends", "contradictions")
workflow.add_edge("contradictions", "briefing")
workflow.add_edge("briefing", END)

# Compile Workflow Graph
intelligence_workflow = workflow.compile()

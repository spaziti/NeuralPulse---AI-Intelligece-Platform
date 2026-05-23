import os
import logging
import json
from typing import Dict, Any, List
import requests
from backend.app.config import settings

logger = logging.getLogger("neuralpulse.ai_agents")


class AIAgentManager:
    def __init__(self):
        self.openai_key = settings.OPENAI_API_KEY
        self.openai_url = "https://api.openai.com/v1/chat/completions"

    async def optimize_query(self, question: str, chat_history: List[Dict[str, Any]]) -> str:
        """Optimizes search queries by resolving coreferences and rewriting them based on chat history."""
        if not chat_history or not self.openai_key:
            return question

        # Format conversation history (last 5 messages)
        history_str = ""
        for msg in chat_history[-5:]:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            history_str += f"{role}: {content}\n"

        system_prompt = (
            "You are a Query Optimization Agent. Your job is to analyze the conversation history "
            "and the user's latest follow-up question. Rewrite the follow-up question into a "
            "single, standalone, self-contained search query. This query should contain all context "
            "necessary to perform semantic and keyword database retrieval without needing the conversation history. "
            "Do NOT answer the question, only output the rewritten search query. "
            "Respond ONLY with a JSON object in this format: "
            '{"query": "The rewritten standalone search query."}'
        )

        user_content = f"Conversation History:\n{history_str}\nFollow-up Question: {question}"

        try:
            res = await self._call_llm(system_prompt, user_content)
            optimized_query = res.get("query", question)
            logger.info(f"Optimized user query from '{question}' to '{optimized_query}'")
            return optimized_query
        except Exception as e:
            logger.error(f"Failed to optimize query via LLM: {e}. Using original question.")
            return question

    async def analyze_content(self, title: str, content: str) -> Dict[str, Any]:
        """Orchestrate a Multi-Agent pipeline for processing raw news articles.

        Agents involved:
        1. Fact-Checker & Credibility Agent - Assigns a credibility score.
        2. Named Entity & Sentiment Agent - Extracts key entities and evaluates sentiment.
        3. Executive Synthesis Agent - Compiles the summary.
        """
        logger.info(f"Initiating Multi-Agent analysis pipeline for: {title}")

        if self.openai_key:
            try:
                # Agent 1: Fact-Checking & Credibility
                credibility_data = await self._run_credibility_agent(title, content)
                
                # Agent 2: Sentiment & Entity Extraction
                analysis_data = await self._run_analysis_agent(title, content)
                
                # Agent 3: Executive Synthesis
                summary_data = await self._run_synthesis_agent(title, content)
                
                # Consolidate agent responses
                return {
                    "summary": summary_data.get("summary", ""),
                    "sentiment": analysis_data.get("sentiment", "NEUTRAL").upper(),
                    "sentiment_score": float(analysis_data.get("sentiment_score", 0.0)),
                    "credibility_score": float(credibility_data.get("credibility_score", 0.8)),
                    "key_entities": ", ".join(analysis_data.get("key_entities", [])),
                }
            except Exception as e:
                logger.error(f"Multi-Agent LLM pipeline failed: {e}. Falling back to local heuristic pipeline.")

        # Fallback to local rule-based multi-agent pipeline
        return self._run_local_agents(title, content)

    async def _call_llm(self, system_prompt: str, user_content: str) -> Dict[str, Any]:
        """Wrapper to call OpenAI API in a non-blocking executor."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_key}"
        }
        payload = {
            "model": "gpt-4-turbo",
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1
        }
        
        import asyncio
        loop = asyncio.get_running_loop()
        
        def make_post():
            return requests.post(self.openai_url, json=payload, headers=headers, timeout=10)
            
        response = await loop.run_in_executor(None, make_post)
        response.raise_for_status()
        raw_content = response.json()["choices"][0]["message"]["content"]
        return json.loads(raw_content)

    async def _run_credibility_agent(self, title: str, content: str) -> Dict[str, Any]:
        """Agent 1: Evaluates facts and assigns source/content credibility."""
        system_prompt = (
            "You are the Credibility & Fact-Checking Agent. Analyze the news article. "
            "Evaluate claims, source consistency, and check for sensationalism. "
            "Assign a credibility score between 0.0 (fake news) and 1.0 (highly reliable factual reporting). "
            "Respond ONLY with a JSON object in this format: "
            '{"credibility_score": 0.9, "explanation": "factual reporting with credible metrics"}'
        )
        return await self._call_llm(system_prompt, f"Title: {title}\nContent: {content}")

    async def _run_analysis_agent(self, title: str, content: str) -> Dict[str, Any]:
        """Agent 2: Conducts sentiment classification and name entity extraction."""
        system_prompt = (
            "You are the Named Entity & Sentiment Agent. Analyze the news text. "
            "Extract up to 5 critical technologies, people, organizations, or markets (key_entities) mentioned. "
            "Also evaluate sentiment (POSITIVE, NEGATIVE, NEUTRAL) and score it between -1.0 and 1.0. "
            "Respond ONLY with a JSON object in this format: "
            '{"sentiment": "POSITIVE", "sentiment_score": 0.75, "key_entities": ["OpenAI", "GPT-4", "TechCrunch"]}'
        )
        return await self._call_llm(system_prompt, f"Title: {title}\nContent: {content}")

    async def _run_synthesis_agent(self, title: str, content: str) -> Dict[str, Any]:
        """Agent 3: Synthesizes content and outputs clean summaries."""
        system_prompt = (
            "You are the Executive Synthesis Agent. Read the news. "
            "Summarize it in 2 or 3 concise sentences. Focus on core events and outcomes. "
            "Respond ONLY with a JSON object in this format: "
            '{"summary": "A brief summary of what happened."}'
        )
        return await self._call_llm(system_prompt, f"Title: {title}\nContent: {content}")

    def _run_local_agents(self, title: str, content: str) -> Dict[str, Any]:
        """Local simulation of the multi-agent pipeline."""
        # 1. Local Credibility Agent
        credibility = 0.85
        trusted_sources = ["bloomberg", "reuters", "techcrunch", "bloomberg"]
        text_lower = (title + " " + content).lower()
        if any(src in text_lower for src in trusted_sources):
            credibility = 0.95
        elif "hack" in text_lower or "breach" in text_lower or "fake" in text_lower:
            credibility = 0.60

        # 2. Local Analysis Agent (Sentiment + Entity extraction)
        positive_words = {"surge", "gain", "rise", "revolution", "launch", "grow", "success", "innovate"}
        negative_words = {"breach", "fail", "drop", "collapse", "risk", "attack", "exploit", "compromise"}
        
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        if pos_count > neg_count:
            sentiment = "POSITIVE"
            score = 0.4 + (0.1 * min(pos_count, 5))
        elif neg_count > pos_count:
            sentiment = "NEGATIVE"
            score = -0.4 - (0.1 * min(neg_count, 5))
        else:
            sentiment = "NEUTRAL"
            score = 0.0

        # Extract uppercase acronyms or words as entities
        words = text_lower.split()
        candidate_entities = ["AI", "LLM", "ChromaDB", "FastAPI", "Next.js", "SaaS"]
        extracted_entities = [ent for ent in candidate_entities if ent.lower() in text_lower]
        if not extracted_entities:
            extracted_entities = ["Technology", "News"]

        # 3. Local Synthesis Agent
        summary = f"Summary of '{title}': The article reviews key milestones. Analysis identifies a {sentiment.lower()} market profile with {credibility * 100}% source credibility."

        return {
            "summary": summary,
            "sentiment": sentiment,
            "sentiment_score": score,
            "credibility_score": credibility,
            "key_entities": ", ".join(extracted_entities)
        }

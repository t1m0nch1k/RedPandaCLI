from __future__ import annotations

import logging
from typing import Any

from aios.core.models import Message
from aios.runtime.models import Intent, IntentCategory

logger = logging.getLogger(__name__)


class IntentEngine:
    """
    Classifies the user's input into an Intent category (CHAT, CODE_TASK, MISSION, etc.)
    using a lightweight LLM call or heuristics.
    """
    def __init__(self, llm_chat: Any) -> None:
        self.llm_chat = llm_chat
        
    async def classify_intent(self, text: str) -> Intent:
        """
        Determine the user's intent based on the text.
        """
        # Heuristics for quick routing
        text_lower = text.lower().strip()
        
        code_keywords = ["write code", "refactor", "напиши", "создай файл", "исправь", "fix", "debug", "implement"]
        mission_keywords = ["/mission", "plan", "goal", "миссия", "автономно"]
        
        if text_lower.startswith("/code") or any(kw in text_lower for kw in code_keywords):
            return Intent(category=IntentCategory.CODE_TASK, confidence=0.9, reasoning="Heuristic matched code keywords")
            
        if any(kw in text_lower for kw in mission_keywords):
            return Intent(category=IntentCategory.MISSION, confidence=0.9, reasoning="Heuristic matched mission keywords")
            
        if text_lower.startswith("/chat") or len(text_lower.split()) < 4:
            return Intent(category=IntentCategory.CHAT, confidence=0.7, reasoning="Short message or chat keyword")

        # Fallback to LLM if heuristics are not definitive
        system_prompt = (
            "You are an Intent Classifier. Given the user's message, classify it into one of these categories: "
            "1. 'code_task': The user wants to write, edit, or analyze code.\n"
            "2. 'mission': The user wants you to perform a complex, multi-step autonomous task.\n"
            "3. 'command': The user is asking about system settings, configuration, or help.\n"
            "4. 'chat': General conversation, quick questions, or unclear requests.\n\n"
            "Respond ONLY with the category name (e.g., 'code_task')."
        )
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=text)
        ]
        
        try:
            response = await self.llm_chat(messages, temperature=0.0)
            # provider.complete() returns a string
            result = response.strip().lower()
            
            if "code" in result:
                category = IntentCategory.CODE_TASK
            elif "mission" in result:
                category = IntentCategory.MISSION
            elif "command" in result:
                category = IntentCategory.COMMAND
            else:
                category = IntentCategory.CHAT
                
            return Intent(category=category, confidence=0.8, reasoning=f"LLM classified as {category.value}")
            
        except Exception as e:
            logger.warning(f"Intent classification failed, defaulting to chat: {e}")
            return Intent(category=IntentCategory.CHAT, confidence=0.5, reasoning="Fallback due to error")

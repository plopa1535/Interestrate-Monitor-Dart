"""
Chat Service using Groq API with Qwen3 32B
Provides AI chat functionality with interest rate context and news data.
"""

import os
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Groq
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("groq package not installed. Chat will be unavailable.")


class ChatService:
    """Service for AI chat using Groq API with Qwen3 32B."""

    # Qwen3 32B model on Groq (free tier: 1,000 RPD, 30 RPM)
    MODEL_NAME = "qwen/qwen3-32b"

    # System prompt for chat
    SYSTEM_PROMPT = """당신은 금리 및 채권 시장 전문 AI 어시스턴트입니다.
사용자의 질문에 친절하고 전문적으로 답변해 주세요.

## 현재 시장 상황
{market_context}

## 최신 뉴스
{news_context}

## 답변 규칙
- 한국어로 답변하세요
- 간결하고 명확하게 답변하세요 (최대 4-5문장)
- 금리, 채권, 통화정책 관련 질문에 집중하세요
- 위에 제공된 시장 데이터와 뉴스를 참고하여 답변하세요
- 투자 조언은 일반적인 정보 제공 수준으로만 하세요
- 구체적인 수치가 있으면 포함하세요
- 뉴스 내용을 언급할 때는 출처를 함께 언급하세요
- /no_think 모드로 응답하세요 (추론 과정 없이 바로 답변)"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the chat service with Groq API key."""
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        self.client = None

        if self.api_key and GROQ_AVAILABLE:
            try:
                self.client = Groq(api_key=self.api_key)
                logger.info("Groq chat service initialized with Qwen3 32B")
            except Exception as e:
                logger.error(f"Failed to initialize Groq: {e}")
        else:
            if not self.api_key:
                logger.warning("Groq API key not provided")
            if not GROQ_AVAILABLE:
                logger.warning("Groq library not available")

    def chat(
        self,
        message: str,
        rate_context: dict = None,
        us_news: list = None,
        kr_news: list = None
    ) -> str:
        """
        Chat with AI about interest rates.

        Args:
            message: User's chat message
            rate_context: Dict with us_rate, kr_rate, spread
            us_news: List of US news items
            kr_news: List of Korean news items

        Returns:
            AI response text
        """
        if not self.client or not GROQ_AVAILABLE:
            return "AI 채팅 서비스를 사용할 수 없습니다. GROQ_API_KEY를 확인해 주세요."

        try:
            # Format market context
            market_context = self._format_market_context(rate_context)

            # Format news context
            news_context = self._format_news_context(us_news, kr_news)

            # Build system prompt with context
            system_prompt = self.SYSTEM_PROMPT.format(
                market_context=market_context,
                news_context=news_context
            )

            # Generate response using Groq with Qwen3
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                model=self.MODEL_NAME,
                temperature=0.7,
                max_tokens=600,
            )

            # Extract response
            if chat_completion.choices and len(chat_completion.choices) > 0:
                response = chat_completion.choices[0].message.content.strip()
                # Remove any thinking tags if present
                if "<think>" in response:
                    response = response.split("</think>")[-1].strip()
                return response

            return "응답을 생성할 수 없습니다. 다시 시도해 주세요."

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in chat: {error_msg}")

            # Handle rate limit errors
            if "429" in error_msg or "rate_limit" in error_msg.lower():
                return "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요. (Groq 무료 티어: 30 RPM, 1,000 RPD)"

            return f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {error_msg[:100]}"

    def _format_market_context(self, rate_context: dict) -> str:
        """Format rate data for the prompt."""
        if not rate_context:
            return "현재 금리 데이터 없음"

        us_rate = rate_context.get('us_rate', 'N/A')
        kr_rate = rate_context.get('kr_rate', 'N/A')
        spread = rate_context.get('spread', 'N/A')

        # Format spread status
        spread_status = ""
        if spread != 'N/A' and isinstance(spread, (int, float)):
            if spread < 0:
                spread_status = f" (역전 상태, 원화 약세 압력)"
            else:
                spread_status = f" (정상 상태)"

        return (
            f"- 미국 10년물 국고채 금리: {us_rate}%\n"
            f"- 한국 10년물 국고채 금리: {kr_rate}%\n"
            f"- 한미 금리 스프레드: {spread}bp{spread_status}"
        )

    def _format_news_context(self, us_news: list, kr_news: list) -> str:
        """Format news data for the prompt."""
        news_parts = []

        # US News
        if us_news and len(us_news) > 0:
            news_parts.append("### 미국 금리 관련 뉴스")
            for i, item in enumerate(us_news[:3], 1):
                title = item.get('title', '')
                source = item.get('source', '')
                if title:
                    news_parts.append(f"{i}. [{source}] {title}")
        else:
            news_parts.append("### 미국 금리 관련 뉴스\n최신 뉴스 없음")

        news_parts.append("")  # Empty line

        # Korean News
        if kr_news and len(kr_news) > 0:
            news_parts.append("### 한국 금리 관련 뉴스")
            for i, item in enumerate(kr_news[:3], 1):
                title = item.get('title', '')
                source = item.get('source', '')
                if title:
                    news_parts.append(f"{i}. [{source}] {title}")
        else:
            news_parts.append("### 한국 금리 관련 뉴스\n최신 뉴스 없음")

        return "\n".join(news_parts)

    def is_available(self) -> bool:
        """Check if the chat service is available."""
        return self.client is not None and GROQ_AVAILABLE


# Singleton instance
_chat_service_instance: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Get or create the chat service singleton."""
    global _chat_service_instance
    if _chat_service_instance is None:
        _chat_service_instance = ChatService()
    return _chat_service_instance

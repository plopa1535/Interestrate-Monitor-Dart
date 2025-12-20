"""
AI Analysis Service using Google Gemini 2.5 Flash
Generates market analysis for interest rate trends.
"""

import os
import logging
from typing import Optional
from datetime import datetime
from cachetools import TTLCache
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed. AI analysis will be unavailable.")


class AIAnalysisService:
    """Service for generating AI-powered interest rate analysis using Gemini."""
    
    MODEL_NAME = "gemini-2.0-flash"
    
    # Cache for analysis (TTL: 6 hours)
    _cache = TTLCache(maxsize=10, ttl=21600)
    
    # Analysis prompt template
    ANALYSIS_PROMPT = """당신은 채권 시장 전문 애널리스트입니다. 아래의 미국과 한국 10년물 국고채 금리 데이터를 분석하여 최신 동향을 요약해 주세요.

## 데이터
### 미국 10년물 국고채 금리 (최근 30일)
{us_data}

### 한국 10년물 국고채 금리 (최근 30일)
{kr_data}

### 현재 스프레드 (한국 - 미국)
{spread}bp

## 요구사항
- 정확히 2문장으로 요약하세요.
- 첫 번째 문장: 최근 금리 추세 및 주요 변동 요인을 분석하세요.
- 두 번째 문장: 향후 단기 전망 또는 투자자가 주의해야 할 포인트를 제시하세요.
- 전문적이면서도 간결한 애널리스트 톤으로 작성하세요.
- 구체적인 수치를 포함하세요.

분석 결과:"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the AI service with API key."""
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model = None
        
        if self.api_key and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.MODEL_NAME)
                logger.info("Gemini AI model initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
        else:
            if not self.api_key:
                logger.warning("Gemini API key not provided")
            if not GEMINI_AVAILABLE:
                logger.warning("Gemini library not available")
    
    def generate_rate_analysis(
        self, 
        us_rates: pd.DataFrame, 
        kr_rates: pd.DataFrame,
        spread: float
    ) -> str:
        """
        Generate AI analysis of interest rate trends.
        
        Args:
            us_rates: DataFrame with US rate data (date, us_rate)
            kr_rates: DataFrame with Korean rate data (date, kr_rate)
            spread: Current spread in basis points
            
        Returns:
            Analysis text (2 sentences)
        """
        # Check cache first
        cache_key = self._get_cache_key(us_rates, kr_rates)
        if cache_key in self._cache:
            logger.info("Returning cached analysis")
            return self._cache[cache_key]
        
        if not self.model:
            logger.warning("AI model not available, returning default message")
            return self._get_default_analysis(us_rates, kr_rates, spread)
        
        try:
            # Prepare data summary for prompt
            us_summary = self._format_rate_data(us_rates, "us_rate")
            kr_summary = self._format_rate_data(kr_rates, "kr_rate")
            
            # Build prompt
            prompt = self.ANALYSIS_PROMPT.format(
                us_data=us_summary,
                kr_data=kr_summary,
                spread=f"{spread:.1f}"
            )
            
            # Generate analysis
            generation_config = genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=200,
            )
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            analysis = response.text.strip()
            
            # Validate response (should be approximately 2 sentences)
            if len(analysis) < 50 or len(analysis) > 500:
                logger.warning("Analysis length unexpected, using default")
                analysis = self._get_default_analysis(us_rates, kr_rates, spread)
            
            # Cache the result
            self._cache[cache_key] = analysis
            logger.info("Generated new AI analysis")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error generating analysis: {e}")
            return self._get_default_analysis(us_rates, kr_rates, spread)
    
    def _format_rate_data(self, df: pd.DataFrame, rate_col: str) -> str:
        """Format rate data for the prompt."""
        if df.empty:
            return "데이터 없음"
        
        # Get summary statistics
        latest = df.iloc[-1][rate_col] if len(df) > 0 else 0
        first = df.iloc[0][rate_col] if len(df) > 0 else 0
        change = latest - first
        high = df[rate_col].max()
        low = df[rate_col].min()
        
        # Get dates
        start_date = df.iloc[0]["date"].strftime("%Y-%m-%d") if len(df) > 0 else "N/A"
        end_date = df.iloc[-1]["date"].strftime("%Y-%m-%d") if len(df) > 0 else "N/A"
        
        return (
            f"기간: {start_date} ~ {end_date}\n"
            f"현재: {latest:.3f}%\n"
            f"기간 변동: {change:+.3f}%p\n"
            f"고점: {high:.3f}%, 저점: {low:.3f}%"
        )
    
    def _get_cache_key(self, us_rates: pd.DataFrame, kr_rates: pd.DataFrame) -> str:
        """Generate cache key based on latest data."""
        us_latest = us_rates.iloc[-1]["date"].strftime("%Y%m%d") if not us_rates.empty else "none"
        kr_latest = kr_rates.iloc[-1]["date"].strftime("%Y%m%d") if not kr_rates.empty else "none"
        return f"analysis_{us_latest}_{kr_latest}"
    
    def _get_default_analysis(
        self, 
        us_rates: pd.DataFrame, 
        kr_rates: pd.DataFrame,
        spread: float
    ) -> str:
        """Generate a default analysis when AI is unavailable."""
        if us_rates.empty or kr_rates.empty:
            return "현재 금리 데이터를 불러올 수 없어 분석이 제공되지 않습니다. 잠시 후 다시 시도해 주세요."
        
        # Calculate basic metrics
        us_latest = us_rates.iloc[-1]["us_rate"]
        kr_latest = kr_rates.iloc[-1]["kr_rate"]
        us_change = us_rates.iloc[-1]["us_rate"] - us_rates.iloc[0]["us_rate"]
        kr_change = kr_rates.iloc[-1]["kr_rate"] - kr_rates.iloc[0]["kr_rate"]
        
        # Determine trend direction
        us_trend = "상승" if us_change > 0.05 else ("하락" if us_change < -0.05 else "보합")
        kr_trend = "상승" if kr_change > 0.05 else ("하락" if kr_change < -0.05 else "보합")
        
        sentence1 = (
            f"최근 30일간 미국 10년물 금리는 {us_latest:.2f}%로 {us_trend}세를 보이고 있으며, "
            f"한국 10년물 금리는 {kr_latest:.2f}%로 {kr_trend}세를 나타내고 있습니다."
        )
        
        if spread < 0:
            sentence2 = (
                f"현재 한미 금리차는 {abs(spread):.0f}bp 역전 상태로, "
                f"원화 약세 압력과 외국인 자금 유출 가능성에 주의가 필요합니다."
            )
        else:
            sentence2 = (
                f"현재 한미 금리차는 {spread:.0f}bp로, "
                f"연준과 한은의 통화정책 방향성에 따른 금리 변동성 확대에 유의해야 합니다."
            )
        
        return f"{sentence1} {sentence2}"
    
    def clear_cache(self):
        """Clear the analysis cache."""
        self._cache.clear()
        logger.info("Analysis cache cleared")


# Singleton instance
_ai_service_instance: Optional[AIAnalysisService] = None


def get_ai_service() -> AIAnalysisService:
    """Get or create the AI service singleton."""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIAnalysisService()
    return _ai_service_instance

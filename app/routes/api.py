"""
API Routes for Interest Rate Monitor
Provides RESTful endpoints for rate data, AI analysis, and news.
"""

from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
import logging
import json
import os

from app.services.rate_service import get_rate_service
from app.services.ai_analysis_service import get_ai_service
from app.services.news_service import get_news_service
from app.services.chat_service import get_chat_service

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


def create_response(status: str, data=None, error: str = None):
    """Create standardized API response."""
    response = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
    }
    if data is not None:
        response["data"] = data
    if error:
        response["error"] = error
    return response


@api_bp.route('/rates', methods=['GET'])
def get_rates():
    """
    Get historical interest rate data.
    
    Query Parameters:
        days (int): Number of days of data (default: 90, max: 365)
        
    Returns:
        JSON with US/Korean rates and spread data
    """
    try:
        days = request.args.get('days', 90, type=int)
        days = min(max(days, 1), 365)  # Clamp between 1 and 365
        
        rate_service = get_rate_service()
        combined_data = rate_service.get_combined_rates(days=days)
        
        if combined_data.empty:
            return jsonify(create_response(
                status="error",
                error="No rate data available"
            )), 404
        
        # Convert to JSON-serializable format
        records = []
        for _, row in combined_data.iterrows():
            records.append({
                "date": row["date"].strftime("%Y-%m-%d"),
                "us_rate": round(float(row["us_rate"]), 3),
                "kr_rate": round(float(row["kr_rate"]), 3),
                "spread": round(float(row["spread"]), 1)
            })
        
        return jsonify(create_response(
            status="success",
            data={
                "rates": records,
                "count": len(records),
                "period_days": days
            }
        ))
        
    except Exception as e:
        logger.error(f"Error fetching rates: {e}")
        return jsonify(create_response(
            status="error",
            error="Failed to fetch rate data"
        )), 500


@api_bp.route('/rates/latest', methods=['GET'])
def get_latest_rates():
    """
    Get the most recent rate data.
    
    Returns:
        JSON with latest US rate, Korean rate, and spread
    """
    try:
        rate_service = get_rate_service()
        latest = rate_service.get_latest_rates()
        
        if latest.get("error"):
            return jsonify(create_response(
                status="error",
                error=latest["error"]
            )), 404
        
        return jsonify(create_response(
            status="success",
            data=latest
        ))
        
    except Exception as e:
        logger.error(f"Error fetching latest rates: {e}")
        return jsonify(create_response(
            status="error",
            error="Failed to fetch latest rate data"
        )), 500


@api_bp.route('/analysis', methods=['GET'])
def get_analysis():
    """
    Get AI-generated market analysis.

    Returns:
        JSON with analysis text and metadata
    """
    try:
        rate_service = get_rate_service()
        ai_service = get_ai_service()
        news_service = get_news_service()

        # Get rate data for analysis
        combined_data = rate_service.get_combined_rates(days=30)

        if combined_data.empty:
            return jsonify(create_response(
                status="error",
                error="Insufficient rate data for analysis"
            )), 404

        # Prepare data for analysis
        us_rates = combined_data[["date", "us_rate"]].copy()
        kr_rates = combined_data[["date", "kr_rate"]].copy()
        current_spread = combined_data.iloc[-1]["spread"]

        # Get news data for analysis
        us_news = news_service.get_us_rate_news(limit=5)
        kr_news = news_service.get_kr_rate_news(limit=5)

        # Generate analysis with news context
        analysis_text = ai_service.generate_rate_analysis(
            us_rates=us_rates,
            kr_rates=kr_rates,
            spread=current_spread,
            us_news=us_news,
            kr_news=kr_news
        )

        return jsonify(create_response(
            status="success",
            data={
                "analysis": analysis_text,
                "generated_at": datetime.now().isoformat(),
                "data_date": combined_data.iloc[-1]["date"].strftime("%Y-%m-%d")
            }
        ))

    except Exception as e:
        logger.error(f"Error generating analysis: {e}")
        return jsonify(create_response(
            status="error",
            error="Failed to generate analysis"
        )), 500


@api_bp.route('/news', methods=['GET'])
def get_news():
    """
    Get interest rate related news.
    
    Query Parameters:
        country (str): 'us', 'kr', or 'all' (default: 'all')
        limit (int): Number of news items per country (default: 5, max: 10)
        
    Returns:
        JSON with news items
    """
    try:
        country = request.args.get('country', 'all').lower()
        limit = request.args.get('limit', 5, type=int)
        limit = min(max(limit, 1), 10)  # Clamp between 1 and 10
        
        news_service = get_news_service()
        
        if country == 'us':
            news_data = {"us": news_service.get_us_rate_news(limit)}
        elif country == 'kr':
            news_data = {"kr": news_service.get_kr_rate_news(limit)}
        else:
            news_data = news_service.get_all_news(limit)
        
        # Add relative time to each news item
        for country_key in news_data:
            for item in news_data[country_key]:
                item["relative_time"] = news_service.get_relative_time(
                    item.get("published_at", "")
                )
        
        return jsonify(create_response(
            status="success",
            data=news_data
        ))
        
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return jsonify(create_response(
            status="error",
            error="Failed to fetch news"
        )), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    
    Returns:
        JSON with service status
    """
    return jsonify(create_response(
        status="success",
        data={
            "service": "Interest Rate Monitor API",
            "version": "1.0.0",
            "healthy": True
        }
    ))


@api_bp.route('/cache/clear', methods=['POST'])
def clear_cache():
    """
    Clear all service caches.

    Returns:
        JSON confirmation
    """
    try:
        get_rate_service().clear_cache()
        get_ai_service().clear_cache()
        get_news_service().clear_cache()

        return jsonify(create_response(
            status="success",
            data={"message": "All caches cleared"}
        ))

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify(create_response(
            status="error",
            error="Failed to clear cache"
        )), 500


@api_bp.route('/forecast', methods=['GET'])
def get_forecast():
    """
    Get analyst forecast data for interest rates.

    Returns:
        JSON with 12-month forecast data
    """
    try:
        # Get the path to forecast.json
        forecast_path = os.path.join(
            current_app.root_path,
            '..',
            'static',
            'data',
            'forecast.json'
        )
        forecast_path = os.path.normpath(forecast_path)

        if not os.path.exists(forecast_path):
            return jsonify(create_response(
                status="error",
                error="Forecast data not found"
            )), 404

        with open(forecast_path, 'r', encoding='utf-8') as f:
            forecast_data = json.load(f)

        return jsonify(create_response(
            status="success",
            data=forecast_data
        ))

    except Exception as e:
        logger.error(f"Error fetching forecast: {e}")
        return jsonify(create_response(
            status="error",
            error="Failed to fetch forecast data"
        )), 500


@api_bp.route('/chat', methods=['POST'])
def chat():
    """
    Chat with AI about interest rates using Groq + Qwen3 32B.

    Request Body:
        message (str): User's chat message

    Returns:
        JSON with AI response
    """
    try:
        data = request.get_json()
        if not data or not data.get('message'):
            return jsonify(create_response(
                status="error",
                error="Message is required"
            )), 400

        message = data['message'].strip()
        if len(message) > 500:
            return jsonify(create_response(
                status="error",
                error="Message too long (max 500 characters)"
            )), 400

        # Get services
        rate_service = get_rate_service()
        news_service = get_news_service()
        chat_service = get_chat_service()

        # Get current rate context
        rate_context = None
        try:
            latest = rate_service.get_latest_rates()
            if not latest.get("error"):
                rate_context = {
                    "us_rate": latest.get("us_rate"),
                    "kr_rate": latest.get("kr_rate"),
                    "spread": latest.get("spread")
                }
        except Exception:
            pass  # Continue without rate context

        # Get news context
        us_news = None
        kr_news = None
        try:
            us_news = news_service.get_us_rate_news(limit=7)
            kr_news = news_service.get_kr_rate_news(limit=7)
        except Exception:
            pass  # Continue without news context

        # Generate response using Groq + Qwen3
        response_text = chat_service.chat(
            message=message,
            rate_context=rate_context,
            us_news=us_news,
            kr_news=kr_news
        )

        return jsonify(create_response(
            status="success",
            data={
                "response": response_text,
                "timestamp": datetime.now().isoformat()
            }
        ))

    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return jsonify(create_response(
            status="error",
            error="Failed to process chat message"
        )), 500

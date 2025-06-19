import logging
import traceback
import asyncio
from functools import wraps
from typing import Callable, Any, Dict, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class ErrorHandler:
    """
    Comprehensive error handling and recovery system
    """
    
    def __init__(self):
        self.error_counts = {}
        self.last_errors = {}
        self.circuit_breaker_status = {}
        self.fallback_data = {}
    
    def handle_api_error(self, error: Exception, api_name: str, fallback_data: Any = None) -> Any:
        """Handle API errors with fallback strategies"""
        error_key = f"{api_name}_{type(error).__name__}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        self.last_errors[error_key] = {
            "timestamp": datetime.now(),
            "error": str(error),
            "traceback": traceback.format_exc()
        }
        
        logger.error(f"API error in {api_name}: {error}")
        
        # Circuit breaker logic
        if self.error_counts[error_key] > 5:
            logger.warning(f"Circuit breaker activated for {api_name}")
            self.circuit_breaker_status[api_name] = {
                "active": True,
                "activated_at": datetime.now()
            }
        
        # Return fallback data if available
        if fallback_data is not None:
            logger.info(f"Using fallback data for {api_name}")
            return fallback_data
        
        # Return cached data if available
        if api_name in self.fallback_data:
            logger.info(f"Using cached fallback data for {api_name}")
            return self.fallback_data[api_name]
        
        # If no fallback, re-raise the error
        raise error
    
    def cache_fallback_data(self, api_name: str, data: Any):
        """Cache successful API responses for fallback use"""
        self.fallback_data[api_name] = {
            "data": data,
            "cached_at": datetime.now()
        }
    
    def is_circuit_breaker_active(self, api_name: str) -> bool:
        """Check if circuit breaker is active for an API"""
        if api_name not in self.circuit_breaker_status:
            return False
        
        status = self.circuit_breaker_status[api_name]
        if not status.get("active", False):
            return False
        
        # Reset circuit breaker after 5 minutes
        time_since_activation = (datetime.now() - status["activated_at"]).total_seconds()
        if time_since_activation > 300:  # 5 minutes
            logger.info(f"Circuit breaker reset for {api_name}")
            self.circuit_breaker_status[api_name]["active"] = False
            return False
        
        return True
    
    def get_error_report(self) -> Dict[str, Any]:
        """Generate error report for monitoring"""
        return {
            "error_counts": self.error_counts,
            "last_errors": {k: v for k, v in self.last_errors.items()},
            "circuit_breakers": self.circuit_breaker_status,
            "cached_fallbacks": list(self.fallback_data.keys())
        }

# Global error handler instance
error_handler = ErrorHandler()

def with_error_handling(api_name: str, fallback_data: Any = None):
    """Decorator for API calls with error handling"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if error_handler.is_circuit_breaker_active(api_name):
                logger.warning(f"Circuit breaker active for {api_name}, using fallback")
                if fallback_data is not None:
                    return fallback_data
                if api_name in error_handler.fallback_data:
                    return error_handler.fallback_data[api_name]["data"]
                raise Exception(f"Circuit breaker active for {api_name} and no fallback available")
            
            try:
                result = await func(*args, **kwargs)
                error_handler.cache_fallback_data(api_name, result)
                return result
            except Exception as e:
                return error_handler.handle_api_error(e, api_name, fallback_data)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if error_handler.is_circuit_breaker_active(api_name):
                logger.warning(f"Circuit breaker active for {api_name}, using fallback")
                if fallback_data is not None:
                    return fallback_data
                if api_name in error_handler.fallback_data:
                    return error_handler.fallback_data[api_name]["data"]
                raise Exception(f"Circuit breaker active for {api_name} and no fallback available")
            
            try:
                result = func(*args, **kwargs)
                error_handler.cache_fallback_data(api_name, result)
                return result
            except Exception as e:
                return error_handler.handle_api_error(e, api_name, fallback_data)
        
        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def safe_execute(func: Callable, *args, default_return=None, **kwargs):
    """Safely execute a function with error handling"""
    try:
        if asyncio.iscoroutinefunction(func):
            return asyncio.create_task(func(*args, **kwargs))
        else:
            return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error executing {func.__name__}: {e}")
        return default_return

class GracefulDegradation:
    """
    Implements graceful degradation strategies
    """
    
    @staticmethod
    def get_demo_markets():
        """Return demo market data when API is unavailable"""
        return [
            {
                "id": "demo_election_2024",
                "question": "Will the Democratic candidate win the 2024 US Presidential Election?",
                "category": "Politics",
                "volume": 1250000.0,
                "liquidity": 85000.0,
                "yes_price": 0.52,
                "no_price": 0.48,
                "end_date": "2024-11-05T00:00:00Z"
            },
            {
                "id": "demo_bitcoin_50k",
                "question": "Will Bitcoin reach $50,000 by end of 2024?",
                "category": "Crypto",
                "volume": 890000.0,
                "liquidity": 45000.0,
                "yes_price": 0.68,
                "no_price": 0.32,
                "end_date": "2024-12-31T23:59:59Z"
            }
        ]
    
    @staticmethod
    def get_offline_analysis(market: Dict):
        """Return basic analysis when AI API is unavailable"""
        return {
            "fair_value": market.get("yes_price", 0.5),
            "volatility": 0.25,
            "trend": "neutral",
            "confidence": 0.5,
            "key_factors": ["Market dynamics", "Price action", "Volume analysis"],
            "price_targets": {
                "support": max(0.01, market.get("yes_price", 0.5) * 0.9),
                "resistance": min(0.99, market.get("yes_price", 0.5) * 1.1)
            }
        }
    
    @staticmethod
    def simulate_trade_execution(market_id: str, side: str, size: float, price: float):
        """Simulate trade execution when API is unavailable"""
        return {
            "success": True,
            "order_id": f"demo_{datetime.now().timestamp()}",
            "executed_size": size,
            "executed_price": price,
            "fee": size * price * 0.001,
            "demo_mode": True
        }

class HealthMonitor:
    """
    Monitor system health and component status
    """
    
    def __init__(self):
        self.component_status = {}
        self.last_health_check = datetime.now()
    
    def check_component_health(self, component_name: str, check_func: Callable) -> bool:
        """Check health of a system component"""
        try:
            result = check_func()
            self.component_status[component_name] = {
                "status": "healthy",
                "last_check": datetime.now(),
                "details": result
            }
            return True
        except Exception as e:
            self.component_status[component_name] = {
                "status": "unhealthy",
                "last_check": datetime.now(),
                "error": str(e)
            }
            logger.error(f"Health check failed for {component_name}: {e}")
            return False
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        healthy_components = sum(
            1 for status in self.component_status.values() 
            if status.get("status") == "healthy"
        )
        total_components = len(self.component_status)
        
        return {
            "overall_status": "healthy" if healthy_components == total_components else "degraded",
            "healthy_components": healthy_components,
            "total_components": total_components,
            "components": self.component_status,
            "last_check": self.last_health_check
        }

# Global health monitor
health_monitor = HealthMonitor()

# Logging configuration for error tracking
def setup_error_logging():
    """Setup comprehensive error logging"""
    
    # Create error logger
    error_logger = logging.getLogger("errors")
    error_logger.setLevel(logging.ERROR)
    
    # Create file handler for errors
    error_handler_file = logging.FileHandler("logs/errors.log")
    error_handler_file.setLevel(logging.ERROR)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    error_handler_file.setFormatter(formatter)
    
    # Add handler to logger
    error_logger.addHandler(error_handler_file)
    
    return error_logger
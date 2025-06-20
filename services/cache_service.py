"""
Cache Service for Search Wizard
Handles Redis-based caching for parsed documents and templates
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

class CacheService:
    """
    Redis-based caching service for document parsing results
    """
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = None
        self.default_ttl = 7 * 24 * 3600  # 7 days
        self.template_ttl = 30 * 24 * 3600  # 30 days for templates
        
    async def connect(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            await self.redis_client.ping()
            print("✅ Redis connection established")
            return True
        except Exception as e:
            print(f"❌ Redis connection failed: {str(e)}")
            print("📝 Falling back to memory-only caching")
            self.redis_client = None
            self._memory_cache = {}
            return False
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    def _get_key(self, key_type: str, identifier: str) -> str:
        """Generate cache key with namespace"""
        return f"search_wizard:{key_type}:{identifier}"
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from cache"""
        try:
            if self.redis_client:
                cached = await self.redis_client.get(key)
                return json.loads(cached) if cached else None
            else:
                # Fallback to memory cache
                return self._memory_cache.get(key)
        except Exception as e:
            print(f"Cache get error: {str(e)}")
            return None
    
    async def set(self, key: str, value: Dict[str, Any], ttl: int = None) -> bool:
        """Set value in cache"""
        try:
            ttl = ttl or self.default_ttl
            
            if self.redis_client:
                await self.redis_client.setex(key, ttl, json.dumps(value))
                return True
            else:
                # Fallback to memory cache (no TTL in memory)
                self._memory_cache[key] = value
                return True
        except Exception as e:
            print(f"Cache set error: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if self.redis_client:
                result = await self.redis_client.delete(key)
                return result > 0
            else:
                return self._memory_cache.pop(key, None) is not None
        except Exception as e:
            print(f"Cache delete error: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            if self.redis_client:
                return await self.redis_client.exists(key) > 0
            else:
                return key in self._memory_cache
        except Exception as e:
            print(f"Cache exists error: {str(e)}")
            return False
    
    # Document parsing cache methods
    async def get_parsed_document(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached parsed document by file hash"""
        key = self._get_key("parsed_doc", file_hash)
        return await self.get(key)
    
    async def cache_parsed_document(self, file_hash: str, parsed_data: Dict[str, Any], ttl: int = None) -> bool:
        """Cache parsed document result"""
        key = self._get_key("parsed_doc", file_hash)
        return await self.set(key, parsed_data, ttl)
    
    async def invalidate_parsed_document(self, file_hash: str) -> bool:
        """Remove parsed document from cache"""
        key = self._get_key("parsed_doc", file_hash)
        return await self.delete(key)
    
    # Template cache methods
    async def get_global_templates(self, category: str = None) -> Optional[List[Dict[str, Any]]]:
        """Get cached global templates"""
        cache_key = f"global_templates:{category or 'all'}"
        key = self._get_key("templates", cache_key)
        return await self.get(key)
    
    async def cache_global_templates(self, templates: List[Dict[str, Any]], category: str = None, ttl: int = None) -> bool:
        """Cache global templates"""
        cache_key = f"global_templates:{category or 'all'}"
        key = self._get_key("templates", cache_key)
        ttl = ttl or self.template_ttl
        return await self.set(key, templates, ttl)
    
    async def invalidate_global_templates(self, category: str = None) -> bool:
        """Invalidate global templates cache"""
        cache_key = f"global_templates:{category or 'all'}"
        key = self._get_key("templates", cache_key)
        return await self.delete(key)
    
    async def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get specific template by ID"""
        key = self._get_key("template", template_id)
        return await self.get(key)
    
    async def cache_template(self, template_id: str, template_data: Dict[str, Any], ttl: int = None) -> bool:
        """Cache specific template"""
        key = self._get_key("template", template_id)
        ttl = ttl or self.template_ttl
        return await self.set(key, template_data, ttl)
    
    # Structure analysis cache methods
    async def get_structure_analysis(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached structure analysis"""
        key = self._get_key("structure", content_hash)
        return await self.get(key)
    
    async def cache_structure_analysis(self, content_hash: str, analysis_data: Dict[str, Any], ttl: int = None) -> bool:
        """Cache structure analysis result"""
        key = self._get_key("structure", content_hash)
        return await self.set(key, analysis_data, ttl)
    
    # Analytics and monitoring
    async def increment_counter(self, counter_name: str, by: int = 1) -> int:
        """Increment a counter (for usage analytics)"""
        try:
            if self.redis_client:
                key = self._get_key("counter", counter_name)
                return await self.redis_client.incrby(key, by)
            else:
                # Memory fallback
                counter_key = f"counter_{counter_name}"
                current = self._memory_cache.get(counter_key, 0)
                self._memory_cache[counter_key] = current + by
                return current + by
        except Exception as e:
            print(f"Counter increment error: {str(e)}")
            return 0
    
    async def get_counter(self, counter_name: str) -> int:
        """Get counter value"""
        try:
            if self.redis_client:
                key = self._get_key("counter", counter_name)
                value = await self.redis_client.get(key)
                return int(value) if value else 0
            else:
                counter_key = f"counter_{counter_name}"
                return self._memory_cache.get(counter_key, 0)
        except Exception as e:
            print(f"Counter get error: {str(e)}")
            return 0
    
    async def track_parser_usage(self, parser_type: str, success: bool = True) -> None:
        """Track parser usage statistics"""
        await self.increment_counter(f"parser_{parser_type}_total")
        if success:
            await self.increment_counter(f"parser_{parser_type}_success")
        else:
            await self.increment_counter(f"parser_{parser_type}_error")
    
    async def get_parser_stats(self) -> Dict[str, Dict[str, int]]:
        """Get parser usage statistics"""
        parsers = ["llamaparse_premium", "llamaparse_fast", "legacy_pymupdf", "basic_fallback"]
        stats = {}
        
        for parser in parsers:
            total = await self.get_counter(f"parser_{parser}_total")
            success = await self.get_counter(f"parser_{parser}_success")
            error = await self.get_counter(f"parser_{parser}_error")
            
            stats[parser] = {
                "total": total,
                "success": success,
                "error": error,
                "success_rate": (success / total * 100) if total > 0 else 0
            }
        
        return stats
    
    # Cache management
    async def get_cache_info(self) -> Dict[str, Any]:
        """Get cache statistics and info"""
        try:
            if self.redis_client:
                info = await self.redis_client.info()
                return {
                    "type": "redis",
                    "connected": True,
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0)
                }
            else:
                return {
                    "type": "memory",
                    "connected": True,
                    "cached_items": len(self._memory_cache),
                    "memory_usage": "unknown"
                }
        except Exception as e:
            return {
                "type": "unknown",
                "connected": False,
                "error": str(e)
            }
    
    async def clear_cache(self, pattern: str = None) -> int:
        """Clear cache (optionally by pattern)"""
        try:
            if self.redis_client:
                if pattern:
                    # Get keys matching pattern and delete them
                    keys = await self.redis_client.keys(f"search_wizard:*{pattern}*")
                    if keys:
                        return await self.redis_client.delete(*keys)
                    return 0
                else:
                    # Clear all search_wizard keys
                    keys = await self.redis_client.keys("search_wizard:*")
                    if keys:
                        return await self.redis_client.delete(*keys)
                    return 0
            else:
                # Memory cache
                if pattern:
                    keys_to_delete = [k for k in self._memory_cache.keys() if pattern in k]
                    for key in keys_to_delete:
                        del self._memory_cache[key]
                    return len(keys_to_delete)
                else:
                    count = len(self._memory_cache)
                    self._memory_cache.clear()
                    return count
        except Exception as e:
            print(f"Cache clear error: {str(e)}")
            return 0

# Global cache instance
_cache_instance = None

async def get_cache() -> CacheService:
    """Get global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService()
        await _cache_instance.connect()
    return _cache_instance

# Convenience functions
async def get_cached_document(file_hash: str) -> Optional[Dict[str, Any]]:
    """Get cached document (convenience function)"""
    cache = await get_cache()
    return await cache.get_parsed_document(file_hash)

async def cache_document(file_hash: str, data: Dict[str, Any]) -> bool:
    """Cache document (convenience function)"""
    cache = await get_cache()
    return await cache.cache_parsed_document(file_hash, data)
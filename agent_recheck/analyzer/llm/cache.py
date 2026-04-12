# -*- coding: utf-8 -*-
"""
LLM 缓存管理

提供结果缓存以减少 API 调用：
- 文档级缓存
- 段落级缓存
- 语义缓存（可选）
"""

import hashlib
import json
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    expires_at: Optional[float] = None
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "hit_count": self.hit_count,
        }


class LLMCache:
    """
    LLM 响应缓存
    
    功能：
    - 文档级缓存（基于文件路径+内容hash）
    - 段落级缓存（基于段落内容hash）
    - TTL 过期机制
    - 磁盘持久化
    """
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        default_ttl: int = 3600 * 24,  # 默认24小时
        max_size: int = 1000,
    ):
        """
        初始化缓存
        
        Args:
            cache_dir: 缓存目录，None 则使用内存缓存
            default_ttl: 默认过期时间（秒）
            max_size: 最大缓存条目数
        """
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._memory_cache: Dict[str, CacheEntry] = {}
        
        if cache_dir:
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_from_disk()
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在或过期返回 None
        """
        entry = self._get_entry(key)
        if entry is None:
            return None
        
        if entry.is_expired():
            self._remove(key)
            return None
        
        # 增加命中计数
        entry.hit_count += 1
        return entry.value
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 使用默认
        """
        # 检查大小限制
        if len(self._memory_cache) >= self.max_size:
            self._evict_oldest()
        
        expires_at = None
        if ttl is None:
            ttl = self.default_ttl
        if ttl > 0:
            expires_at = time.time() + ttl
        
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            expires_at=expires_at,
        )
        
        self._memory_cache[key] = entry
        
        # 持久化到磁盘
        if self.cache_dir:
            self._save_to_disk(key, entry)
    
    def delete(self, key: str) -> None:
        """删除缓存"""
        self._remove(key)
        
        if self.cache_dir:
            cache_file = self.cache_dir / f"{self._hash_key(key)}.json"
            if cache_file.exists():
                cache_file.unlink()
    
    def clear(self) -> None:
        """清空所有缓存"""
        self._memory_cache.clear()
        
        if self.cache_dir:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = len(self._memory_cache)
        expired = sum(1 for e in self._memory_cache.values() if e.is_expired())
        total_hits = sum(e.hit_count for e in self._memory_cache.values())
        
        return {
            "total_entries": total,
            "expired_entries": expired,
            "active_entries": total - expired,
            "total_hits": total_hits,
            "hit_rate": total_hits / total if total > 0 else 0,
        }
    
    def _get_entry(self, key: str) -> Optional[CacheEntry]:
        """获取缓存条目"""
        return self._memory_cache.get(key)
    
    def _remove(self, key: str) -> None:
        """移除缓存条目"""
        self._memory_cache.pop(key, None)
    
    def _evict_oldest(self) -> None:
        """驱逐最老的条目"""
        if not self._memory_cache:
            return
        
        # 找到最老的条目
        oldest_key = min(
            self._memory_cache.keys(),
            key=lambda k: self._memory_cache[k].created_at
        )
        self._remove(oldest_key)
    
    def _hash_key(self, key: str) -> str:
        """计算键的哈希"""
        return hashlib.md5(key.encode()).hexdigest()
    
    def _load_from_disk(self) -> None:
        """从磁盘加载缓存"""
        if not self.cache_dir:
            return
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    entry = CacheEntry(**data)
                    
                    # 检查是否过期
                    if not entry.is_expired():
                        self._memory_cache[entry.key] = entry
            except Exception:
                continue
    
    def _save_to_disk(self, key: str, entry: CacheEntry) -> None:
        """保存缓存到磁盘"""
        if not self.cache_dir:
            return
        
        cache_file = self.cache_dir / f"{self._hash_key(key)}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(entry.to_dict(), f, ensure_ascii=False)
        except Exception:
            pass


class DocumentCache:
    """
    文档级缓存
    
    缓存整个文档的分析结果
    """
    
    def __init__(self, llm_cache: LLMCache):
        self.cache = llm_cache
        self.prefix = "doc:"
    
    def get_document_result(self, file_path: str, file_hash: str) -> Optional[List]:
        """获取文档分析结果"""
        key = self._make_key(file_path, file_hash)
        return self.cache.get(key)
    
    def set_document_result(
        self,
        file_path: str,
        file_hash: str,
        result: List,
        ttl: Optional[int] = None,
    ) -> None:
        """设置文档分析结果"""
        key = self._make_key(file_path, file_hash)
        self.cache.set(key, result, ttl)
    
    def _make_key(self, file_path: str, file_hash: str) -> str:
        """生成缓存键"""
        return f"{self.prefix}{file_path}:{file_hash}"


class ParagraphCache:
    """
    段落级缓存
    
    缓存单个段落的分析结果
    """
    
    def __init__(self, llm_cache: LLMCache):
        self.cache = llm_cache
        self.prefix = "para:"
    
    def get_paragraph_result(
        self,
        paragraph_hash: str,
        analysis_type: str,
    ) -> Optional[Dict]:
        """获取段落分析结果"""
        key = self._make_key(paragraph_hash, analysis_type)
        return self.cache.get(key)
    
    def set_paragraph_result(
        self,
        paragraph_hash: str,
        analysis_type: str,
        result: Dict,
        ttl: Optional[int] = None,
    ) -> None:
        """设置段落分析结果"""
        key = self._make_key(paragraph_hash, analysis_type)
        self.cache.set(key, result, ttl)
    
    def _make_key(self, paragraph_hash: str, analysis_type: str) -> str:
        """生成缓存键"""
        return f"{self.prefix}{analysis_type}:{paragraph_hash}"


def compute_file_hash(file_path: str) -> str:
    """计算文件内容哈希"""
    import hashlib
    
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    
    return hasher.hexdigest()


def compute_text_hash(text: str) -> str:
    """计算文本哈希"""
    return hashlib.md5(text.encode()).hexdigest()


# 导出
__all__ = [
    'LLMCache',
    'DocumentCache',
    'ParagraphCache',
    'CacheEntry',
    'compute_file_hash',
    'compute_text_hash',
]

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知识库构建脚本
从 docs 目录中的 Markdown 文档生成向量知识库
"""

import sys
import logging
from pathlib import Path
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from knowledge_base import VectorKnowledgeBase

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """主函数：构建知识库"""
    
    print("=" * 60)
    print("🚀 开始构建向量知识库")
    print("=" * 60)
    
    # 检查 docs 目录是否存在（当前文件已在 docs 目录内）
    docs_dir = Path(".")
    if not docs_dir.exists():
        logger.error(f"❌ 当前目录不存在: {docs_dir.absolute()}")
        sys.exit(1)
    
    # 统计文档数量
    md_files = list(docs_dir.rglob("*.md"))
    logger.info(f"📁 找到 {len(md_files)} 个 Markdown 文件")
    
    if len(md_files) == 0:
        logger.warning("⚠️  docs 目录中没有找到 .md 文件")
        return
    
    # 列出所有文件
    print("\n📄 将要处理的文件:")
    for i, file in enumerate(md_files, 1):
        print(f"  {i}. {file.relative_to(docs_dir)}")
    
    print("\n" + "=" * 60)
    
    try:
        # 初始化知识库
        logger.info("🔧 初始化向量知识库...")
        kb = VectorKnowledgeBase(
            docs_dir=".",
            db_path="../chroma_db",
            collection_name="docs"
        )
        
        # 构建知识库
        logger.info("🔨 开始构建索引...")
        kb.build(chunk_size=500)
        
        # 获取统计信息
        stats = kb.get_stats()
        
        print("\n" + "=" * 60)
        print("✅ 知识库构建完成！")
        print("=" * 60)
        print(f"📊 统计信息:")
        print(f"  - 总文档片段: {stats['total_documents']}")
        print(f"  - 集合名称: {stats['collection_name']}")
        print(f"  - 存储路径: ./chroma_db")
        print("=" * 60)
        
        # 测试搜索功能
        print("\n🔍 测试搜索功能...")
        test_search(kb)
        
    except Exception as e:
        logger.error(f"❌ 构建知识库失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def test_search(kb: VectorKnowledgeBase):
    """测试搜索功能"""
    
    test_queries = [
        "如何点击UI元素",
        "怎么获取设备信息",
        "性能监控"
    ]
    
    for query in test_queries:
        print(f"\n  查询: '{query}'")
        try:
            results = kb.search(query, top_k=2)
            
            if results:
                for i, doc in enumerate(results, 1):
                    print(f"    [{i}] 相似度: {doc['score']:.2f} | {doc['title']}")
            else:
                print("    未找到相关结果")
                
        except Exception as e:
            print(f"    搜索失败: {str(e)}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from pathlib import Path
from typing import List, Dict
import hashlib

# ============ 1. 向量知识库类 ============
class VectorKnowledgeBase:
    """基于向量数据库的知识库"""
    
    def __init__(
        self, 
        docs_dir: str = "./docs",
        db_path: str = "./chroma_db",
        collection_name: str = "docs"
    ):
        self.docs_dir = Path(docs_dir)
        
        # 初始化Embedding模型（使用中文模型）
        print("加载Embedding模型...")
        
        # 尝试多种加载方式
        try:
            # 方案1: 使用镜像站并增加超时时间
            import os
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
            # 增加超时时间到30秒
            from sentence_transformers import util
            util.http_get = lambda url, *args, **kwargs: util.http_get(url, *args, **kwargs, timeout=30)
            
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            print("✅ 模型加载成功（使用镜像站）")
        except Exception as e:
            print(f"从HuggingFace加载失败: {e}")
            print("尝试使用本地缓存...")
            try:
                # 方案2: 使用本地缓存（如果之前下载过）
                self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', local_files_only=True)
                print("✅ 模型加载成功（使用本地缓存）")
            except Exception as e2:
                print(f"本地缓存也不存在: {e2}")
                print("使用轻量级替代模型...")
                # 方案3: 使用更小的模型作为后备
                try:
                    self.model = SentenceTransformer('all-MiniLM-L6-v2', local_files_only=True)
                    print("✅ 模型加载成功（使用轻量级模型）")
                except:
                    print("⚠️  无法加载任何Embedding模型，使用简单文本匹配")
                    # 方案4: 使用简单的文本匹配作为最后手段
                    self.model = None
        
        # 初始化Chroma客户端
        self.client = chromadb.PersistentClient(path=db_path)
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )
    
    def build(self, chunk_size: int = 500):
        """构建知识库"""
        print("开始构建向量知识库...")
        
        documents = []
        metadatas = []
        ids = []
        
        # 1. 读取并切片文档
        for file_path in self.docs_dir.rglob("*.md"):
            print(f"处理: {file_path.name}")
            content = file_path.read_text(encoding='utf-8')
            
            # 按标题切片
            sections = self._split_by_headers(content, str(file_path))
            
            for section_idx, section in enumerate(sections):
                # 生成唯一ID（包含文件名、标题和索引）
                doc_id = hashlib.md5(
                    (section['source'] + section['title'] + str(section_idx)).encode()
                ).hexdigest()
                
                documents.append(section['content'])
                metadatas.append({
                    'source': section['source'],
                    'title': section['title']
                })
                ids.append(doc_id)
        
        # 2. 生成向量并存储（批量处理）
        batch_size = 32
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            # 生成Embedding
            embeddings = self.model.encode(batch_docs).tolist()
            
            # 存入Chroma
            self.collection.add(
                documents=batch_docs,
                metadatas=batch_meta,
                embeddings=embeddings,
                ids=batch_ids
            )
            
            print(f"已处理 {i+len(batch_docs)}/{len(documents)} 个片段")
        
        print(f"✅ 知识库构建完成：{len(documents)} 个文档片段")
    
    def _split_by_headers(self, content: str, source: str) -> List[Dict]:
        """按标题切片（同上）"""
        sections = []
        lines = content.split('\n')
        current_section = {"title": "", "content": "", "source": source}
        
        for line in lines:
            if line.startswith('#'):
                if current_section['content'].strip():
                    sections.append(current_section)
                current_section = {
                    "title": line.strip('#').strip(),
                    "content": line + '\n',
                    "source": source
                }
            else:
                current_section['content'] += line + '\n'
        
        if current_section['content'].strip():
            sections.append(current_section)
        
        return sections
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """语义搜索"""
        if self.model is None:
            # 如果没有模型，使用简单的文本匹配
            return self._simple_text_search(query, top_k)
        
        try:
            # 1. 查询向量化
            query_embedding = self.model.encode([query]).tolist()
            
            # 2. 向量检索
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )
            
            # 3. 格式化结果
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'content': results['documents'][0][i],
                    'source': results['metadatas'][0][i]['source'],
                    'title': results['metadatas'][0][i]['title'],
                    'score': 1 - results['distances'][0][i]  # 转换为相似度
                })
            
            return formatted_results
        except Exception as e:
            print(f"向量搜索失败: {e}，使用文本搜索")
            return self._simple_text_search(query, top_k)
    
    def _simple_text_search(self, query: str, top_k: int = 3) -> List[Dict]:
        """简单的文本搜索（后备方案）"""
        # 获取所有文档
        all_docs = self.collection.get(include=['documents', 'metadatas'])
        
        if not all_docs['documents']:
            return []
        
        # 简单的关键词匹配
        query_words = set(query.lower().split())
        scored_docs = []
        
        for i, doc_content in enumerate(all_docs['documents']):
            doc_words = set(doc_content.lower().split())
            
            # 计算简单的匹配分数
            common_words = query_words.intersection(doc_words)
            score = len(common_words) / len(query_words) if query_words else 0
            
            scored_docs.append({
                'content': doc_content,
                'source': all_docs['metadatas'][i]['source'],
                'title': all_docs['metadatas'][i]['title'],
                'score': score
            })
        
        # 按分数排序并返回前top_k个
        scored_docs.sort(key=lambda x: x['score'], reverse=True)
        return scored_docs[:top_k]
    
    def get_stats(self) -> Dict:
        """获取知识库统计信息"""
        count = self.collection.count()
        return {
            'total_documents': count,
            'collection_name': self.collection.name
        }


# ============ 2. 使用示例 ============

# 2.1 构建知识库（只需运行一次）
if __name__ == "__main__":
    kb = VectorKnowledgeBase(
        docs_dir="./docs",
        db_path="./chroma_db"
    )
    
    # 构建索引
    kb.build()
    
    # 2.2 测试搜索
    print("\n" + "="*50)
    print("测试搜索功能")
    print("="*50)
    
    test_queries = [
        "如何点击UI元素",
        "怎么获取CPU使用率",
        "测试结果怎么上报"
    ]
    
    for query in test_queries:
        print(f"\n查询: {query}")
        results = kb.search(query, top_k=2)
        
        for i, doc in enumerate(results, 1):
            print(f"\n  结果 {i} (相似度: {doc['score']:.2f}):")
            print(f"  来源: {doc['source']}")
            print(f"  标题: {doc['title']}")
            print(f"  内容: {doc['content'][:150]}...")
    
    # 2.3 查看统计
    print("\n" + "="*50)
    stats = kb.get_stats()
    print(f"知识库统计: {stats}")

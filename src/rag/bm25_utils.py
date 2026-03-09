import jieba

def jieba_preprocess(text: str) -> list:
    """适用于中英文混合的 BM25 分词器"""
    # 转换为小写并使用 jieba 搜索引擎模式分词
    return jieba.lcut_for_search(text.lower())

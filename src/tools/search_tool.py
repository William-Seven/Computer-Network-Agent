from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.tools import tool

@tool
def internet_search(query: str) -> str:
    """
    当你需要获取最新的互联网信息，或者本地资料中没有相关答案（如超纲的前沿技术、外部工具的最新用法）时，必须使用此工具进行联网搜索。
    """
    print(f"🔍 [联网搜索] 正在自动搜索: {query}")
    try:
        search = DuckDuckGoSearchResults()
        return search.run(query)
    except Exception as e:
        print(f"⚠️ 搜索失败: {e}")
        return f"互联网搜索发生错误: {str(e)}"

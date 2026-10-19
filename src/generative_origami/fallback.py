from __future__ import annotations
from urllib.parse import quote_plus

def fallback_links(query: str) -> list[dict[str,str]]:
    q=quote_plus((query or "")+" 折纸 教程")
    return [
        {"name":"Bing","url":f"https://www.bing.com/search?q={q}","type":"WEB_SEARCH"},
        {"name":"Bilibili","url":f"https://search.bilibili.com/all?keyword={q}","type":"VIDEO_SEARCH"},
        {"name":"YouTube","url":f"https://www.youtube.com/results?search_query={q}","type":"VIDEO_SEARCH"},
    ]
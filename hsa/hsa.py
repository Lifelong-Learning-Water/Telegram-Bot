import requests
import time

# 配置信息
API_BASE_URL = "https://api.pearktrue.cn/api/dailyhot/"
PLATFROMS = [
    "哔哩哔哩", "百度", "知乎", "百度贴吧", "少数派", "IT之家",
    "澎湃新闻", "今日头条", "微博热搜", "36氪", "稀土掘金", "腾讯新闻"
]

def fetch_hot_data(platform):
    """获取指定平台的热搜数据"""
    url = f"{API_BASE_URL}?title={platform}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 200:
            print(data)
            return data.get("data", [])
        else:
            print(f"警告：{platform} API返回错误：{data.get('message')}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"错误：请求{platform}时发生异常：{str(e)}")
        return []

def format_hot_data(data_list):
    """格式化数据为可读文本"""
    formatted = []
    for item in data_list:
        title = item.get("title", "无标题")
        link = item.get("link", "#")
        hot = item.get("hot", "无热度")
        formatted.append(f"- [{title}]({link}) (热度: {hot})")
    return "\n".join(formatted)

def main():
    result = []
    for platform in PLATFROMS:
        print(f"正在获取：{platform}")
        data = fetch_hot_data(platform)
        if data:
            formatted = format_hot_data(data)
            result.append(f"**{platform} 热搜榜单**\n{formatted}\n\n")
        time.sleep(1)  # 避免请求过快
        
    print("=== 整合后的热搜数据 ===")
    print("\n".join(result))

if __name__ == "__main__":
    main()
import requests
import time

# 配置信息
API_BASE_URL = "https://api.pearktrue.cn/api/dailyhot/"
PLATFROMS = [
    ["百度", "url"], ["知乎", "url"], ["百度贴吧", "url"], ["少数派", "url"], ["IT之家", "url"],
    ["澎湃新闻", "url"], ["今日头条", "url"], ["36氪", "url"], ["稀土掘金", "mobileUrl"], ["腾讯新闻", "url"]
]

def fetch_hot_data(platform):
    """获取指定平台的热搜数据"""
    url = f"{API_BASE_URL}?title={platform}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 200:
            return data.get("data", [])
        else:
            print(f"警告：{platform} API返回错误：{data.get('message')}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"错误：请求{platform}时发生异常：{str(e)}")
        return []

def format_hot_data(data_list, url_key):
    """格式化数据为可读文本"""
    formatted = []
    for item in data_list:
        title = item.get("title", "无标题")
        link = item.get(url_key, "#")
        hot = item.get("hot", "无热度")
        formatted.append(f"- [{title}]({link}) (热度: {hot})")
    return "\n".join(formatted)

def main():
    result = []
    for platform in PLATFROMS:
        print(f"正在获取：{platform[0]}")
        data = fetch_hot_data(platform[0])
        if data:
            formatted = format_hot_data(data, platform[1])
            result.append(f"**{platform} 热搜榜单**\n{formatted}\n\n")
        time.sleep(1)  # 避免请求过快
        
    print("=== 整合后的热搜数据 ===")
    print("\n".join(result))

if __name__ == "__main__":
    main()
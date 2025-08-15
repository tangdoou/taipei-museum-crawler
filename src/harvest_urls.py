import requests
import json
import time
from bs4 import BeautifulSoup


def harvest_all_urls(target_category="繪畫", page_size=30, output_file="output/urls.txt"):
    """
    采集指定分类下所有文物详情页的URL。
    """
    base_url = "https://digitalarchive.npm.gov.tw"
    search_url = f"{base_url}/opendata/Pub/Search"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'Content-Type': 'application/json;charset=UTF-8',
    }

    all_urls = []

    # 使用一个临时的Session来获取列表
    with requests.Session() as session:
        # 先访问一次，获取总页数
        print("正在获取总页数信息...")
        payload_for_page1 = {
            "RegisterType": target_category, "PageInfo": {"PageIndex": 1, "PageSize": page_size}
        }
        try:
            response = session.post(search_url, headers=headers, data=json.dumps(payload_for_page1))
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            total_pages_tag = soup.find('span', id='total-pageCount')
            if not total_pages_tag:
                print("错误：未能找到总页数。")
                return
            total_pages = int(total_pages_tag.text)
            print(f"目标分类【{target_category}】共有 {total_pages} 页。")
        except Exception as e:
            print(f"获取总页数失败: {e}")
            return

        # 遍历所有页码
        for page_num in range(1, total_pages + 1):
            print(f"正在采集第 {page_num} / {total_pages} 页的URL...")
            payload = {
                "RegisterType": target_category, "PageInfo": {"PageIndex": page_num, "PageSize": page_size}
            }
            try:
                response = session.post(search_url, headers=headers, data=json.dumps(payload))
                response.raise_for_status()
                list_page_html = response.text

                soup = BeautifulSoup(list_page_html, 'html.parser')
                detail_links = soup.find_all('a', class_='openblank')

                if not detail_links:
                    print(f"警告：第 {page_num} 页没有找到任何文物链接。")
                    continue

                for link_tag in detail_links:
                    relative_url = link_tag.get('href')
                    full_detail_url = f"{base_url}{relative_url}"
                    all_urls.append(full_detail_url)

                # 礼貌性等待
                time.sleep(1)

            except Exception as e:
                print(f"采集第 {page_num} 页时发生错误: {e}")
                time.sleep(5)

    # 将所有URL写入文件
    with open(output_file, "w", encoding="utf-8") as f:
        for url in all_urls:
            f.write(url + "\n")

    print(f"\n采集完成！共获取 {len(all_urls)} 个URL，已保存至 {output_file}")


if __name__ == '__main__':
    harvest_all_urls()
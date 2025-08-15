import requests
import os
import re
import json
import csv
from bs4 import BeautifulSoup
from tqdm import tqdm
import time


# --- 更健壮的解析函数 (保持不变) ---
def parse_key_value_table(table_tag):
    data = {}
    if not table_tag: return data
    for row in table_tag.find_all('tr'):
        key_cell = row.find('th') if row.find('th') else row.find('td')
        value_cell = row.find('td').find_next_sibling('td') if key_cell and key_cell.name == 'td' else row.find('td')
        if key_cell and value_cell:
            key = key_cell.get_text(strip=True)
            value = value_cell.get_text(separator='\n', strip=True)
            if key in data:
                if isinstance(data[key], list):
                    data[key].append(value)
                else:
                    data[key] = [data[key], value]
            else:
                data[key] = value
    return data


def parse_header_row_table(table_tag):
    data = []
    if not table_tag: return data
    headers = [th.get_text(strip=True) for th in table_tag.find_all('th')]
    if not headers: return data
    for row in table_tag.find_all('tr'):
        cells = row.find_all('td')
        if cells and len(cells) == len(headers):
            row_data = {headers[i]: cell.get_text(separator='\n', strip=True) for i, cell in enumerate(cells)}
            data.append(row_data)
    return data


def parse_inscription_table(table_tag):
    data = []
    if not table_tag: return data
    headers = [th.get_text(strip=True) for th in table_tag.find('tr').find_all('th')]
    if not headers: return []
    all_rows = table_tag.find('tbody').find_all('tr') if table_tag.find('tbody') else table_tag.find_all('tr')
    i = 0
    while i < len(all_rows):
        row = all_rows[i]
        if row.find('th') or row.find_parent('table') != table_tag:
            i += 1
            continue
        cells = row.find_all('td', recursive=False)
        if len(cells) == len(headers):
            row_data = {header: cell.get_text(separator='\n', strip=True) for header, cell in zip(headers, cells)}
            if i + 1 < len(all_rows):
                next_row = all_rows[i + 1]
                if next_row.find('table', class_='table-details2'):
                    seals_table = next_row.find('table', class_='table-details2')
                    seals = parse_header_row_table(seals_table)
                    row_data['印記資料'] = seals
                    i += 1
            data.append(row_data)
        i += 1
    return data


def parse_conservation_info(div_tag):
    data = {}
    if not div_tag: return data
    info_div = div_tag.find('div', class_='nav-info')
    if info_div: data['說明'] = info_div.get_text(strip=True)
    links = [{'文本': a_tag.get_text(strip=True), 'onclick': a_tag.get('onclick')} for a_tag in
             div_tag.find_all('a', class_='btn-project2')]
    data['相關連結'] = links
    return data


# --- 主抓取函数 (已修复解析错误) ---
def scrape_artifact_metadata(url, headers):
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        item_id_match = re.search(r"GetJson\?cid=(\d+)", response.text)
        unique_id = item_id_match.group(1) if item_id_match else url.split('Detail/')[1].split('?')[0]

        artifact_data = {
            "UniqueID": unique_id,
            "URL": url,
            "文物名称": soup.find('div', class_='details-title').get_text(strip=True) if soup.find('div',
                                                                                                   class_='details-title') else "N/A"
        }

        sections_to_scrape = {
            "基本資料": ("details-1", parse_key_value_table),
            "典藏尺寸": ("details-2", parse_header_row_table),
            "質地": ("details-3", parse_header_row_table),
            "題跋資料": ("details-4", parse_inscription_table),
            "印記資料": ("details-5", parse_header_row_table),
            "主題": ("details-6", parse_header_row_table),
            "技法": ("details-7", parse_header_row_table),
            "參考資料": ("details-8", parse_key_value_table),
            "保存維護": ("details-9", parse_conservation_info)
        }

        for section_name, (div_id, parse_func) in sections_to_scrape.items():
            section_div = soup.find('div', id=div_id)
            # --- 关键修复：在操作前，先判断section_div是否存在 ---
            if section_div:
                target_tag = section_div.find('table') if "table" in parse_func.__name__ else section_div
                artifact_data[section_name] = parse_func(target_tag)
            else:
                artifact_data[section_name] = {}  # 如果整个部分不存在，则记录为空字典
        return artifact_data
    except Exception as e:
        # 使用tqdm.write打印，避免打乱进度条
        tqdm.write(f"处理URL {url} 时发生错误: {e}")
        return None


if __name__ == '__main__':
    URL_FILE = "output/urls.txt"
    JSON_OUTPUT_DIR = "output/metadata_json"
    CSV_OUTPUT_FILE = "output/metadata.csv"

    os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(URL_FILE):
        print(f"错误: 未找到URL列表文件 '{URL_FILE}'。")
    else:
        with open(URL_FILE, "r", encoding="utf-8") as f:
            urls_to_scrape = [line.strip() for line in f if line.strip()]

        print(f"从 '{URL_FILE}' 文件中加载了 {len(urls_to_scrape)} 个URL。")

        # ==================== 在这里配置您的分布式任务 ====================
        # 您可以在不同的电脑上设置不同的范围，来实现分布式爬取
        # 电脑1: START_INDEX = 1, END_INDEX = 5000
        # 电脑2: START_INDEX = 5001, END_INDEX = 10000
        # 电脑3: START_INDEX = 10001, END_INDEX = None
        START_INDEX = 1
        END_INDEX = 100  # 先用一个小范围测试，确保一切正常
        # ==========================================================

        urls_to_process = urls_to_scrape[START_INDEX - 1:END_INDEX] if END_INDEX is not None else urls_to_scrape[
                                                                                                  START_INDEX - 1:]
        print(
            f"本次任务将处理第 {START_INDEX} 到 {END_INDEX if END_INDEX is not None else len(urls_to_scrape)} 个URL，共计 {len(urls_to_process)} 个。")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'}
        CSV_HEADERS = ["UniqueID", "URL", "文物名称", "基本資料", "典藏尺寸", "質地", "題跋資料", "印記資料", "主題",
                       "技法", "參考資料", "保存維護"]

        with open(CSV_OUTPUT_FILE, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            if f.tell() == 0: writer.writeheader()

            # --- 回归到简单的单线程循环 ---
            for url in tqdm(urls_to_process, desc="元数据采集中"):
                item_id_match = re.search(r'Detail/(\d+)', url)
                if item_id_match:
                    unique_id = item_id_match.group(1)
                    json_filepath = os.path.join(JSON_OUTPUT_DIR, f"artifact_{unique_id}.json")
                    if os.path.exists(json_filepath):
                        # tqdm.write(f"JSON文件已存在，跳过: {json_filepath}")
                        continue

                metadata = scrape_artifact_metadata(url, headers)
                if metadata:
                    json_filepath = os.path.join(JSON_OUTPUT_DIR, f"artifact_{metadata['UniqueID']}.json")
                    with open(json_filepath, "w", encoding="utf-8") as json_f:
                        json.dump(metadata, json_f, indent=4, ensure_ascii=False)

                    flat_data = {}
                    for key in CSV_HEADERS:
                        value = metadata.get(key, "")
                        if isinstance(value, (dict, list)) and value:
                            flat_data[key] = json.dumps(value, ensure_ascii=False)
                        elif not value:
                            flat_data[key] = ""
                        else:
                            flat_data[key] = value
                    writer.writerow(flat_data)

                time.sleep(1)  # 单线程下，稍短的延时即可

        print(f"\n任务完成！元数据已保存至CSV文件 '{CSV_OUTPUT_FILE}' 及JSON文件夹 '{JSON_OUTPUT_DIR}'。")
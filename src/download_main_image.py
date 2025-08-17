import requests
import os
import re
import time
import io
import json
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract
from tqdm import tqdm

# --- 全局配置 ---
MAX_RETRIES = 10
REQUEST_TIMEOUT = 60
PROXIES = {'http': None, 'https': None}


# --- 核心功能函数 ---
def solve_captcha(session, captcha_url, headers):
    try:
        print("  正在下载验证码...")
        captcha_response = session.get(captcha_url, headers=headers, timeout=REQUEST_TIMEOUT, proxies=PROXIES)
        captcha_response.raise_for_status()
        captcha_image = Image.open(io.BytesIO(captcha_response.content))
        config = r'--psm 7 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        ocr_result = pytesseract.image_to_string(captcha_image, config=config).strip()
        print(f"  OCR自动识别结果: '{ocr_result}'")
        return ocr_result
    except Exception as e:
        print(f"  下载或识别验证码时出错: {e}")
        return ""


def download_main_image(session, item_id, image_info, output_filepath, headers, detail_page_url, log_file_path, index):
    print(f"\n--- 正在下载主图: {os.path.basename(output_filepath)} ---")
    base_url = "https://digitalarchive.npm.gov.tw"
    for attempt in range(MAX_RETRIES):
        print(f"第 {attempt + 1} / {MAX_RETRIES} 次尝试...")
        captcha_solution = solve_captcha(session, f"{base_url}/opendata/Image/GetCaptchaImageFor600", headers)
        if not captcha_solution:
            print("  OCR识别为空，直接进入下一次尝试...")
            time.sleep(2)
            continue

        payload = {'ImageId': image_info['id'], 'Dep': 'U', 'RandomCode': image_info['code'], 'ItemId': item_id,
                   'CaptchaCode': captcha_solution}
        post_headers = headers.copy()
        post_headers['Referer'] = detail_page_url
        print(f"  提交验证信息...")
        try:
            validation_response = session.post(f"{base_url}/opendata/Image/DownloadDialog600", data=payload,
                                               headers=post_headers, timeout=REQUEST_TIMEOUT, proxies=PROXIES)
            validation_data = validation_response.json()
        except requests.exceptions.RequestException as e:
            print(f"  提交验证时网络错误: {e}。即将重试...")
            time.sleep(2)
            continue

        if validation_data.get("result"):
            print("  验证成功！准备下载...")
            final_params = validation_data
            img_response = session.get(f"{base_url}/opendata/Image/Download600",
                                       params={"imageId": final_params['ImageId'], "dept": final_params['Dep'],
                                               "cid": final_params['Cid'], "capchaCode": final_params['Captcha'],
                                               "code": final_params['ImageCode']}, headers=headers,
                                       timeout=REQUEST_TIMEOUT, proxies=PROXIES)
            img_response.raise_for_status()
            with open(output_filepath, 'wb') as f:
                f.write(img_response.content)
            print(f"主图成功下载至: {output_filepath}")
            return True
        else:
            print(f"  验证失败 (服务器信息: {validation_data.get('message')})，即将重试...")
            time.sleep(2)

    print(f"--- 主图 {os.path.basename(output_filepath)} 尝试{MAX_RETRIES}次后仍然失败 ---")
    with open(log_file_path, "a", encoding="utf-8") as f:
        log_entry = {
            "index": index,
            "detail_page_url": detail_page_url, 
            "image_info": image_info,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    return False


def run_scraper_for_url(page_url, headers, project_root, index):
    """对单个详情页抓取主图。"""
    LOG_FILE_PATH = os.path.join(project_root, 'output', 'failed_main_images.log')
    MAIN_IMAGE_DIR = os.path.join(project_root, 'output', 'main_images')
    os.makedirs(MAIN_IMAGE_DIR, exist_ok=True)

    with requests.Session() as session:
        try:
            response = session.get(page_url, headers=headers, timeout=REQUEST_TIMEOUT, proxies=PROXIES)
            response.raise_for_status()
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')

            item_id_match = re.search(r"GetJson\?cid=(\d+)", html_content)
            item_id = item_id_match.group(1) if item_id_match else None
            gallery_div = soup.find('div', id='gallery')
            image_tags = gallery_div.find_all('img') if gallery_div else []

            if not (item_id and image_tags):
                tqdm.write(f"错误(Index: {index})：在详情页 {page_url} 未找到文物ID或图片列表。")
                return

            main_image_info = {
                'name': image_tags[0].get('data-image-name'), 
                'id': image_tags[0].get('data-image-id'), 
                'code': image_tags[0].get('data-image-code')
            }

            page_title = soup.title.string.strip().replace(' ', '_').replace('　', '_')
            safe_page_title = re.sub(r'[\\/:*?"<>|]', '_', page_title)
            # 使用 序号_标题.jpg 格式命名
            output_filename = f"{index:05d}_{safe_page_title}.jpg"
            output_filepath = os.path.join(MAIN_IMAGE_DIR, output_filename)

            if os.path.exists(output_filepath):
                tqdm.write(f"主图 '{os.path.basename(output_filepath)}' 已存在，跳过。")
                return

            success = download_main_image(session, item_id, main_image_info, output_filepath, headers, page_url, LOG_FILE_PATH, index)
            if not success:
                tqdm.write(f"警告(Index: {index})：主图 {main_image_info['name']} 未能成功下载，详情已记录到 {LOG_FILE_PATH}")

        except Exception as e:
            tqdm.write(f"处理URL (Index: {index}, URL: {page_url}) 时发生严重错误: {e}")


if __name__ == '__main__':
    # --- 动态路径处理 ---
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
    URL_FILE = os.path.join(PROJECT_ROOT, 'output', 'urls.txt')
    LOG_FILE = os.path.join(PROJECT_ROOT, 'output', 'failed_main_images.log')
    # ---

    if not os.path.exists(URL_FILE):
        print(f"错误: 未找到URL列表文件 '{URL_FILE}'。请先运行 'src/harvest_urls.py'。")
    else:
        with open(URL_FILE, "r", encoding="utf-8") as f:
            urls_to_scrape = [line.strip() for line in f if line.strip()]
        print(f"从 '{URL_FILE}' 文件中加载了 {len(urls_to_scrape)} 个URL。")

        START_INDEX = 1
        END_INDEX = 10

        # 根据起始索引号切片
        urls_to_process = urls_to_scrape[START_INDEX - 1:END_INDEX] if END_INDEX is not None else urls_to_scrape[START_INDEX - 1:]
        print(f"本次任务将处理第 {START_INDEX} 到 {END_INDEX if END_INDEX is not None else len(urls_to_scrape)} 个URL，共计 {len(urls_to_process)} 个。")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'}

        # 使用 enumerate 来获取每个URL的索引 (从START_INDEX开始)
        for index, url in enumerate(tqdm(urls_to_process, desc="主图下载进度"), start=START_INDEX):
            try:
                run_scraper_for_url(url, headers, PROJECT_ROOT, index)
                tqdm.write(f"--- (Index: {index})单个文物主图处理完毕，休息3秒 ---")
                time.sleep(3)
            except Exception as e:
                tqdm.write(f"处理URL (Index: {index}, URL: {url}) 时发生顶级未知错误: {e}。将继续处理下一个URL。")
                time.sleep(5)

        print("\n本次指定的主图下载任务已全部完成！")
        if os.path.exists(LOG_FILE):
            print(f"\n警告：有部分主图下载失败，详情请查看 {LOG_FILE} 文件。")

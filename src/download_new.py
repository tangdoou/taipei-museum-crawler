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


# --- 核心功能函数 (这部分保持不变) ---
def solve_captcha(session, captcha_url, headers):
    # (此函数与上一版完全相同)
    try:
        # ...
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


def download_single_image(session, item_id, image_info, download_folder, headers, detail_page_url):
    # (此函数与上一版完全相同)
    print(f"\n--- 正在下载新图片: {image_info['name']} ---")
    # ...
    # (函数内部逻辑与上一版完全相同，此处省略以保持清爽)
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
            file_path = os.path.join(download_folder, f"{image_info['name']}.jpg")
            with open(file_path, 'wb') as f:
                f.write(img_response.content)
            print(f"图片成功下载至: {file_path}")
            return True
        else:
            print(f"  验证失败 (服务器信息: {validation_data.get('message')})，即将重试...")
            time.sleep(2)

    print(f"--- 图片 {image_info['name']} 尝试{MAX_RETRIES}次后仍然失败 ---")
    with open("output/failed_images.log", "a", encoding="utf-8") as f:
        log_entry = {"detail_page_url": detail_page_url, "image_info": image_info,
                     "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    return False


# --- 关键升级：run_scraper_for_url 函数 ---
def run_scraper_for_url(page_url, headers):
    """对单个详情页进行完整的图片抓取流程，采用精准断点续传。"""
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
                tqdm.write(f"错误：在详情页 {page_url} 未找到文物ID或图片列表。")
                return

            image_info_list = [
                {'name': tag.get('data-image-name'), 'id': tag.get('data-image-id'), 'code': tag.get('data-image-code')}
                for tag in image_tags]
            page_title = soup.title.string.strip().replace(' ', '_').replace('　', '_')
            download_folder = os.path.join("output/taipei_museum_artifacts", page_title)
            os.makedirs(download_folder, exist_ok=True)

            # ==================== 全新的“精准检查”逻辑 ====================
            # 1. 获取“应下载文件名”清单
            expected_filenames = {f"{info['name']}.jpg" for info in image_info_list}

            # 2. 获取本地文件夹中“已存在文件名”清单
            existing_filenames = set(os.listdir(download_folder))

            # 3. 计算出“待下载文件名”清单
            missing_files_info = []
            for info in image_info_list:
                if f"{info['name']}.jpg" not in existing_filenames:
                    missing_files_info.append(info)

            # 4. 根据清单决定行动
            if not missing_files_info:
                tqdm.write(f"文件夹 '{page_title}' 内容已完整，精准跳过。")
                return
            else:
                tqdm.write(
                    f"文件夹 '{page_title}' 检查完毕，发现 {len(missing_files_info)} / {len(expected_filenames)} 个文件需要下载。")
            # ==========================================================

            # 现在，我们只遍历那些需要下载的图片信息
            for i, single_image in enumerate(missing_files_info):
                success = download_single_image(session, item_id, single_image, download_folder, headers, page_url)
                if not success:
                    tqdm.write(f"警告：图片 {single_image['name']} 未能成功下载，详情已记录到output/failed_images.log")
                if i < len(missing_files_info) - 1:
                    time.sleep(1)
        except Exception as e:
            tqdm.write(f"处理详情页 {page_url} 时发生严重错误: {e}")


# --- 主程序入口 (保持不变) ---
if __name__ == '__main__':
    URL_FILE = "output/urls.txt"
    if not os.path.exists(URL_FILE):
        print(f"错误: 未找到URL列表文件 '{URL_FILE}'。请先运行 'harvest_urls.py'。")
    else:
        with open(URL_FILE, "r", encoding="utf-8") as f:
            urls_to_scrape = [line.strip() for line in f if line.strip()]
        print(f"从 '{URL_FILE}' 文件中加载了 {len(urls_to_scrape)} 个URL。")

        # 您可以在这里配置您的分布式任务
        START_INDEX = 43
        END_INDEX = 52

        urls_to_process = urls_to_scrape[START_INDEX - 1:END_INDEX] if END_INDEX is not None else urls_to_scrape[
                                                                                                  START_INDEX - 1:]
        print(
            f"本次任务将处理第 {START_INDEX} 到 {END_INDEX if END_INDEX is not None else len(urls_to_scrape)} 个URL，共计 {len(urls_to_process)} 个。")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'}

        for url in tqdm(urls_to_process, desc="下载总进度"):
            try:
                run_scraper_for_url(url, headers)
                tqdm.write("--- 单个文物处理完毕，休息3秒 ---")
                time.sleep(3)
            except Exception as e:
                tqdm.write(f"处理URL {url} 时发生顶级未知错误: {e}。将继续处理下一个URL。")
                time.sleep(5)

        print("\n本次指定的下载任务已全部完成！")
        if os.path.exists("output/failed_images.log"):
            print("\n警告：有部分图片下载失败，详情请查看 output/failed_images.log 文件。")
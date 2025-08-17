import os
import csv
import sys
from PIL import Image

def analyze_images(root_folder, output_csv):
    """
    Analyzes images in a root folder to extract resolution and file size.

    Args:
        root_folder (str): The path to the folder containing images.
        output_csv (str): The path to the output CSV file.
    """
    image_data = []
    # Supported image extensions
    supported_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')

    print(f"\n开始分析目录: {root_folder}")
    # Use a generator to count files to show progress
    all_files = list(os.walk(root_folder))
    total_files = sum(len(files) for _, _, files in all_files)
    processed_files = 0

    for subdir, _, files in all_files:
        for file in files:
            processed_files += 1
            print(f"\r正在处理: {processed_files}/{total_files}", end="")
            if file.lower().endswith(supported_extensions):
                file_path = os.path.join(subdir, file)
                try:
                    # Get file size
                    file_size_kb = round(os.path.getsize(file_path) / 1024, 2)

                    # Get image dimensions
                    with Image.open(file_path) as img:
                        width, height = img.size

                    # Get relative path for cleaner output
                    relative_path = os.path.relpath(file_path, root_folder)

                    image_data.append([relative_path, width, height, file_size_kb])

                except Exception as e:
                    print(f"\n无法处理 {file_path}: {e}")

    # Write data to CSV
    if image_data:
        # Sort data by folder, then filename
        image_data.sort(key=lambda x: os.path.dirname(x[0]))
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['File Path', 'Width (px)', 'Height (px)', 'Size (KB)'])
            writer.writerows(image_data)
        print(f"\n\n成功分析 {len(image_data)} 张图片。")
        print(f"结果已保存至: {output_csv}")
    else:
        print("\n在指定目录中未找到任何图片。")

if __name__ == '__main__':
    # Check if the user provided a directory path as a command-line argument
    if len(sys.argv) < 2:
        print("\n错误: 请提供要分析的图片目录路径。")
        print("用法: python src/analyze_images.py <图片目录路径>")
        print("例如: python src/analyze_images.py output/main_images")
        sys.exit(1)  # Exit the script if no directory is provided

    artifacts_directory = sys.argv[1]

    # --- 动态路径处理 ---
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
    # Create a descriptive name for the output CSV file based on the input directory
    dir_name = os.path.basename(os.path.normpath(artifacts_directory))
    output_file = os.path.join(PROJECT_ROOT, "output", f"analysis_{dir_name}.csv")
    # ---
    
    # The input directory path can be relative, so we don't force it to be absolute
    if not os.path.isdir(artifacts_directory):
        print(f"\n错误: 找不到指定的目录 '{artifacts_directory}'")
    else:
        analyze_images(artifacts_directory, output_file)

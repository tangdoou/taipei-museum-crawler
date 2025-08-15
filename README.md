# 台北故宫文物数据集爬虫

本项目是一个用于爬取台北故宫博物院开放数据平台（[Open Data](https://digitalarchive.npm.gov.tw/opendata/)）上文物信息的 Python 爬虫。它可以自动化地采集指定分类下的文物元数据、下载高清图片，并对图片进行基础分析。

## ✨ 主要功能

- **URL 采集**: 自动获取指定分类（如“绘画”）下所有文物的详情页链接。
- **元数据抓取**: 从每个文物详情页提取详细的元数据，并保存为独立的 JSON 文件和一份总的 CSV 文件。
- **图片下载**:
    - 自动处理并识别验证码（使用 Tesseract OCR）。
    - 支持断点续传，只下载尚未获取的图片。
    - 将每个文物的图片保存在以其标题命名的独立文件夹中。
- **图像分析**: 分析已下载的图片，提取分辨率和文件大小等信息，并生成 CSV 报告。
- **结构清晰**: 采用 `src` 和 `output` 目录分离代码与数据，方便管理。

## 📂 项目结构

项目文件经过整理，具有清晰的结构：

```
/
├── src/                      # 存放所有 Python 源代码
│   ├── harvest_urls.py       # 采集文物详情页 URL
│   ├── scrape_metadata.py    # 抓取元数据
│   ├── download_new.py       # 下载文物图片
│   └── analyze_images.py     # 分析图片信息
├── output/                     # 存放所有输出结果
│   ├── urls.txt              # 采集到的 URL 列表
│   ├── metadata.csv          # 所有文物的元数据表格
│   ├── image_analysis.csv    # 图片分析结果
│   ├── metadata_json/        # 每个文物的独立 JSON 元数据文件
│   └── taipei_museum_artifacts/ # 下载的文物图片
├── .gitignore                # Git 忽略规则
├── README.md                 # 项目说明文件
└── requirements.txt          # Python 依赖库
```

## 🚀 环境配置与安装

在运行此项目前，请确保您的系统满足以下要求。

### 1. 安装 Tesseract OCR

本项目的图片下载脚本需要使用 Tesseract OCR 引擎来识别验证码。请根据您的操作系统预先安装。

- **macOS**:
  ```bash
  brew install tesseract
  ```
- **Ubuntu/Debian**:
  ```bash
  sudo apt update
  sudo apt install tesseract-ocr
  ```
- **Windows**:
  可以从 [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) 下载安装程序。**请注意**：安装时请勾选 "Add Tesseract to system PATH" 选项，或手动将其安装路径添加到系统环境变量中。

安装完成后，请在终端或命令行中运行 `tesseract --version` 来验证是否安装成功。

### 2. 安装 Python 依赖

建议使用虚拟环境以避免包版本冲突。

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd 台北故宫文物数据集爬虫

# 2. (可选，但推荐) 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate  # 在 Windows 上使用 `venv\Scripts\activate`

# 3. 安装所需的 Python 库
pip install -r requirements.txt
```

## 📖 使用流程

请按照以下顺序执行脚本，以完成整个数据采集流程。

### 第 1 步：采集 URL

运行 `harvest_urls.py` 脚本，获取所有目标文物的详情页链接。默认采集“绘画”分类。

```bash
python src/harvest_urls.py
```

成功后，所有链接将保存在 `output/urls.txt` 文件中。

### 第 2 步：抓取元数据

使用上一步生成的 `urls.txt` 文件，抓取每个文物的详细元数据。

```bash
python src/scrape_metadata.py
```

元数据将以两种格式保存在 `output` 目录下：
- `output/metadata_json/`: 每个文物一个 JSON 文件。
- `output/metadata.csv`: 包含所有文物信息的单张 CSV 表格。

### 第 3 步：下载图片

此脚本将读取 `urls.txt`，访问每个详情页并下载所有相关的高清图片。

```bash
python src/download_new.py
```

图片会保存在 `output/taipei_museum_artifacts/` 目录下，每个文物一个子文件夹。脚本支持断点续传，如果中途中断，重新运行即可。

### 第 4 步：分析图片

对所有已下载的图片进行分析，提取基本信息。

```bash
python src/analyze_images.py
```

分析结果将保存在 `output/image_analysis.csv` 文件中。

## 📝 输出文件说明

- **`output/urls.txt`**: 文物详情页的 URL 列表，每行一个。
- **`output/metadata.csv`**: 所有文物元数据的集合，适合用 Excel 或 Pandas 进行分析。
- **`output/image_analysis.csv`**: 已下载图片的元数据，包括路径、宽度、高度和文件大小。
- **`output/metadata_json/`**: 包含每个文物详细元数据的 JSON 文件，文件名与文物 ID 对应。
- **`output/taipei_museum_artifacts/`**: 存放所有已下载图片的根目录，内部按文物名称分文件夹存放。
- **`output/failed_images.log`**: (如果出现下载失败) 记录下载失败的图片信息，方便排查。
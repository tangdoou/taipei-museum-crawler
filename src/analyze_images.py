import os
import csv
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

    for subdir, _, files in os.walk(root_folder):
        for file in files:
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
                    print(f"Processed: {relative_path}")

                except Exception as e:
                    print(f"Could not process {file_path}: {e}")

    # Write data to CSV
    if image_data:
        # Sort data by folder, then filename
        image_data.sort(key=lambda x: os.path.dirname(x[0]))
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['File Path', 'Width (px)', 'Height (px)', 'Size (KB)'])
            writer.writerows(image_data)
        print(f"\nSuccessfully analyzed {len(image_data)} images.")
        print(f"Results saved to {output_csv}")
    else:
        print("No images found in the specified directory.")

if __name__ == '__main__':
    # The directory where your artifact images are stored
    artifacts_directory = 'output/taipei_museum_artifacts'
    # The name for the output file
    output_file = 'output/image_analysis.csv'
    
    if not os.path.isdir(artifacts_directory):
        print(f"Error: Directory not found at '{artifacts_directory}'")
    else:
        analyze_images(artifacts_directory, output_file)

"""
Script tai cac dataset tu Roboflow va luu vao D:\ANH DATASET
"""

import os
import sys
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Cài đặt roboflow nếu chưa có
try:
    import roboflow
except ImportError:
    print("Đang cài đặt roboflow...")
    os.system(f"{sys.executable} -m pip install roboflow")
    from roboflow import Roboflow

from roboflow import Roboflow

# Thư mục lưu dataset
OUTPUT_DIR = Path("D:/ANH DATASET")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# API Key
API_KEY = "5ik3gd74DjOP3Hww02F4"

# Danh sách các dataset cần tải
DATASETS = [
    {
        "workspace": "damaged-building-slbtd",
        "project": "aerial-person-detection-cyxrn",
        "version": 1,
        "name": "damaged-building-aerial-person-v1",
        "description": "7k ảnh"
    },
    {
        "workspace": "aerial-person-detection",
        "project": "aerial-person-detection",
        "version": 3,
        "name": "aerial-person-detection-v3",
        "description": "7k ảnh"
    },
    {
        "workspace": "aerial-person-detection",
        "project": "aerial-person-detection",
        "version": 2,
        "name": "aerial-person-detection-v2",
        "description": "20k ảnh"
    },
    {
        "workspace": "aerial-person-detection",
        "project": "aerial-person-detection",
        "version": 1,
        "name": "aerial-person-detection-v1",
        "description": "7k ảnh"
    },
    {
        "workspace": "riccardo-kxtut",
        "project": "overhead-person-szky0",
        "version": 2,
        "name": "overhead-person-v2",
        "description": "4k2 ảnh"
    },
    {
        "workspace": "riccardo-kxtut",
        "project": "overhead-person-szky0",
        "version": 1,
        "name": "overhead-person-v1",
        "description": "4k1 ảnh"
    },
    {
        "workspace": "garbage-pu8hj",
        "project": "pedestrian-z78m0",
        "version": 1,
        "name": "pedestrian-v1",
        "description": "1.3k ảnh"
    },
    {
        "workspace": "dronedetect-an991",
        "project": "drone-person-detection-ald8g",
        "version": 4,
        "name": "drone-person-detection-v4",
        "description": "5k ảnh"
    },
    {
        "workspace": "pukyung-university",
        "project": "person-pfjle",
        "version": 2,
        "name": "person-pfjle-v2",
        "description": "4.6k ảnh"
    },
    {
        "workspace": "new-workspace-laz58",
        "project": "person-xfzsr",
        "version": 1,
        "name": "person-xfzsr-v1",
        "description": "1k ảnh"
    },
    {
        "workspace": "garage-2",
        "project": "person-n0f20",
        "version": 2,
        "name": "person-n0f20-v2",
        "description": "2k ảnh"
    },
]

def download_dataset(dataset_info):
    """Tải một dataset từ Roboflow"""
    workspace = dataset_info["workspace"]
    project_name = dataset_info["project"]
    version = dataset_info["version"]
    name = dataset_info["name"]
    description = dataset_info["description"]
    
    print(f"\n{'='*60}")
    print(f"Dang tai: {name} ({description})")
    print(f"Workspace: {workspace}")
    print(f"Project: {project_name}")
    print(f"Version: {version}")
    print(f"{'='*60}")
    
    try:
        # Ket noi Roboflow
        rf = Roboflow(api_key=API_KEY)
        
        # Lay project
        project = rf.workspace(workspace).project(project_name)
        
        # Lay version
        version_obj = project.version(version)
        
        # Tai dataset (format YOLOv5)
        print(f"Dang tai dataset...")
        dataset = version_obj.download("yolov5", location=str(OUTPUT_DIR / name))
        
        print(f"[OK] Hoan thanh: {name}")
        print(f"   Da luu vao: {OUTPUT_DIR / name}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Loi khi tai {name}: {str(e)}")
        return False

def main():
    print("="*60)
    print("SCRIPT TAI DATASET TU ROBOFLOW")
    print("="*60)
    print(f"Thu muc luu: {OUTPUT_DIR}")
    print(f"Tong so dataset: {len(DATASETS)}")
    print("="*60)
    
    # Đếm số dataset thành công/thất bại
    success_count = 0
    fail_count = 0
    
    # Tai tung dataset
    for i, dataset_info in enumerate(DATASETS, 1):
        print(f"\n[{i}/{len(DATASETS)}] Dang xu ly dataset {i}...")
        
        if download_dataset(dataset_info):
            success_count += 1
        else:
            fail_count += 1
    
    # Tong ket
    print("\n" + "="*60)
    print("TONG KET")
    print("="*60)
    print(f"[OK] Thanh cong: {success_count}/{len(DATASETS)}")
    print(f"[ERROR] That bai: {fail_count}/{len(DATASETS)}")
    print(f"Thu muc luu: {OUTPUT_DIR}")
    print("="*60)
    
    if fail_count > 0:
        print("\n[WARNING] Mot so dataset tai that bai. Vui long kiem tra lai.")
        return 1
    else:
        print("\n[SUCCESS] Tat ca dataset da duoc tai thanh cong!")
        return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[WARNING] Da dung boi nguoi dung (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Loi khong mong doi: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


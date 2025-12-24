"""
utils.py
錯誤處理、檔案讀寫輔助工具。
"""
import os
import json

def read_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def safe_remove(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass

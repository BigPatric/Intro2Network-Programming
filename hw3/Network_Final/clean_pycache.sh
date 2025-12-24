#!/bin/bash
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null
find . -type f -name "*.pyc" -delete
echo "已清除所有 __pycache__ 目錄與 .pyc 檔案"
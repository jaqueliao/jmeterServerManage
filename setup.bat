@echo off
:1
title jmeterManage安装
echo 开始安装python……
echo 请勾选add python to environment variables选项
python-3.8.3-amd64.exe
echo 开始安装依赖包……
pip install -r requirements.txt
echo 安装完成
pause
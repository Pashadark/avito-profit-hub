import os
import subprocess

# Убиваем процессы
subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], capture_output=True)
subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], capture_output=True)
subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], capture_output=True)

print("✅ Процессы завершены")
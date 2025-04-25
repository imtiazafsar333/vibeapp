import os
import webbrowser
import threading
import subprocess
import re


def open_browser(port):
    url = f"http://localhost:{port}"
    webbrowser.open_new(url)


# Start Streamlit and capture its output
def launch_streamlit():
    python_path = r"C:\Users\eGeeks Global\Downloads\vibeeeeeee\venv\Scripts\python.exe"
    command = [python_path, "-m", "streamlit", "run", "app.py", "--server.headless=true"]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    while True:
        line = process.stdout.readline()
        if not line:
            break
        print(line.strip())
        match = re.search(r"http://localhost:(\d+)", line)
        if match:
            port = match.group(1)
            threading.Thread(target=open_browser, args=(port,)).start()
            break


launch_streamlit()

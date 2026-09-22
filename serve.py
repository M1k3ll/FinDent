"""اجرای سرور با Waitress (به‌جای runserver که فقط برای توسعه است)."""
import os
import threading
import webbrowser

from waitress import serve

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from config.wsgi import application  # noqa: E402

if __name__ == "__main__":
    host = os.environ.get("FINDENT_HOST", "127.0.0.1")
    port = int(os.environ.get("FINDENT_PORT", "8000"))
    if os.environ.get("FINDENT_OPEN_BROWSER") == "1":
        threading.Timer(1.5, webbrowser.open, args=[f"http://localhost:{port}"]).start()
    print(f"Findent is running on http://localhost:{port}")
    print("Do not close this window while working. Close it to stop the server.")
    serve(application, host=host, port=port, threads=4)

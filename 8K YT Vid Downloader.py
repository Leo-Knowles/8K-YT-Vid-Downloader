import yt_dlp
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, Task
from rich.text import Text
import os
import pyperclip
import pyfiglet
import shutil

console = Console()
RAINBOW = ["red", "yellow", "green", "cyan", "blue", "magenta"]

# ================= RAINBOW TEXT =================
def rainbow_text(text: str) -> Text:
    t = Text()
    for i, char in enumerate(text):
        t.append(char, style=RAINBOW[i % len(RAINBOW)])
    return t

def rprint(text="", end="\n"):
    console.print(rainbow_text(text), end=end)

def rinput(prompt_text: str) -> str:
    console.print(rainbow_text(prompt_text), end="")
    value = input()
    console.print(rainbow_text(value))
    return value

# ================= BANNER =================
def banner():
    try:
        width = shutil.get_terminal_size().columns
    except:
        width = 80
    art = pyfiglet.figlet_format("8K Video Downloader!!", font="standard", width=width)
    for line in art.splitlines():
        console.print(rainbow_text(line))

# ================= FOLDER SELECT =================
def choose_folder():
    base = os.path.expanduser("~")
    folders = {
        "1": os.path.join(base, "Desktop"),
        "2": os.path.join(base, "Downloads"),
        "3": os.path.join(base, "Pictures"),
        "4": os.path.join(base, "Music"),
        "5": os.path.join(base, "Videos"),
        "6": os.path.join(base, "Documents"),
    }

    rprint("Select download folder:")
    for k, v in folders.items():
        rprint(f"{k}) {os.path.basename(v)}")
    rprint("7) Custom folder")

    while True:
        choice = rinput("Choose folder [1/2/3/4/5/6/7]: ").strip()
        if choice in [str(i) for i in range(1, 8)]:
            break

    if choice == "7":
        path = rinput("Enter full custom path: ").strip()
    else:
        path = folders[choice]

    os.makedirs(path, exist_ok=True)
    return path

# ================= QUALITY SELECT =================
def choose_quality():
    options = {
        "1": ("Best Available", "bestvideo+bestaudio/best"),
        "2": ("8K (4320p)", "bestvideo[height<=4320]+bestaudio"),
        "3": ("4K (2160p)", "bestvideo[height<=2160]+bestaudio"),
        "4": ("1440p", "bestvideo[height<=1440]+bestaudio"),
        "5": ("1080p", "bestvideo[height<=1080]+bestaudio"),
        "6": ("720p", "bestvideo[height<=720]+bestaudio"),
        "7": ("480p", "bestvideo[height<=480]+bestaudio"),
        "8": ("360p", "bestvideo[height<=360]+bestaudio"),
        "9": ("240p", "bestvideo[height<=240]+bestaudio"),
        "10": ("144p (Potato 🥔)", "bestvideo[height<=144]+bestaudio"),
    }

    rprint("\nSelect Video Quality:")
    for k, v in options.items():
        rprint(f"{k}) {v[0]}")

    while True:
        choice = rinput("Choose quality [1-10]: ").strip()
        if choice in options:
            break

    return options[choice][1]

# ================= RAINBOW PROGRESS COLUMNS =================
class RainbowBarColumn(BarColumn):
    def render(self, task: Task) -> Text:
        bar = super().render(task)
        colored = Text()
        for i, c in enumerate(str(bar)):
            colored.append(c, style=RAINBOW[i % len(RAINBOW)])
        return colored

class RainbowPercentColumn(TextColumn):
    def __init__(self):
        super().__init__("{task.percentage:>3.0f}%")

    def render(self, task: Task) -> Text:
        percent_text = f"{task.percentage:>3.0f}%"
        t = Text()
        for i, char in enumerate(percent_text):
            t.append(char, style=RAINBOW[i % len(RAINBOW)])
        return t

# ================= DOWNLOAD FUNCTION =================
def download(url, folder, mode):
    opts = {
        "outtmpl": os.path.join(folder, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "logger": None
    }

    if mode == "1":  # Video
        opts["format"] = choose_quality()
        opts["merge_output_format"] = "mp4"
    elif mode == "2":  # MP3
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    elif mode == "3":  # Playlist
        opts["format"] = "bestvideo+bestaudio/best"
        opts["merge_output_format"] = "mp4"
        opts["outtmpl"] = os.path.join(folder, "%(playlist_title)s/%(title)s.%(ext)s")

    with Progress(
        RainbowBarColumn(),
        RainbowPercentColumn(),
        transient=True
    ) as progress:
        task = progress.add_task("", total=100)

        def hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
                downloaded = d.get("downloaded_bytes", 0)
                progress.update(task, completed=downloaded / total * 100)
            elif d["status"] == "finished":
                progress.update(task, completed=100)

        opts["progress_hooks"] = [hook]
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

# ================= MAIN =================
def main():
    banner()
    folder = choose_folder()
    rprint("\nDownloads will be saved to: " + folder + "\n")

    while True:
        rprint("Select mode:")
        rprint("1) Video")
        rprint("2) MP3 (Audio)")
        rprint("3) Playlist")

        mode = rinput("Choose mode [1/2/3]: ").strip()

        url = rinput("Enter YouTube URL (press Enter to use clipboard): ").strip()
        if not url:
            url = pyperclip.paste().strip()
            rprint("Using clipboard URL: " + url)

        if not url:
            rprint("No URL provided\n")
            continue

        download(url, folder, mode)
        rprint("✅ Done!\n")

        again = rinput("Download another? (y/n): ").strip().lower()
        if again != "y":
            rprint("Goodbye 👋")
            break

if __name__ == "__main__":
    main()

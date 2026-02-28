import os
import platform
import subprocess
import time
import pyperclip
import yt_dlp
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, Task
from rich.text import Text
import pyfiglet

console = Console()
RAINBOW = ["#FF00FF", "#00FFFF", "#00FF00", "#FFFF00", "#FF6600", "#FF0000"]

# ================= Rainbow Utilities =================
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

# ================= Banner =================
def banner():
    try:
        width = os.get_terminal_size().columns
    except:
        width = 80
    art = pyfiglet.figlet_format("NASA DOWNLOADER", font="slant", width=width)
    for line in art.splitlines():
        console.print(rainbow_text(line))
    rprint("Networked Audio & Stream Acquirer\n")

# ================= Folder Selection =================
def choose_folder():
    base = os.path.expanduser("~")
    folders = {
        "1": os.path.join(base, "Desktop"),
        "2": os.path.join(base, "Downloads"),
        "3": os.path.join(base, "Music"),
        "4": os.path.join(base, "Videos"),
        "5": os.path.join(base, "Documents"),
    }
    rprint("Select download folder:")
    for k, v in folders.items():
        rprint(f"{k}) {os.path.basename(v)}")
    rprint("6) Custom folder")
    while True:
        choice = rinput("Choose folder [1-6]: ").strip()
        if choice in [str(i) for i in range(1, 7)]:
            break
    if choice == "6":
        path = rinput("Enter full custom path: ").strip()
    else:
        path = folders[choice]
    os.makedirs(path, exist_ok=True)
    return path

# ================= GPU Detection =================
def detect_gpu():
    device_name = platform.processor() or "Unknown CPU"
    nvenc_available = False
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            device_name = result.stdout.strip()
            encoders = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
            if any(x in encoders.stdout for x in ["h264_nvenc", "hevc_nvenc"]):
                nvenc_available = True
    except FileNotFoundError:
        pass
    if device_name and 'NVIDIA' not in device_name.upper():
        device_name += ' (Not NVIDIA)'
    return device_name, nvenc_available

# ================= Progress Bar =================
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

# ================= Audio Filters =================
def build_audio_filters(bass=0, trim_start=0, trim_end=None, fadein=0, fadeout=0, normalize=False):
    filters = []
    if bass > 0:
        filters.append(f"bass=g={bass}")
    if normalize:
        filters.append("loudnorm")
    if fadein > 0:
        filters.append(f"afade=t=in:st=0:d={fadein}")
    if fadeout > 0 and trim_end:
        start_time = max(trim_end - fadeout, 0)
        filters.append(f"afade=t=out:st={start_time}:d={fadeout}")
    if trim_start > 0 or trim_end:
        end = trim_end if trim_end else 0
        filters.append(f"atrim=start={trim_start}:end={end}")
    return ','.join(filters) if filters else None

# ================= Download Core =================
def download(url, folder, mode="video_audio", video_opts=None, audio_opts=None, extra_args=None):
    opts = {
        "outtmpl": os.path.join(folder, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "concurrent_fragment_downloads": 4,
        "noplaylist": True
    }
    if video_opts:
        opts["format"] = video_opts.get("format", "bestvideo+bestaudio/best")

    postprocs = []

    if mode in ["audio_only", "video_audio"] and audio_opts:
        postprocs.append({
            "key": "FFmpegExtractAudio",
            "preferredcodec": audio_opts.get("codec", "mp3"),
            "preferredquality": audio_opts.get("quality", "192"),
        })
        if audio_opts.get("filters"):
            postprocs.append({"key": "FFmpegMetadata"})

    if postprocs:
        opts["postprocessors"] = postprocs
    if extra_args:
        opts["postprocessor_args"] = extra_args

    with Progress(RainbowBarColumn(), RainbowPercentColumn(), transient=True) as progress:
        task = progress.add_task("", total=100)
        def hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                if total:
                    downloaded = d.get("downloaded_bytes", 0)
                    progress.update(task, completed=downloaded / total * 100)
            elif d["status"] == "finished":
                progress.update(task, completed=100)
        opts["progress_hooks"] = [hook]

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except Exception as e:
            rprint(f"❌ Download failed: {e}")

# ================= Auto 8K Quality =================
def auto_quality_format():
    return "bestvideo+bestaudio/best"

def auto_download(url, folder):
    video_opts = {"format": auto_quality_format(), "container": "mp4", "gpu": True, "nvenc": True}
    audio_opts = {"codec": "mp3", "quality": "320"}
    download(url, folder, mode="video_audio", video_opts=video_opts, audio_opts=audio_opts)
    rprint("✅ Automatic download complete!")

def auto_mode_loop(folder):
    last_url = ""
    rprint("🚀 Automatic Archival Mode Active (Clipboard Watcher)")
    rprint("Copy a YouTube URL and it will download automatically!\n")
    try:
        while True:
            url = pyperclip.paste().strip()
            if url != last_url and url.startswith(("http://","https://")):
                last_url = url
                rprint(f"Detected URL: {url}")
                auto_download(url, folder)
            time.sleep(2)
    except KeyboardInterrupt:
        rprint("👋 Exiting Automatic Mode")

# ================= URL Type =================
def detect_type(url):
    if "playlist" in url or "list=" in url:
        return "playlist"
    return "video"

# ================= Interactive Manual Mode =================
def manual_mode(folder):
    quality_map = [
        ("Best (auto)",       "bestvideo+bestaudio/best"),
        ("8K",                "bestvideo[height>=4320]+bestaudio/best"),
        ("4K",                "bestvideo[height>=2160]+bestaudio/best"),
        ("2160p",             "bestvideo[height>=2160]+bestaudio/best"),
        ("1440p",             "bestvideo[height>=1440]+bestaudio/best"),
        ("1080p",             "bestvideo[height>=1080]+bestaudio/best"),
        ("720p",              "bestvideo[height>=720]+bestaudio/best"),
        ("480p",              "bestvideo[height>=480]+bestaudio/best"),
        ("360p",              "bestvideo[height>=360]+bestaudio/best"),
        ("144p",              "bestvideo[height>=144]+bestaudio/best"),
    ]

    while True:
        url = rinput("Enter YouTube URL (press Enter for clipboard): ").strip()
        if not url:
            url = pyperclip.paste().strip()
            rprint(f"Using clipboard URL: {url}")
        if not url.startswith(("http://","https://")):
            rprint("Invalid URL format\n")
            continue

        content_type = detect_type(url)
        rprint("Detected:", "Playlist 📃" if content_type=="playlist" else "Single Video 🎬")

        rprint("Select Download Type:")
        rprint("1) Video & Audio (Default)")
        rprint("2) Video Only (No Audio)")
        rprint("3) Audio Only (No Video)")
        dtype = rinput("Choose type [1-3, default 1]: ").strip()
        if dtype not in ["1","2","3"]:
            dtype = "1"
        mode_map = {"1":"video_audio","2":"video_only","3":"audio_only"}
        download_mode = mode_map[dtype]

        # Video options
        video_opts = {}
        if download_mode != "audio_only":
            rprint("Select Video Quality (8K+ where available):")
            for i, (label, _) in enumerate(quality_map,1):
                rprint(f"{i}) {label}")
            choice = rinput("Choose quality [1, default 1]: ").strip()
            try:
                idx = int(choice)-1
                fmt = quality_map[idx][1]
            except:
                fmt = "bestvideo+bestaudio/best"
            video_opts["format"] = fmt
            video_opts["container"] = rinput("Video container (mp4/mkv/mov/avi) leave blank for mp4: ").strip() or "mp4"
            video_opts["gpu"] = rinput("Use GPU if available? [y/n]: ").lower() == "y"

        # Audio options
        audio_opts = {}
        if download_mode != "video_only":
            audio_opts["codec"] = rinput("mp3/m4a/flac/wav/ogg leave blank for mp3: ").strip() or "mp3"
            audio_opts["quality"] = rinput("Bitrate kbps (192 default): ").strip() or "192"

        extra_args = rinput("Extra FFmpeg args (leave blank for none): ").strip().split() or None

        download(url, folder, mode=download_mode, video_opts=video_opts, audio_opts=audio_opts, extra_args=extra_args)
        rprint("✅ Download complete!\n")
        again = rinput("Download another? (y/n): ").strip().lower()
        if again != "y":
            rprint("Goodbye 👋")
            break

# ================= MAIN =================
def main():
    banner()
    folder = choose_folder()
    gpu_name, nvenc_available = detect_gpu()
    rprint(f"[SYSTEM] Device: {gpu_name}")
    rprint(f"[SYSTEM] NVENC Available: {nvenc_available}\n")

    rprint("Select Mode:")
    rprint("1) Manual Interactive Mode")
    rprint("2) Automatic 8K Archival Mode")
    mode = rinput("Choose mode [1-2, default 1]: ").strip()
    if mode not in ["1","2"]:
        mode = "1"

    if mode == "1":
        manual_mode(folder)
    else:
        auto_mode_loop(folder)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        rprint(f"[ERROR] {e}")
        traceback.print_exc()
        input("Press Enter to exit...")

import os
import sys
import subprocess
import platform
import pyperclip
import yt_dlp
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, Task
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from rich.table import Table
import pyfiglet

console = Console()
RAINBOW = ["#FF00FF", "#00FFFF", "#00FF00", "#FFFF00", "#FF6600", "#FF0000"]

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
        width = os.get_terminal_size().columns
    except:
        width = 80
    art = pyfiglet.figlet_format("NASA DOWNLOADER", font="slant", width=width)
    for line in art.splitlines():
        console.print(rainbow_text(line))
    rprint("Networked Audio & Stream Acquirer\n")

# ================= FOLDER SELECT =================
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

# ================= GPU DETECTION =================
def detect_gpu():
    gpu_name = platform.processor() or "Unknown CPU"
    nvenc_available = False
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                                capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            gpu_name = result.stdout.strip()
            encoders = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
            if "h264_nvenc" in encoders.stdout or "hevc_nvenc" in encoders.stdout:
                nvenc_available = True
    except FileNotFoundError:
        pass

    if gpu_name and 'NVIDIA' not in gpu_name.upper():
        gpu_name += ' (Not NVIDIA)'

    return gpu_name, nvenc_available

# ================= PROGRESS BAR =================
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

# ================= AUDIO FILTER =================
def build_audio_filters(bass=0, trim_start=0, trim_end=None, fadein=0, fadeout=0, normalize=False):
    filters = []
    if bass > 0:
        filters.append(f"bass=g={bass}")
    if normalize:
        filters.append("loudnorm")
    if fadein > 0:
        filters.append(f"afade=t=in:st=0:d={fadein}")
    if fadeout > 0:
        filters.append(f"afade=t=out:st={trim_end - fadeout if trim_end else 0}:d={fadeout}")
    if trim_start > 0 or trim_end:
        end = trim_end if trim_end else '0'
        filters.append(f"atrim=start={trim_start}:end={end}")
    return ','.join(filters) if filters else None

# ================= DOWNLOAD FUNCTION =================
def download(url, folder, mode="video_audio", video_opts=None, audio_opts=None, extra_args=None):
    opts = {"outtmpl": os.path.join(folder, "%(title)s.%(ext)s"),
            "quiet": True, "no_warnings": True, "ignoreerrors": True}

    # Video & Audio
    if mode in ["video_audio", "video_only"]:
        opts["format"] = video_opts.get("format", "bestvideo+bestaudio/best")
        opts["merge_output_format"] = video_opts.get("container", "mp4")
        if video_opts.get("gpu") and video_opts.get("nvenc"):
            opts["postprocessors"] = [{"key":"FFmpegVideoConvertor","preferedformat":video_opts.get("container","mp4")}]

    # Audio Only
    if mode in ["audio_only", "video_audio"]:
        postproc = [{"key": "FFmpegExtractAudio",
                     "preferredcodec": audio_opts.get("codec", "mp3"),
                     "preferredquality": audio_opts.get("quality", "192")}]
        if audio_opts.get("filters"):
            postproc.append({"key":"FFmpegMetadata"})
        opts["postprocessors"] = postproc

    if extra_args:
        opts["postprocessor_args"] = extra_args

    with Progress(RainbowBarColumn(), RainbowPercentColumn(), transient=True) as progress:
        task = progress.add_task("", total=100)
        def hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
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

# ================= URL TYPE =================
def detect_type(url):
    if "playlist" in url or "list=" in url:
        return "playlist"
    return "video"

# ================= MAIN =================
def main():
    banner()
    folder = choose_folder()
    gpu_name, nvenc_available = detect_gpu()
    rprint(f"[SYSTEM] GPU Detected: {gpu_name}")
    rprint(f"[SYSTEM] NVENC Available: {nvenc_available}\n")

    # Mode selection
    rprint("Select Downloader Mode:")
    rprint("1) Basic")
    rprint("2) Advanced")
    rprint("3) Nerdy (Pro Audio Mode)")
    mode = rinput("Choose mode [1-3, default 1]: ").strip()
    if mode not in ["1","2","3"]:
        mode = "1"

    # Download Loop
    while True:
        url = rinput("Enter YouTube URL (press Enter for clipboard): ").strip()
        if not url:
            try:
                url = pyperclip.paste().strip()
                rprint(f"Using clipboard URL: {url}")
            except Exception:
                url = ""
        if not url:
            rprint("No URL provided\n")
            continue

        content_type = detect_type(url)
        if content_type == "playlist":
            rprint("Detected: Playlist 📃")
        else:
            rprint("Detected: Single Video 🎬")

        # Download mode
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
        if download_mode != "audio_only" and mode in ["2","3"]:
            rprint("Select Video Quality:")
            quality_map = ["best","8k","4k","2160p","1440p","1080p","720p","480p","360p","240p","144p"]
            for i, q in enumerate(quality_map, 1):
                rprint(f"{i}) {q}")
            choice = rinput("Choose quality [1, default 1]: ").strip()
            video_opts["format"] = quality_map[int(choice)-1] if choice.isdigit() and 1<=int(choice)<=len(quality_map) else "best"
            video_opts["container"] = rinput("Video container (mp4/mkv/mov/avi) leave blank for mp4: ").strip() or "mp4"
            video_opts["gpu"] = rinput("Use GPU if available? [y/n]: ").lower() == "y"
            video_opts["nvenc"] = nvenc_available and video_opts["gpu"]

        # Audio options
        audio_opts = {}
        if download_mode != "video_only" and mode in ["2","3"]:
            rprint("Select Audio Format:")
            audio_opts["codec"] = rinput("mp3/m4a/flac/wav/ogg leave blank for mp3: ").strip() or "mp3"
            audio_opts["quality"] = rinput("Bitrate kbps (192 default): ").strip() or "192"
            if mode=="3":
                bass = rinput("Bass boost (1-1000, default 0): ").strip()
                bass = int(bass) if bass.isdigit() else 0
                audio_opts["filters"] = build_audio_filters(bass=bass)

        extra_args = rinput("Extra FFmpeg args (leave blank for none): ").strip().split() or None

        download(url, folder, mode=download_mode, video_opts=video_opts, audio_opts=audio_opts, extra_args=extra_args)
        rprint("✅ Download complete!\n")
        again = rinput("Download another? (y/n): ").strip().lower()
        if again != "y":
            rprint("Goodbye 👋")
            break

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        rprint(f"[ERROR] {e}")
        traceback.print_exc()
        input("Press Enter to exit...")

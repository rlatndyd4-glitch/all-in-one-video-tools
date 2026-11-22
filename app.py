import hmac
import ipaddress
import json
import os
import socket
import tempfile
import threading
import time
import uuid
from collections import deque
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import streamlit as st
import yt_dlp

st.set_page_config(page_title="만능 영상 도구 · All-in-One Video Tool", page_icon="🎬", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap');
:root { --ink:#182230; --muted:#687386; --line:#e8ebf1; --accent:#7657f6; }
html, body, [class*="css"] { font-family:'DM Sans','Noto Sans KR',sans-serif; }
.stApp { background:radial-gradient(ellipse at 88% 0%,#eeeaff 0,transparent 34%),#f7f8fc; color:var(--ink); }
.block-container { max-width:1040px; padding-top:3.5rem; padding-bottom:4rem; }
.hero { padding:28px 32px 32px; border:1px solid #e8e5f5; border-radius:24px; background:linear-gradient(120deg,rgba(255,255,255,.96),rgba(245,242,255,.94)); box-shadow:0 14px 40px rgba(36,27,84,.06); }
.kicker { color:#7657f6; font-weight:700; font-size:.78rem; letter-spacing:.14em; }
.hero h1 { font-size:2.1rem; letter-spacing:-.045em; margin:.42rem 0 .45rem; color:#172033; }
.hero p { color:#687386; margin:0; font-size:1rem; }
.stForm { border:1px solid var(--line); border-radius:18px; padding:20px; background:rgba(255,255,255,.88); box-shadow:0 8px 26px rgba(35,43,70,.045); }
.section-title { font-size:1.18rem; font-weight:750; color:#182230; margin:0 0 4px; }
.section-sub { color:#778195; font-size:.9rem; margin:0 0 18px; }
div[data-testid="stTextInput"] input { border-radius:12px; border-color:#dfe3ec; background:#fbfcff; }
.stButton>button, .stDownloadButton>button { border-radius:12px; font-weight:650; min-height:44px; }
div[data-testid="stFormSubmitButton"] button { background:linear-gradient(100deg,#7557f5,#5d74ff); color:white; border:0; }
div[data-testid="stMetric"] { background:#fff; border:1px solid var(--line); border-radius:15px; padding:15px 18px; }
footer { visibility:hidden; }
@media(max-width:700px) { .hero{padding:23px 20px}.hero h1{font-size:1.65rem}.panel{padding:19px} }
</style>
""", unsafe_allow_html=True)

L10N = {
    "한국어": {
        "language": "Language", "hero_title": "영상 링크 하나로, 간편하게.",
        "hero_sub": "지원되는 공개 영상 링크를 넣고 원본 또는 음성 제거 파일을 저장하세요.",
        "link_title": "① 영상 링크", "link_help": "공개적으로 접근 가능한 영상 주소를 입력해 주세요.",
        "url_placeholder": "https://영상 링크를 붙여 넣으세요", "check": "영상 확인하기",
        "fetching": "영상 정보를 확인하고 있어요…", "too_long": "현재는 15분 이하 영상만 지원합니다.",
        "link_error": "링크를 확인하지 못했어요. 공개 링크인지, 지원되는 사이트인지 확인해 주세요.",
        "vimeo_note": "Vimeo 미리보기는 표시했지만, 이 앱에서는 Vimeo 다운로드를 지원하지 않아요. Vimeo 페이지에서 소유자가 허용한 다운로드 옵션을 확인해 주세요.",
        "preview_title": "② 영상 미리보기", "preview_help": "아래 정보를 확인한 뒤 원하는 파일을 선택하세요.",
        "unknown_title": "영상", "unknown_channel": "채널 정보 없음", "channel": "채널",
        "duration": "길이 · {minutes}분 {seconds}초",
        "rights": "다운로드 권리가 있는 영상만 이용해 주세요. 사이트 정책과 저작권을 확인하세요.",
        "download_title": "③ 다운로드",
        "download_help": "720p 무료 옵션 · 1080p 광고 없는 테스트 옵션 · 파일당 200MB · 영상 길이 15분 이하",
        "original": "원본 영상 · 720p", "original_help": "영상과 소리를 함께 저장",
        "mute": "음성 제거 · 720p", "mute_help": "영상만 저장하고 소리는 제거",
        "quality1080": "1080p · 광고 없이", "quality1080_help": "광고 없는 테스트 다운로드",
        "prepare": "{label} 준비하기", "preparing": "파일을 준비하고 있어요…", "save": "⬇ 내 기기에 저장",
        "file_limit": "파일이 200MB 제한을 넘었습니다.", "length_error": "15분 이하 영상만 처리할 수 있어요.",
        "download_error": "파일을 만들지 못했어요. 링크가 공개 상태인지 확인해 주세요.",
        "footer": "개인정보를 저장하지 않으며, 최근 24시간 통계만 메모리에 임시 보관합니다. 무료 서버가 재시작되면 통계는 초기화됩니다. 일부 사이트는 다운로드를 지원하지 않을 수 있습니다.",
        "admin": "관리자 통계", "admin_password": "관리자 비밀번호",
        "admin_secret": "관리자 비밀번호를 배포 설정의 Secrets에 ADMIN_PASSWORD로 등록하면 이용할 수 있습니다.",
        "visitors": "24시간 방문자", "downloads": "다운로드 요청", "volume": "요청 파일 용량",
        "ad_views": "광고 시청", "ad_unavailable": "미연동",
        "admin_note": "방문자는 익명 세션 기준 추정치, 용량은 다운로드 요청 기준입니다. 광고는 아직 연결되지 않았습니다.",
        "reset_stats": "24시간 통계 초기화", "stats_reset_done": "통계를 초기화했습니다.",
        "wrong_password": "비밀번호가 맞지 않습니다.",
    },
    "English": {
        "language": "Language", "hero_title": "Video links made simple.",
        "hero_sub": "Paste a supported public video link to save the video or a version without audio.",
        "link_title": "① Video link", "link_help": "Enter a publicly accessible video URL.",
        "url_placeholder": "Paste a video link here", "check": "Check video",
        "fetching": "Checking video details…", "too_long": "Videos must be 15 minutes or shorter.",
        "link_error": "Could not read this link. Check that it is public and supported.",
        "vimeo_note": "The Vimeo preview is available, but downloads are not supported here. Check Vimeo for a download option enabled by the owner.",
        "preview_title": "② Preview", "preview_help": "Review the details, then choose a download option.",
        "unknown_title": "Video", "unknown_channel": "Channel unavailable", "channel": "Channel",
        "duration": "Length · {minutes} min {seconds} sec",
        "rights": "Only download videos you have the right to use. Check copyright and the source site's terms.",
        "download_title": "③ Downloads",
        "download_help": "Free 720p options · 1080p ad-free test option · 200 MB per file · Up to 15 minutes",
        "original": "Original · 720p", "original_help": "Save video with audio",
        "mute": "Remove audio · 720p", "mute_help": "Save video without audio",
        "quality1080": "1080p · Ad-free", "quality1080_help": "Ad-free test download",
        "prepare": "Prepare {label}", "preparing": "Preparing your file…", "save": "⬇ Save to my device",
        "file_limit": "The file exceeds the 200 MB limit.", "length_error": "Only videos up to 15 minutes are supported.",
        "download_error": "Could not prepare the file. Check that the link is public.",
        "footer": "We do not store personal information. Anonymous statistics are kept in memory for 24 hours and may reset when the free server restarts. Some sites may not support downloads.",
        "admin": "Admin statistics", "admin_password": "Admin password",
        "admin_secret": "Set ADMIN_PASSWORD in the app's deployment Secrets to enable this section.",
        "visitors": "Visitors · 24h", "downloads": "Download requests", "volume": "Requested data",
        "ad_views": "Ad views", "ad_unavailable": "Not connected",
        "admin_note": "Visitor count is an anonymous session estimate. Data volume is based on download requests. Ads are not connected yet.",
        "reset_stats": "Reset 24-hour statistics", "stats_reset_done": "Statistics have been reset.",
        "wrong_password": "Incorrect password.",
    },
    "日本語": {
        "language": "Language", "hero_title": "動画リンクから、かんたん保存。",
        "hero_sub": "対応している公開動画リンクを貼り付けて、動画または音声なしのファイルを保存できます。",
        "link_title": "① 動画リンク", "link_help": "誰でも閲覧できる動画URLを入力してください。",
        "url_placeholder": "動画リンクを貼り付けてください", "check": "動画を確認",
        "fetching": "動画情報を確認しています…", "too_long": "現在、15分以内の動画に対応しています。",
        "link_error": "リンクを確認できません。公開リンクか、対応サイトかをご確認ください。",
        "vimeo_note": "Vimeoのプレビューを表示しましたが、このアプリではダウンロードに対応していません。動画ページで所有者が許可したダウンロード設定をご確認ください。",
        "preview_title": "② 動画プレビュー", "preview_help": "内容を確認して、保存方法を選んでください。",
        "unknown_title": "動画", "unknown_channel": "チャンネル情報なし", "channel": "チャンネル",
        "duration": "長さ · {minutes}分{seconds}秒",
        "rights": "ダウンロードする権利のある動画のみご利用ください。著作権とサイトの利用規約をご確認ください。",
        "download_title": "③ ダウンロード",
        "download_help": "無料720p · 1080p広告なしテスト版 · 1ファイル200MBまで · 15分以内",
        "original": "元動画 · 720p", "original_help": "音声付きで保存",
        "mute": "音声なし · 720p", "mute_help": "音声を削除して保存",
        "quality1080": "1080p · 広告なし", "quality1080_help": "広告なしのテストダウンロード",
        "prepare": "{label}を準備", "preparing": "ファイルを準備しています…", "save": "⬇ 端末に保存",
        "file_limit": "ファイルが200MBの上限を超えています。", "length_error": "15分以内の動画のみ処理できます。",
        "download_error": "ファイルを準備できませんでした。公開リンクかご確認ください。",
        "footer": "個人情報は保存しません。匿名統計はメモリに24時間だけ保存され、無料サーバーの再起動時に消去されることがあります。一部のサイトはダウンロードに対応していません。",
        "admin": "管理者統計", "admin_password": "管理者パスワード",
        "admin_secret": "利用するには、デプロイ設定のSecretsにADMIN_PASSWORDを設定してください。",
        "visitors": "24時間の訪問者", "downloads": "ダウンロード要求", "volume": "要求されたデータ量",
        "ad_views": "広告視聴", "ad_unavailable": "未連携",
        "admin_note": "訪問者数は匿名セッションによる推定値です。容量はダウンロード要求に基づきます。広告はまだ連携されていません。",
        "reset_stats": "24時間統計をリセット", "stats_reset_done": "統計をリセットしました。",
        "wrong_password": "パスワードが正しくありません。",
    },
}

LANGUAGE_NAMES = {"한국어": "Korean", "English": "English", "日本語": "Japanese"}

with st.container():
    lang_col, _ = st.columns([1, 3])
    lang_col.selectbox(
        "Language", list(L10N), format_func=lambda language: LANGUAGE_NAMES[language], key="ui_language"
    )
T = L10N[st.session_state.ui_language]

def tr(key, **kwargs):
    return T[key].format(**kwargs)

MAX_BYTES = 200 * 1024 * 1024
MAX_SECONDS = 15 * 60
WINDOW = 24 * 60 * 60

@st.cache_resource
def stats_store():
    return {"events": deque(), "lock": threading.Lock()}

def record(kind, value=0):
    store = stats_store()
    now = time.time()
    with store["lock"]:
        store["events"].append((now, kind, value))
        while store["events"] and now - store["events"][0][0] > WINDOW:
            store["events"].popleft()

def recent_stats():
    store = stats_store()
    now = time.time()
    with store["lock"]:
        while store["events"] and now - store["events"][0][0] > WINDOW:
            store["events"].popleft()
        rows = list(store["events"])
    return {
        "visitors": len({v for t, k, v in rows if k == "visit"}),
        "downloads": sum(1 for t, k, v in rows if k == "download"),
        "bytes": sum(v for t, k, v in rows if k == "download"),
    }

def reset_stats():
    store = stats_store()
    with store["lock"]:
        store["events"].clear()

def safe_url(raw):
    parsed = urlparse(raw.strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("http 또는 https 주소를 입력해 주세요.")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "metadata.google.internal"} or host.endswith(".local"):
        raise ValueError("공개 웹사이트 주소만 사용할 수 있어요.")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
        if not addresses or any(not ipaddress.ip_address(addr).is_global for addr in addresses):
            raise ValueError("공개 웹사이트 주소만 사용할 수 있어요.")
    except socket.gaierror:
        raise ValueError("주소를 찾을 수 없어요. 링크를 다시 확인해 주세요.")
    return raw.strip()

def vimeo_oembed_info(url):
    endpoint = "https://vimeo.com/api/oembed.json?" + urlencode({"url": url})
    request = Request(endpoint, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=12) as response:
        data = json.loads(response.read().decode("utf-8"))
    return {
        "title": data.get("title"),
        "thumbnail": data.get("thumbnail_url"),
        "uploader": data.get("author_name"),
        "duration": data.get("duration"),
    }

def download_video(url, mute=False, max_height=720):
    workdir = tempfile.mkdtemp(prefix="jarvis_")
    progress = {"size": 0}
    def hook(data):
        if data.get("status") == "downloading":
            size = data.get("total_bytes") or data.get("total_bytes_estimate") or data.get("downloaded_bytes") or 0
            progress["size"] = max(progress["size"], size)
            if progress["size"] > MAX_BYTES:
                raise RuntimeError("파일이 200MB 제한을 넘었습니다.")
    fmt = (f"bestvideo[height<={max_height}][ext=mp4]/bestvideo[height<={max_height}]"
           if mute else f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]")
    opts = {
        "format": fmt, "outtmpl": os.path.join(workdir, "video.%(ext)s"),
        "merge_output_format": "mp4", "quiet": True, "no_warnings": True,
        "noplaylist": True, "max_filesize": MAX_BYTES, "socket_timeout": 20,
        "retries": 1, "fragment_retries": 1, "progress_hooks": [hook],
        "restrictfilenames": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info.get("duration") and info["duration"] > MAX_SECONDS:
                raise RuntimeError("15분 이하 영상만 처리할 수 있어요.")
            output = Path(ydl.prepare_filename(info))
            if not output.exists():
                candidates = list(Path(workdir).glob("video.*"))
                if not candidates:
                    raise RuntimeError("다운로드 파일을 찾지 못했습니다.")
                output = candidates[0]
        if mute:
            import subprocess
            muted = Path(workdir) / "jarvis_muted.mp4"
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(output), "-map", "0:v:0", "-c:v", "copy", "-an", str(muted)],
                check=True, capture_output=True, timeout=180,
            )
            output = muted
        if output.stat().st_size > MAX_BYTES:
            raise RuntimeError("파일이 200MB 제한을 넘었습니다.")
        return output.read_bytes(), output.name
    finally:
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)

if "visitor_id" not in st.session_state:
    st.session_state.visitor_id = uuid.uuid4().hex
    record("visit", st.session_state.visitor_id)

st.markdown(f"""
<div class="hero">
  <div class="kicker">ALL-IN-ONE VIDEO TOOLS</div>
  <h1>{T['hero_title']}</h1>
  <p>{T['hero_sub']}</p>
</div>
""", unsafe_allow_html=True)

st.markdown(f'<div class="section-title">{T["link_title"]}</div><div class="section-sub">{T["link_help"]}</div>', unsafe_allow_html=True)
with st.form("link_form"):
    entered_url = st.text_input(T["link_title"], placeholder=T["url_placeholder"], label_visibility="collapsed")
    submitted = st.form_submit_button(T["check"], use_container_width=True)

if submitted:
    st.session_state.pop("video_info", None)
    st.session_state.pop("video_url", None)
    try:
        checked = safe_url(entered_url)
        hostname = (urlparse(checked).hostname or "").lower()
        is_vimeo = hostname == "vimeo.com" or hostname.endswith(".vimeo.com")
        can_download = True
        with st.spinner(T["fetching"]):
            try:
                with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True, "socket_timeout": 15}) as ydl:
                    info = ydl.extract_info(checked, download=False)
            except Exception:
                if not is_vimeo:
                    raise
                info = vimeo_oembed_info(checked)
                can_download = False
        if info.get("duration") and info["duration"] > MAX_SECONDS:
            st.warning(T["too_long"])
        else:
            st.session_state.video_info = {
                "title": info.get("title", T["unknown_title"]), "thumbnail": info.get("thumbnail"),
                "uploader": info.get("uploader", T["unknown_channel"]),
                "duration": info.get("duration"),
                "can_download": can_download,
            }
            st.session_state.video_url = checked
    except Exception:
        st.error(T["link_error"])

info = st.session_state.get("video_info")
if info:
    st.markdown(f'<div class="section-title">{T["preview_title"]}</div><div class="section-sub">{T["preview_help"]}</div>', unsafe_allow_html=True)
    left, right = st.columns([1, 1.45], gap="large")
    with left:
        if info["thumbnail"]:
            st.image(info["thumbnail"], use_container_width=True)
    with right:
        st.markdown(f"### {info['title']}")
        st.caption(f"{T['channel']} · {info['uploader']}")
        if info["duration"]:
            st.caption(tr("duration", minutes=int(info["duration"]) // 60, seconds=int(info["duration"]) % 60))
        st.info(T["rights"])
    if not info.get("can_download", True):
        st.warning(T["vimeo_note"])
    else:
        st.markdown(f'<div class="section-title">{T["download_title"]}</div><div class="section-sub">{T["download_help"]}</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3, gap="medium")
        for col, mute, max_height, label, desc, key in [
            (col1, False, 720, T["original"], T["original_help"], "original_720"),
            (col2, True, 720, T["mute"], T["mute_help"], "mute_720"),
            (col3, False, 1080, T["quality1080"], T["quality1080_help"], "original_1080"),
        ]:
            with col:
                st.markdown(f"**{label}**  \n{desc}")
                if st.button(tr("prepare", label=label), key=f"make_{key}", use_container_width=True):
                    try:
                        with st.spinner(T["preparing"]):
                            data, filename = download_video(st.session_state.video_url, mute, max_height)
                        st.session_state[f"file_{key}"] = (data, filename)
                    except Exception as exc:
                        message = str(exc)
                        if "200MB" in message:
                            st.warning(T["file_limit"])
                        elif "15분" in message:
                            st.warning(T["length_error"])
                        else:
                            st.error(T["download_error"])
                item = st.session_state.get(f"file_{key}")
                if item:
                    st.download_button(
                        T["save"], data=item[0], file_name=item[1],
                        mime="video/mp4", key=f"save_{key}", use_container_width=True,
                        on_click=record, args=("download", len(item[0])),
                    )
st.caption(T["footer"])

with st.expander(T["admin"]):
    try:
        configured = st.secrets.get("ADMIN_PASSWORD", "")
    except st.errors.StreamlitSecretNotFoundError:
        configured = ""
    if not configured:
        st.caption(T["admin_secret"])
    else:
        supplied = st.text_input(T["admin_password"], type="password", key="admin_password")
        if supplied and hmac.compare_digest(supplied, configured):
            stats = recent_stats()
            a, b, c, d = st.columns(4)
            a.metric(T["visitors"], stats["visitors"])
            b.metric(T["downloads"], stats["downloads"])
            c.metric(T["volume"], f"{stats['bytes'] / (1024**3):.2f} GB")
            d.metric(T["ad_views"], T["ad_unavailable"])
            st.caption(T["admin_note"])
            if st.button(T["reset_stats"], key="reset_24h_stats"):
                reset_stats()
                st.session_state["stats_reset_done"] = True
                st.rerun()
            if st.session_state.pop("stats_reset_done", False):
                st.success(T["stats_reset_done"])
        elif supplied:
            st.error(T["wrong_password"])

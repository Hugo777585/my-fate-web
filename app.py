import base64
import json
import os
import pathlib
import runpy
import warnings

import streamlit as st
import streamlit.components.v1 as components

warnings.filterwarnings("ignore", message=".*Unable to load P12 key.*")


def _ensure_hugo_key_json():
    key_file_path = pathlib.Path(__file__).with_name("hugo-key.json")
    if key_file_path.exists():
        return

    service_account_info = None
    try:
        service_account_info = st.secrets["GCP_SERVICE_ACCOUNT"]
    except (FileNotFoundError, KeyError):
        try:
            service_account_info = st.secrets["gcp_service_account"]
        except (FileNotFoundError, KeyError):
            service_account_info = None

    if not service_account_info:
        return

    if isinstance(service_account_info, str):
        service_account_info = json.loads(service_account_info)

    if service_account_info is not None:
        if hasattr(service_account_info, "to_dict"):
            service_account_info = service_account_info.to_dict()
        else:
            service_account_info = dict(service_account_info)

    key_file_path.write_text(
        json.dumps(service_account_info, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _patch_banner_iframe():
    original_iframe = components.iframe

    def patched_iframe(*args, **kwargs):
        src = kwargs.get("src")
        if src == "/static/banner.html":
            try:
                html_path = pathlib.Path(__file__).with_name("hugo_banner.html")
                html_content = html_path.read_text(encoding="utf-8")

                audio_path = pathlib.Path(__file__).with_name("温暖而有力量的人.mp3.mp3")
                if audio_path.exists():
                    audio_b64 = base64.b64encode(audio_path.read_bytes()).decode()
                    html_content = html_content.replace(
                        'src="温暖而有力量的人.mp3.mp3"',
                        f'src="data:audio/mpeg;base64,{audio_b64}"',
                    )

                height = kwargs.get("height", 750)
                scrolling = kwargs.get("scrolling", False)
                return components.html(html_content, height=height, scrolling=scrolling)
            except Exception:
                pass
        return original_iframe(*args, **kwargs)

    components.iframe = patched_iframe


_ensure_hugo_key_json()
_patch_banner_iframe()

_app_path = pathlib.Path(__file__).with_name("app_backup.py")
runpy.run_path(str(_app_path), run_name="__main__")

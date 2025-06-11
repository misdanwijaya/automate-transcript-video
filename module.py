from datetime import datetime
from dotenv import load_dotenv

import streamlit as st
import os
import subprocess
import time
import google.generativeai as genai

# ==== Load API Key dari .env ====
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
#konfigurasi genai
genai.configure(api_key=api_key)

def download_file(file_format,file_url):
    timestamp_format = "%Y%m%d_%H%M%S"
    current_time_str = datetime.now().strftime(timestamp_format)
    output_filename = f"file_{current_time_str}.{file_format}"
    if file_format=="mp3":
            command = [
                'yt-dlp',
                '--quiet',
                # Opsi untuk mengekstrak audio dan mengkonversinya ke mp3
                '--extract-audio',
                '--audio-format', 'mp3',
                # Opsi untuk menjaga kualitas audio terbaik
                '--audio-quality', '0', # 0 berarti kualitas terbaik
                '-o', output_filename,
                file_url
            ]
    elif file_format=="mp4":
            command = [
                'yt-dlp',
                '--quiet',
                '-f', 'best[ext=mp4]',
                '-o', output_filename,
                file_url
            ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    
    return output_filename

def upload_to_gemini(output_filename):
    #upload file ke gemini
    uploaded_file = genai.upload_file(path=output_filename)
    st.success(f"✅ Upload berhasil. URI File: {uploaded_file.uri}, Name: {uploaded_file.name}")
    
    st.info("⏳ Menunggu file menjadi ACTIVE...")
    timeout_seconds = 300  # Misalnya 5 menit
    start_time = time.time()

    countdown_placeholder = st.empty()

    while time.time() - start_time < timeout_seconds:
        elapsed = time.time() - start_time
        remaining = int(timeout_seconds - elapsed)
        minutes, seconds = divmod(remaining, 60)
        
        file_status = genai.get_file(name=uploaded_file.name).state.name

        # Tampilkan status file dan waktu tersisa
        countdown_placeholder.info(
            f"🕒 Waktu tersisa: **{minutes:02d}:{seconds:02d}**\n\n📄 File Status: `{file_status}`"
        )

        #checker status active file
        if file_status == "ACTIVE":
            st.success(f"✅ File siap diproses!, Status: {file_status}")
            countdown_placeholder.empty()
            break
        elif file_status == "FAILED":
            st.error("❌ Server gagal memproses video. Coba dengan video lain.")
            countdown_placeholder.empty()
            raise Exception("File processing failed on server.")
        
        # Tunggu 5 detik sebelum periksa lagi
        time.sleep(5)
    
    else:
        st.error("⏱️ Timeout! File tidak pernah menjadi ACTIVE.")
    
    return uploaded_file

def get_transcript(uploaded_file):
    #membuat transcript
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    prompt = [
        "Anda adalah seorang ahli transkripsi. Tolong transkripsikan audio dari video ini ke dalam Bahasa Indonesia.",
        "Tuliskan transkripnya secara lengkap dan akurat, kata per kata.",
        "Kembalikan hanya teks transkripsinya, tanpa kalimat pembuka atau tambahan lainnya.",
        uploaded_file
    ]
    response = model.generate_content(prompt, request_options={'timeout': 600})

    return response

def delete_file(output_filename,uploaded_file):
    os.remove(output_filename)
    genai.delete_file(uploaded_file.name)
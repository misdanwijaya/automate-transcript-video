import streamlit as st
import os
import subprocess
import time
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
from st_copy_to_clipboard import st_copy_to_clipboard

# ==== Load API Key dari .env ====
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# ==== Konfigurasi halaman Streamlit ====
st.set_page_config(
    page_title="Transkrip Video Otomatis",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 Transkrip Media Sosial Otomatis")
st.write("Masukkan URL postingan dari YouTube, Instagram, TikTok, atau platform lain yang didukung.")


# ==== Metode Analisis====
format_options = {
    "Audio (untuk kebutuhan cepat)": "mp3",
    "Video (untuk analisis kompleks)": "mp4"
}
selected_format_label = st.radio(
    "Pilih metode analisis yang dibutuhkan:",
    options=format_options.keys(),
    horizontal=True
)
file_format = format_options[selected_format_label]

# ==== Input URL Video ====
file_url = st.text_input("🔗 Masukan URL", placeholder="https://www.instagram.com/p/xxxxx/", key="url_input")

# ==== Jika URL sudah dimasukkan ====
if file_url:
    if not api_key:
        st.error("API key tidak ditemukan. Pastikan file .env berisi GOOGLE_API_KEY.")
        st.stop()

    with st.spinner("Mengonfigurasi API Key..."):
        try:
            genai.configure(api_key=api_key)
        except Exception as e:
            st.error("Gagal mengonfigurasi API Key.")
            st.stop()
    
    timestamp_format = "%Y%m%d_%H%M%S"
    current_time_str = datetime.now().strftime(timestamp_format)
    output_filename = f"file_{current_time_str}.{file_format}"

    with st.spinner("📥 Mengunduh file.."):
        try:

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
            st.success(f"✅ File berhasil diunduh dan disimpan sebagai: '{output_filename}'")
                    
        except subprocess.CalledProcessError as e:
            st.error(f"❌ Gagal mengunduh video.\n{e.stderr}")
            st.stop()

    with st.spinner("☁️ Mengunggah ke Gemini File API..."):
        try:
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

        except Exception as e:
            st.error(f"❌ Gagal upload ke Gemini: {e}")
            st.stop()

    with st.spinner("🧠 Meminta transkrip dari Gemini... (maks 10 menit)"):
        try:

           #membuat transcript
            model = genai.GenerativeModel(model_name="gemini-1.5-flash")
            prompt = [
                "Anda adalah seorang ahli transkripsi. Tolong transkripsikan audio dari video ini ke dalam Bahasa Indonesia.",
                "Tuliskan transkripnya secara lengkap dan akurat, kata per kata.",
                "Kembalikan hanya teks transkripsinya, tanpa kalimat pembuka atau tambahan lainnya.",
                uploaded_file
            ]
            response = model.generate_content(prompt, request_options={'timeout': 600})
            st.success("✅ Transkrip berhasil dibuat!")
            st.subheader("📄 Hasil Transkrip:")
            st.text_area("Transkrip:", response.text, height=400)
            st_copy_to_clipboard(response.text)
        
        except Exception as e:
            st.error(f"❌ Gagal membuat transkrip: {e}")
            st.stop()

    with st.spinner("🧹 Membersihkan file sementara..."):
        try:
            os.remove(output_filename)
            genai.delete_file(uploaded_file.name)
            st.success("✅ File lokal dan file server berhasil dihapus.")

        except Exception as e:
            st.warning(f"⚠️ Terjadi kesalahan saat menghapus file: {e}")
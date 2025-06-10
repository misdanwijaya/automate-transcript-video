import streamlit as st
import os
import subprocess
import time
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

st.title("🎬 Transkrip Video Otomatis")
st.write("Masukkan URL video dari YouTube, Instagram, TikTok, atau platform lain yang didukung.")

# ==== Input URL Video ====
video_url = st.text_input("🔗 Masukkan URL Video", placeholder="https://www.instagram.com/p/xxxxx/")

# ==== Jika URL sudah dimasukkan ====
if video_url:
    if not api_key:
        st.error("API key tidak ditemukan. Pastikan file .env berisi GOOGLE_API_KEY.")
        st.stop()

    with st.spinner("Mengonfigurasi API Key..."):
        try:
            genai.configure(api_key=api_key)
        except Exception as e:
            st.error("Gagal mengonfigurasi API Key.")
            st.stop()

    output_filename = "audio.mp3"

    with st.spinner("📥 Mengunduh video dan konversi ke audio..."):
        try:
            command = [
                'yt-dlp',
                '--quiet',
                # Opsi untuk mengekstrak audio dan mengkonversinya ke mp3
                '--extract-audio',
                '--audio-format', 'mp3',
                # Opsi untuk menjaga kualitas audio terbaik
                '--audio-quality', '0', # 0 berarti kualitas terbaik
                '-o', output_filename,
                video_url
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)
            st.success(f"✅ Audio berhasil diunduh dan disimpan sebagai: '{output_filename}'")
                    
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
                    st.success(f"✅ Video siap diproses!, Status: {file_status}")
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
                uploaded_file
            ]
            response = model.generate_content(prompt, request_options={'timeout': 600})
            st.success("✅ Transkrip berhasil dibuat!")
            st.subheader("📄 Hasil Transkrip:")
            st_copy_to_clipboard(response.text)
            st.text_area("Transkrip:", response.text, height=400)
        
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

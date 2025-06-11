import streamlit as st
import subprocess
from st_copy_to_clipboard import st_copy_to_clipboard
from module import is_valid_url, download_file, upload_to_gemini, get_transcript, delete_file

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

    # ==== Checker URL ====
    if not is_valid_url(file_url):
        st.error("URL tidak sah. Harap masukkan URL yang benar (contoh: https://www.youtube.com/...).")
        st.stop() # Menghentikan eksekusi jika URL tidak sah

    # ==== Download File ====
    with st.spinner("📥 Mengunduh file.."):
        try:

            output_filename = download_file(file_format,file_url)
            st.success(f"✅ File berhasil diunduh dan disimpan sebagai: '{output_filename}'")
                    
        except subprocess.CalledProcessError as e:
            st.error(f"❌ Gagal mengunduh video.\n{e.stderr}")
            st.stop()

    # ==== Upload File ke Gemini ====
    with st.spinner("☁️ Mengunggah ke Gemini File API..."):
        try:
            uploaded_file=upload_to_gemini(output_filename)

        except Exception as e:
            st.error(f"❌ Gagal upload ke Gemini: {e}")
            st.stop()

    # ==== Transkrip File ====
    with st.spinner("🧠 Meminta transkrip dari Gemini... (maks 10 menit)"):
        try:
            
            response = get_transcript(uploaded_file)
            st.success("✅ Transkrip berhasil dibuat!")
            st.subheader("📄 Hasil Transkrip:")
            st.text_area("Transkrip:", response.text, height=400)
            st_copy_to_clipboard(response.text)
        
        except Exception as e:
            st.error(f"❌ Gagal membuat transkrip: {e}")
            st.stop()

    # ==== Delete File ====
    with st.spinner("🧹 Membersihkan file sementara..."):
        try:
            delete_file(output_filename,uploaded_file)
            st.success("✅ File lokal dan file server berhasil dihapus.")

        except Exception as e:
            st.warning(f"⚠️ Terjadi kesalahan saat menghapus file: {e}")
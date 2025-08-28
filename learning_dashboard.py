
# learning_dashboard.py
# Streamlit dashboard for an Active Learning routine (Recall + Feynman + Refleksi)
import streamlit as st
import pandas as pd
from pathlib import Path
import uuid, datetime as dt

DATA_DIR = Path("./learning_data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_CSV = DATA_DIR / "sessions.csv"
CARDS_CSV = DATA_DIR / "cards.csv"
REFLECTIONS_CSV = DATA_DIR / "reflections.csv"
FEYNMAN_CSV = DATA_DIR / "feynman_notes.csv"

SRS_STEPS = [1, 3, 7, 14, 30]  # days

def load_df(path, columns):
    if not path.exists():
        pd.DataFrame(columns=columns).to_csv(path, index=False)
    df = pd.read_csv(path)
    # Normalize date columns if present
    for c in ["date","created_at","next_due","week_start"]:
        if c in df.columns:
            try:
                df[c] = pd.to_datetime(df[c]).dt.date
            except Exception:
                pass
    return df

def save_df(path, df):
    df.to_csv(path, index=False)

def add_session_log(date, session, topic, recall, new_study, practice, review, feynman, minutes, notes):
    df = load_df(SESSIONS_CSV, ["date","session","topic","recall_done","new_study_done","practice_done","review_done","feynman_done","minutes","notes"])
    row = {
        "date": date, "session": session, "topic": topic,
        "recall_done": bool(recall), "new_study_done": bool(new_study),
        "practice_done": bool(practice), "review_done": bool(review),
        "feynman_done": bool(feynman), "minutes": int(minutes or 0), "notes": notes or ""
    }
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_df(SESSIONS_CSV, df)

def add_card(question, answer, tags):
    df = load_df(CARDS_CSV, ["id","question","answer","tags","created_at","stage","next_due","last_result"])
    now = dt.date.today()
    row = {
        "id": str(uuid.uuid4()), "question": question.strip(),
        "answer": (answer or "").strip(),
        "tags": (tags or "").strip(),
        "created_at": now, "stage": 0,
        "next_due": now, "last_result": ""
    }
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_df(CARDS_CSV, df)

def review_card(card_id, result):
    df = load_df(CARDS_CSV, ["id","question","answer","tags","created_at","stage","next_due","last_result"])
    idx = df.index[df["id"] == card_id]
    if len(idx) == 0: return
    i = idx[0]
    today = dt.date.today()
    if result == "ingat":
        stage = int(df.at[i,"stage"]) + 1
        if stage >= len(SRS_STEPS): stage = len(SRS_STEPS) - 1
        df.at[i,"stage"] = stage
        df.at[i,"next_due"] = today + dt.timedelta(days=int(SRS_STEPS[stage]))
        df.at[i,"last_result"] = "ingat"
    else:
        df.at[i,"stage"] = 0
        df.at[i,"next_due"] = today + dt.timedelta(days=SRS_STEPS[0])
        df.at[i,"last_result"] = "lupa"
    save_df(CARDS_CSV, df)

def add_reflection(week_start, understand, confused, next_plan):
    df = load_df(REFLECTIONS_CSV, ["week_start","understand","confused","next_plan","created_at"])
    row = {
        "week_start": week_start,
        "understand": understand, "confused": confused, "next_plan": next_plan,
        "created_at": dt.date.today()
    }
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_df(REFLECTIONS_CSV, df)

def add_feynman(date, concept, explanation, analogy, clarity):
    df = load_df(FEYNMAN_CSV, ["date","concept","explanation","analogy","clarity_rating"])
    row = {
        "date": date, "concept": concept, "explanation": explanation,
        "analogy": analogy, "clarity_rating": clarity
    }
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_df(FEYNMAN_CSV, df)

def compute_streak():
    df = load_df(SESSIONS_CSV, ["date","session","topic","recall_done","new_study_done","practice_done","review_done","feynman_done","minutes","notes"])
    if df.empty: return 0
    days = sorted(set(pd.to_datetime(df["date"]).dt.date))
    if not days: return 0
    today = dt.date.today()
    streak = 0
    d = today
    while d in days:
        streak += 1
        d = d - dt.timedelta(days=1)
    return streak

# UI
st.set_page_config(page_title="Live Dashboard Pembelajaran", page_icon="📚", layout="wide")

st.sidebar.title("📚 Dashboard Belajar")
page = st.sidebar.radio("Navigasi", ["Hari Ini", "Kartu Tanya (Recall)", "Feynman", "Refleksi Mingguan", "Statistik", "Data mentah"])

with st.sidebar:
    st.markdown("---")
    st.caption("Teknik: Active Recall • Spaced Repetition • Feynman • Refleksi")
    streak = compute_streak()
    st.metric("Streak hari ini", f"{streak} hari")

# ---- PAGE: HARI INI ----
if page == "Hari Ini":
    st.header("📆 Hari Ini")
    today = dt.date.today()
    st.write(f"Tanggal: **{today.strftime('%A, %d %B %Y')}**")

    st.subheader("Catat Sesi Pagi / Sore")
    with st.form("log_session"):
        col1, col2, col3 = st.columns([1.2,1,1])
        with col1:
            session = st.selectbox("Sesi", ["Pagi", "Sore"])
            topic = st.text_input("Topik (mis. Basis Data, Jaringan, dll.)")
        with col2:
            recall = st.checkbox("Recall")
            new_study = st.checkbox("Materi Baru")
            practice = st.checkbox("Latihan/Praktek")
        with col3:
            review = st.checkbox("Review")
            feynman = st.checkbox("Feynman")
            minutes = st.number_input("Menit belajar", min_value=0, max_value=240, value=45, step=5)
        notes = st.text_area("Catatan singkat (opsional)")
        submitted = st.form_submit_button("Simpan Sesi")
        if submitted:
            if not topic.strip():
                st.warning("Isi topik dulu ya.")
            else:
                add_session_log(today, session, topic, recall, new_study, practice, review, feynman, minutes, notes)
                st.success("Sesi tersimpan!")

    st.subheader("Kartu Recall Jatuh Tempo (hari ini & terlewat)")
    cards = load_df(CARDS_CSV, ["id","question","answer","tags","created_at","stage","next_due","last_result"])
    if cards.empty:
        st.info("Belum ada kartu. Tambah kartu di menu 'Kartu Tanya (Recall)'.")
    else:
        due = cards[(pd.to_datetime(cards["next_due"]).dt.date <= today)]
        if due.empty:
            st.success("Tidak ada kartu jatuh tempo. Mantap 🎉")
        else:
            st.dataframe(due[["question","tags","stage","next_due","last_result"]])

# ---- PAGE: KARTU TANYA ----
elif page == "Kartu Tanya (Recall)":
    st.header("🗂️ Kartu Tanya (Recall)")
    with st.expander("➕ Tambah kartu baru"):
        with st.form("add_card"):
            q = st.text_area("Pertanyaan (bahasamu sendiri, 1 ide per kartu)")
            a = st.text_area("Jawaban/penjelasan (opsional)")
            tags = st.text_input("Tag (pisahkan dengan koma)")
            submit = st.form_submit_button("Simpan Kartu")
            if submit:
                if not q.strip():
                    st.warning("Pertanyaan tidak boleh kosong.")
                else:
                    add_card(q, a, tags)
                    st.success("Kartu ditambahkan!")

    st.subheader("Review Kartu Jatuh Tempo")
    cards = load_df(CARDS_CSV, ["id","question","answer","tags","created_at","stage","next_due","last_result"])
    today = dt.date.today()
    due = cards[(pd.to_datetime(cards["next_due"]).dt.date <= today)]
    if due.empty:
        st.info("Tidak ada kartu jatuh tempo. Kamu bisa tetap review kartu mana saja di bawah.")
    else:
        st.write(f"Jumlah kartu jatuh tempo: **{len(due)}**")
        # ambil satu kartu dulu (first due)
        c = due.sort_values(by="next_due").iloc[0]
        st.markdown(f"**Pertanyaan:** {c['question']}")
        if st.button("Tampilkan Jawaban/Hint"):
            st.info(c["answer"] if isinstance(c["answer"], str) and c['answer'].strip() else "(Belum ada jawaban tersimpan)")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Ingat"):
                review_card(c["id"], "ingat")
                st.rerun()
        with col2:
            if st.button("↩️ Lupa"):
                review_card(c["id"], "lupa")
                st.rerun()

    st.subheader("Semua Kartu")
    if not cards.empty:
        st.dataframe(cards[["question","tags","stage","next_due","last_result"]])
    else:
        st.caption("Belum ada kartu.")

# ---- PAGE: FEYNMAN ----
elif page == "Feynman":
    st.header("🧠 Catatan Feynman (jelaskan ke 'anak SMP')")
    today = dt.date.today()
    with st.form("feynman_form"):
        date = st.date_input("Tanggal", value=today)
        concept = st.text_input("Konsep (mis. Primary Key, IP Address, Algoritma)")
        explanation = st.text_area("Jelaskan 5–7 kalimat (bahasa sehari-hari)")
        analogy = st.text_area("Analogi sehari-hari (contoh: NIS di sekolah untuk Primary Key)")
        clarity = st.slider("Seberapa jelas pemahamanmu?", 1, 5, 3)
        submit = st.form_submit_button("Simpan Catatan")
        if submit:
            if not concept.strip() or not explanation.strip():
                st.warning("Konsep dan penjelasan wajib diisi.")
            else:
                add_feynman(date, concept, explanation, analogy, clarity)
                st.success("Catatan Feynman tersimpan!")

    df = load_df(FEYNMAN_CSV, ["date","concept","explanation","analogy","clarity_rating"])
    st.subheader("Riwayat Feynman Terbaru")
    if df.empty:
        st.caption("Belum ada catatan.")
    else:
        st.dataframe(df.sort_values(by="date", ascending=False).head(20))

# ---- PAGE: REFLEKSI MINGGUAN ----
elif page == "Refleksi Mingguan":
    st.header("🪞 Refleksi Mingguan")
    # week start = Monday of current week
    today = dt.date.today()
    week_start = today - dt.timedelta(days=today.weekday())
    with st.form("reflection_form"):
        ws = st.date_input("Minggu mulai (Senin)", value=week_start)
        st.write("Template (isi langsung):")
        understand = st.text_area("Aku paham …")
        confused = st.text_area("Aku masih bingung …")
        next_plan = st.text_area("Minggu depan aku harus …")
        submit = st.form_submit_button("Simpan Refleksi")
        if submit:
            add_reflection(ws, understand, confused, next_plan)
            st.success("Refleksi tersimpan!")

    df = load_df(REFLECTIONS_CSV, ["week_start","understand","confused","next_plan","created_at"])
    st.subheader("Riwayat Refleksi")
    if df.empty:
        st.caption("Belum ada refleksi.")
    else:
        st.dataframe(df.sort_values(by="week_start", ascending=False))

# ---- PAGE: STATISTIK ----
elif page == "Statistik":
    st.header("📈 Statistik & Ringkasan")
    sessions = load_df(SESSIONS_CSV, ["date","session","topic","recall_done","new_study_done","practice_done","review_done","feynman_done","minutes","notes"])
    cards = load_df(CARDS_CSV, ["id","question","answer","tags","created_at","stage","next_due","last_result"])
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total sesi tercatat", len(sessions))
    col2.metric("Total kartu", len(cards))
    col3.metric("Kartu jatuh tempo hari ini", len(cards[pd.to_datetime(cards["next_due"]).dt.date <= dt.date.today()]))
    col4.metric("Streak hari berturut-turut", compute_streak())

    if not sessions.empty:
        sessions_plot = sessions.groupby("date")["minutes"].sum().reset_index()
        st.subheader("Menit belajar per hari")
        st.line_chart(sessions_plot, x="date", y="minutes", height=260)
        st.subheader("Sebaran sesi per topik")
        by_topic = sessions.groupby("topic")["minutes"].sum().reset_index().sort_values("minutes", ascending=False)
        st.bar_chart(by_topic, x="topic", y="minutes", height=260)

    st.subheader("Status Kartu (stage)")
    if not cards.empty:
        stage_count = cards.groupby("stage")["id"].count().reset_index().rename(columns={"id":"jumlah"})
        st.bar_chart(stage_count, x="stage", y="jumlah", height=260)
    else:
        st.caption("Belum ada kartu.")

# ---- PAGE: DATA ----
elif page == "Data mentah":
    st.header("🧾 Data Mentah (CSV)")
    st.write("Folder data: `./learning_data` (di samping file app). Simpan otomatis.")
    st.write("• sessions.csv • cards.csv • reflections.csv • feynman_notes.csv")

    s = load_df(SESSIONS_CSV, ["date","session","topic","recall_done","new_study_done","practice_done","review_done","feynman_done","minutes","notes"])
    st.subheader("sessions.csv")
    st.dataframe(s)

    c = load_df(CARDS_CSV, ["id","question","answer","tags","created_at","stage","next_due","last_result"])
    st.subheader("cards.csv")
    st.dataframe(c)

    r = load_df(REFLECTIONS_CSV, ["week_start","understand","confused","next_plan","created_at"])
    st.subheader("reflections.csv")
    st.dataframe(r)

    f = load_df(FEYNMAN_CSV, ["date","concept","explanation","analogy","clarity_rating"])
    st.subheader("feynman_notes.csv")
    st.dataframe(f)

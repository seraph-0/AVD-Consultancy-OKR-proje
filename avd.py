import altair as alt
import pandas as pd
import streamlit as st
import sqlite3
import time
import os
import google.generativeai as genai
import re
import json

# API anahtarı ayarı
os.environ['GEMINI_API_KEY'] = 'AIzaSyA1-uLTtQ4YRhZpDfrC82LMp0S23nT_K34'
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

generation_config = {
    "temperature": 0.9,  # Farklı ve çeşitli yanıtlar almak için sıcaklık değerini arttırdık
    "top_p": 0.95,
    "top_k": 60,
    "max_output_tokens": 512,
    "response_mime_type": "text/plain",
}

# Modelin yapılandırılması
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-exp-0827",
    generation_config=generation_config,
)

# SQLite bağlantısı ve tablo oluşturma
conn = sqlite3.connect('chatbot.db')
c = conn.cursor()

def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history
                 (question TEXT PRIMARY KEY, response TEXT)''')
    conn.commit()

def insert_into_db(question, response):
    c.execute("INSERT OR IGNORE INTO chat_history (question, response) VALUES (?, ?)",
              (question, response))
    conn.commit()

def get_response_from_db(question):
    c.execute("SELECT response FROM chat_history WHERE question = ?", (question,))
    result = c.fetchone()
    return result[0] if result else None

init_db()

# Gantt grafiği oluşturma fonksiyonu
def generate_gantt_chart(data):
    df = pd.DataFrame(data)
    df['start'] = pd.to_datetime(df['start'])
    df['end'] = pd.to_datetime(df['end'])
    
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('start:T', axis=alt.Axis(title='Başlangıç Tarihi')),
        x2='end:T',
        y=alt.Y('task:N', axis=alt.Axis(title='Görevler')),
        color=alt.Color('task:N', legend=None),
        tooltip=['task', 'start', 'end']
    ).properties(
        title='KPI Hedefleri Gantt Grafiği',
        width=800,
        height=300
    )
    return chart

def get_chart(data):
    return generate_gantt_chart(data)

# Sidebar düzenlemesi
def display_sidebar():
    with st.sidebar:
        st.image('./speda.png', use_column_width=True)
        st.write(""" 
        **Speda: AI KPI Assistant**
        KPI verileri oluşturma, veri modelleme ve grafik destek konularında yardımcı olurum. Sorularınız için buradayım!
        """)
        st.write(""" 
        - **Başlangıç Tarihi**: KPI hedeflerinize ne zaman başlayacağınızı belirleyin.
        - **Bitiş Tarihi**: Hedeflerinizi tamamlamayı planladığınız zaman dilimi.
        - **Görevler**: KPI hedeflerinizi ayrıntılı olarak belirleyin ve zamanlayın.
        """)
        st.write("### Hesap Ayarları")
        if st.button('Giriş Yap'):
            st.write("Giriş yapıldı.")
        if st.button('Çıkış Yap'):
            st.write("Çıkış yapıldı.")

display_sidebar()

# Ana başlığı mavi renkte göstermek
st.markdown(
    """
    <style>
    .main-title { color: #1f77b4; font-size: 36px; font-weight: bold; }
    </style>
    <div class="main-title">
    Speda: AI KPI Assistant
    </div>
    """,
    unsafe_allow_html=True
)

avd_prompt = """
Adın Speda. Bir KPI hesaplama asistanısın. Sana sorulan şirket için KPI üreteceksin. Eğer KPI ile ilgili birşey istenmezse Normal bir şekilde muhabbet de edebilirsin. Veri modelini sunacaksın. Grafik oluşturmalarına destek olacaksın. AVD Danışmanlık ve Boğaziçi Üniversitesi bünyesinde staj yapan 6 öğrencinin bitirme projesisin.
KPI verilerini JSON formatında sağlamalısınız. Örnek JSON:
[ 
    {"task": "Enerji Verimliliğini %20 Artırma", "start": "2024-01-01", "end": "2024-12-31"},
    {"task": "Geri Dönüştürülen Atık Miktarını %30 Artırma", "start": "2024-03-01", "end": "2024-09-30"}
] Bu verilerle Gantt chart oluşturulacak.
"""

# st.session_state başlatma
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Size nasıl yardımcı olabilirim?"}
    ]

if 'chart' not in st.session_state:
    st.session_state['chart'] = None

if 'show_chart' not in st.session_state:
    st.session_state['show_chart'] = False

# Kullanıcı selamlaşmasını kontrol eden fonksiyon
def check_for_greeting(prompt):
    greetings = ["merhaba", "selam", "günaydın", "iyi akşamlar", "nasılsın"]
    return any(greeting in prompt.lower() for greeting in greetings)

def generate_response(prompt):
    if check_for_greeting(prompt):
        return "Merhaba! Size nasıl yardımcı olabilirim?"
    try:
        response = model.generate_content([ 
            avd_prompt, 
            f"input: {prompt}", 
            "output: | |"
        ])
        return response.text
    except Exception as e:
        return f'API Hatası: {e}'

def type_text(response_text, delay=0.05):
    placeholder = st.empty()
    for i in range(len(response_text) + 1):
        placeholder.write(response_text[:i])
        time.sleep(delay)

# Chat input ve yanıt işleme
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user", avatar="🧑‍💻").write(prompt)
    placeholder = st.chat_message("assistant", avatar="🕷")
    response = get_response_from_db(prompt)
    if response is None:
        response = generate_response(prompt)
        insert_into_db(prompt, response)
    placeholder.empty()
    type_text(response)
    
    # JSON verisi kontrolü ve işleme
    try:
        json_strings = re.findall(r'\[\s*\{(?:[^{}]*|\{[^{}]*\})*\}(?:\s*,\s*\{(?:[^{}]*|\{[^{}]*\})*\})*\s*\]', response)
        
        if not json_strings:
            st.session_state.messages.append({"role": "assistant", "content": "Geçersiz JSON formatı veya veri bulunamadı."})
        else:
            for json_str in json_strings:
                try:
                    data = json.loads(json_str)
                    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                        for item in data:
                            if 'start' in item and 'end' in item:
                                try:
                                    pd.to_datetime(item['start'])
                                    pd.to_datetime(item['end'])
                                except ValueError:
                                    raise ValueError('Geçersiz tarih formatı')
                        chart = get_chart(data)
                        st.session_state['chart'] = chart
                        st.session_state.messages.append({"role": "assistant", "content": json.dumps(data, indent=2)})
                        break
                except json.JSONDecodeError:
                    continue
            else:
                st.session_state.messages.append({"role": "assistant", "content": "Gantt chart için gerekli veriler bulunamadı."})
    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"Grafik oluşturulurken hata: {str(e)}"})

# Buton ve Gantt chart görünürlüğü
if st.button('Göster/Gizle'):
    st.session_state['show_chart'] = not st.session_state['show_chart']

if st.session_state['show_chart']:
    if st.session_state['chart']:
        st.altair_chart(st.session_state['chart'], theme="streamlit", use_container_width=True)
    else:
        st.write("KPI verisi bulunamadı veya JSON formatında hata var.")

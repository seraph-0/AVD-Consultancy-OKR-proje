import re
import json
import altair as alt
import pandas as pd
import streamlit as st
import sqlite3
import time
import os
import google.generativeai as genai

os.environ['GEMINI_API_KEY'] = 'AIzaSyA1-uLTtQ4YRhZpDfrC82LMp0S23nT_K34'
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 512,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)


def generate_gantt_chart(data):
    df = pd.DataFrame(data)
    chart = alt.Chart(df).mark_bar().encode(
        x='start',
        x2='end',
        y='task'
    )
    return chart

def getChart(data):
    chart = generate_gantt_chart(data)
    return chart

st.image('./speda.png')
st.title("Speda: AI KPI Assistant")

avd_prompt = """
Adın Speda. Bir KPI hesaplama asistanısın. KPI ile ilgili soru sorılmadığında kullanıcı ile sohbet edebilirsin. Sana sorulan şirket için KPI üreteceksin. Sana KPI ile ilgili soru sorulmadığında KPI üretmeni istemiyorum, kullanıcıyla sohbet edebilirsin. Veri modelini sunacaksın. Grafik oluşturmalarına destek olacaksın. AVD Danışmanlık ve Boğaziçi Üniversitesi bünyesinde staj yapan 6 öğrencinin bitirme projesisin.
[
    {"task": "task", "start": 1, "end": 12},
    {"task": "task", "start": 3, "end": 9}
] Bu örnek veri ile sorulacak soruları ilişkilendir. Gantt chart için veri hazırla. task yazan yerlere firma ile ilgili belirlemiş olduğun hedefleri koy.Bulduğun hedefleri yıl icerisinde bölerek start ve end degerlerini yerlestir JSON formatında cevap vermek zorundasın. Kısa Cevap Ver!!!
"""

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Size nasıl yardımcı olabilirim?"}]

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message(msg["role"], avatar="🧑‍💻").write(msg["content"])
    else:
        st.chat_message(msg["role"], avatar="🕷").write(msg["content"])

def generate_response(prompt):
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
        # JSON formatında olabilecek kısımları bulmak için regex
        json_strings = re.findall(r'\[\s*\{(?:[^{}]*|\{[^{}]*\})*\}(?:\s*,\s*\{(?:[^{}]*|\{[^{}]*\})*\})*\s*\]', response)
        
        # Her JSON stringini kontrol et
        for json_str in json_strings:
            try:
                data = json.loads(json_str)
                if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                    # Geçerli JSON verisi varsa Gantt grafiği oluştur
                    chart = getChart(data)
                    st.session_state['chart'] = chart
                    break
            except json.JSONDecodeError:
                continue
        else:
            # JSON verisi bulunamazsa veya geçersizse mesajı göster
            st.session_state.messages.append({"role": "assistant", "content": response})
    except Exception as e:
        st.write(f'Bir hata oluştu: {e}')

# Buton ve Gantt chart görünürlüğü
if 'show_chart' not in st.session_state:
    st.session_state['show_chart'] = False

if st.button('Göster/Gizle'):
    st.session_state['show_chart'] = not st.session_state['show_chart']

if st.session_state['show_chart']:
    if 'chart' in st.session_state:
        tab1, tab2 = st.tabs(["Streamlit Teması (Varsayılan)", "Altair Yerel Teması"])
        with tab1:
            st.altair_chart(st.session_state['chart'], theme="streamlit", use_container_width=True)
        with tab2:
            st.altair_chart(st.session_state['chart'], theme=None, use_container_width=True)
    else:
        st.write("KPI verisi bulunamadı veya JSON formatında hata var.")

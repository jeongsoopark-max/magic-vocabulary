import streamlit as st
import random
import os
import io
from gtts import gTTS
from google import genai

# --- 1. 기능 함수 정의 ---
def play_audio(text):
    tts = gTTS(text=text, lang='en')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

def get_ai_hint(word, level, api_key):
    if not api_key:
        return "API Key를 먼저 입력해주세요."
    try:
        client = genai.Client(api_key=api_key)
        prompt = f"""
        당신은 한국의 영어 교사입니다. 학생이 '{word}'라는 단어를 외우고 있습니다. 
        이 학생의 수준은 '{level}'입니다.
        이 단어가 포함된, 해당 수준의 영어 시험(내신 또는 수능)에 나올 법한 짧은 영어 예문 1개와 한국어 해석을 작성해주세요.
        형식: 
        예문: [영어 문장]
        해석: [한국어 해석]
        """
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"AI 힌트 생성 오류: {e}"

def load_words(file_path):
    word_list = []
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                parts = line.strip().split('|')
                if len(parts) >= 2:
                    word_list.append({
                        "word": parts[0].strip(),
                        "meaning": parts[1].strip(),
                        "level": parts[2].strip() if len(parts) >= 3 else "기본"
                    })
    return word_list

# --- 2. 초기 데이터 세팅 ---
if 'word_list' not in st.session_state:
    loaded_words = load_words("words.txt")
    if not loaded_words:
        loaded_words = [{"word": "sample", "meaning": "샘플", "level": "테스트"}]
    st.session_state.word_list = loaded_words

if 'quiz_started' not in st.session_state:
    st.session_state.quiz_started = False
    st.session_state.quiz_type = "단답형 주관식"
    st.session_state.current_idx = 0
    st.session_state.score = 0
    st.session_state.wrong_words = []
    st.session_state.test_pool = []

# --- 시험 시작 함수 (객관식 보기 생성 로직 추가) ---
def start_quiz(level, quiz_type):
    pool = [w for w in st.session_state.word_list if w['level'] == level]
    random.shuffle(pool)
    test_pool = pool[:10] # 10문제 추출
    
    # 5지선다 객관식일 경우, 오답 보기 4개 자동 생성
    if quiz_type == "5지선다 객관식":
        all_meanings = list(set([w['meaning'] for w in st.session_state.word_list]))
        for q in test_pool:
            correct_meaning = q['meaning']
            # 정답을 제외한 나머지 뜻 중에서 랜덤으로 4개 추출
            wrong_meanings = [m for m in all_meanings if m != correct_meaning]
            # 만약 전체 단어가 5개 미만이면 있는 대로 다 가져옴
            num_wrong = min(4, len(wrong_meanings))
            choices = random.sample(wrong_meanings, num_wrong) + [correct_meaning]
            random.shuffle(choices) # 정답 위치를 랜덤으로 섞음
            q['choices'] = choices

    st.session_state.test_pool = test_pool
    st.session_state.quiz_started = True
    st.session_state.quiz_type = quiz_type
    st.session_state.current_idx = 0
    st.session_state.score = 0
    st.session_state.wrong_words = []

# --- 3. 환경 설정 (사이드바) ---
with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.text_input("Google Gemini API Key를 입력하세요", type="password")
    if api_key:
        st.success("API Key 적용 완료!")
    else:
        st.warning("AI 힌트 기능을 쓰려면 API Key가 필요합니다.")
        
    st.divider()
    
    if st.button("🔄 최신 단어장 불러오기"):
        st.session_state.word_list = load_words("words.txt")
        st.success(f"새로고침 완료! (총 {len(st.session_state.word_list)}개 단어)")

# --- 4. 메인 UI 레이아웃 ---
st.title("🎯 스마트 영단어 실력 체크")

if not st.session_state.quiz_started:
    st.subheader("시험 설정을 선택하세요!")
    
    # 난이도 및 문제 유형 선택 UI 추가
    col1, col2 = st.columns(2)
    available_levels = list(set([w['level'] for w in st.session_state.word_list]))
    available_levels.sort()
    
    with col1:
        level = st.selectbox("📌 학년/수준 선택", available_levels)
    with col2:
        quiz_type = st.radio("📝 문제 유형", ["단답형 주관식", "5지선다 객관식"])
        
    st.write("---")
    if st.button("시험 시작 🚀", use_container_width=True):
        start_quiz(level, quiz_type)
        st.rerun()

else:
    current_pool = st.session_state.test_pool
    idx = st.session_state.current_idx

    if len(current_pool) == 0:
        st.error("이 난이도에는 아직 등록된 단어가 없습니다.")
        if st.button("돌아가기"):
            st.session_state.quiz_started = False
            st.rerun()
            
    elif idx < len(current_pool):
        progress = (idx) / len(current_pool)
        st.progress(progress)
        st.write(f"**문제 {idx + 1} / {len(current_pool)}**")

        q_word = current_pool[idx]['word']
        q_level = current_pool[idx]['level']
        
        st.markdown(f"### 정답은 무엇일까요? \n # **{q_word}**")
        
        # 발음 듣기
        audio_file = play_audio(q_word)
        st.audio(audio_file, format="audio/mp3")

        # AI 힌트
        if st.button("💡 AI 실전 예문 힌트 보기"):
            with st.spinner("AI가 예문을 만들고 있습니다..."):
                hint = get_ai_hint(q_word, q_level, api_key)
                st.info(hint)

        st.write("---")

        # --- 5. 문제 유형별 입력창 ---
        if st.session_state.quiz_type == "5지선다 객관식":
            # 객관식 UI
            user_choice = st.radio("가장 알맞은 뜻을 고르세요:", current_pool[idx]['choices'], index=None, key=f"radio_{idx}")
            
            if st.button("정답 제출 ➡️"):
                if user_choice is None:
                    st.warning("보기를 선택해주세요!")
                else:
                    if user_choice == current_pool[idx]['meaning']:
                        st.session_state.score += 1
                    else:
                        st.session_state.wrong_words.append(current_pool[idx])
                    st.session_state.current_idx += 1
                    st.rerun()

        else:
            # 주관식 UI
            user_answer = st.text_input("뜻을 입력하세요 (엔터를 치면 다음으로 넘어갑니다)", key=f"q_{idx}")
            
            if st.button("다음 문제 ➡️") or (user_answer and st.session_state.get(f"last_answer") != user_answer):
                if user_answer.strip() == current_pool[idx]['meaning']:
                    st.session_state.score += 1
                else:
                    st.session_state.wrong_words.append(current_pool[idx])
                
                st.session_state.current_idx += 1
                st.rerun()

    else:
        st.balloons()
        st.success(f"시험 종료! 당신의 점수는 **{st.session_state.score} / {len(current_pool)}** 점입니다.")
        
        if st.session_state.wrong_words:
            st.warning("🧐 다시 확인해볼 단어들:")
            for w in st.session_state.wrong_words:
                st.write(f"- **{w['word']}**: {w['meaning']}")
        
        if st.button("다시 시작하기 🔄"):
            st.session_state.quiz_started = False
            st.rerun()
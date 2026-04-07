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

# --- 2. 시험 시작 함수 (NameError 방지를 위해 상단 배치) ---
def start_quiz(level, quiz_type):
    pool = [w for w in st.session_state.word_list if w['level'] == level]
    random.shuffle(pool)
    test_pool = pool[:10] # 10문제 추출
    
    # 5지선다 객관식일 경우, 오답 보기 4개 자동 생성
    if quiz_type == "5지선다 객관식":
        all_meanings = list(set([w['meaning'] for w in st.session_state.word_list]))
        for q in test_pool:
            correct_meaning = q['meaning']
            wrong_meanings = [m for m in all_meanings if m != correct_meaning]
            num_wrong = min(4, len(wrong_meanings))
            choices = random.sample(wrong_meanings, num_wrong) + [correct_meaning]
            random.shuffle(choices) 
            q['choices'] = choices

    st.session_state.test_pool = test_pool
    st.session_state.quiz_started = True
    st.session_state.quiz_type = quiz_type
    st.session_state.current_idx = 0
    st.session_state.score = 0
    st.session_state.wrong_words = []

# --- 3. 초기 세션 및 데이터 세팅 ---
if 'student_id' not in st.session_state:
    st.session_state.student_id = "일반"

if 'word_list' not in st.session_state:
    st.session_state.word_list = load_words("words.txt")
    if not st.session_state.word_list:
        st.session_state.word_list = [{"word": "sample", "meaning": "샘플", "level": "테스트"}]

if 'quiz_started' not in st.session_state:
    st.session_state.quiz_started = False
    st.session_state.quiz_type = "단답형 주관식"
    st.session_state.current_idx = 0
    st.session_state.score = 0
    st.session_state.wrong_words = []
    st.session_state.test_pool = []

# --- 4. 환경 설정 (사이드바) ---
with st.sidebar:
    st.header("👤 사용자 인증")
    # 학생 ID 입력창
    input_name = st.text_input("학생 이름을 입력하세요", placeholder="미입력 시 일반용 로드")
    
    if st.button("접속하기"):
        if input_name.strip():
            st.session_state.student_id = input_name.strip()
            target_file = f"words_{st.session_state.student_id}.txt"
        else:
            st.session_state.student_id = "일반"
            target_file = "words.txt"
        
        # 파일 존재 여부 확인 후 로드
        loaded = load_words(target_file)
        if not loaded:
            if st.session_state.student_id != "일반":
                st.warning(f"'{target_file}' 파일이 없어 기본 단어장을 사용합니다.")
            st.session_state.word_list = load_words("words.txt")
        else:
            st.session_state.word_list = loaded
            st.success(f"{st.session_state.student_id}님 환영합니다!")
        
        st.session_state.quiz_started = False # 사용자 변경 시 퀴즈 초기화
        st.rerun()

    st.divider()
    st.header("⚙️ 설정")
    api_key = st.text_input("Google Gemini API Key", type="password")
    
    if st.button("🔄 현재 단어장 새로고침"):
        current_file = "words.txt" if st.session_state.student_id == "일반" else f"words_{st.session_state.student_id}.txt"
        st.session_state.word_list = load_words(current_file)
        st.success("새로고침 완료!")

# --- 5. 메인 UI 레이아웃 ---
st.title("🎯 스마트 영단어 실력 체크")
st.caption(f"현재 접속 모드: **{st.session_state.student_id}**")

if not st.session_state.quiz_started:
    st.subheader("시험 설정을 선택하세요!")
    
    # 난이도 및 문제 유형 선택 UI
    col1, col2 = st.columns(2)
    # 중복 제거 및 정렬하여 레벨 리스트 생성
    available_levels = sorted(list(set([w['level'] for w in st.session_state.word_list])))
    
    with col1:
        level = st.selectbox("📌 학년/수준 선택", available_levels if available_levels else ["기본"])
    with col2:
        quiz_type = st.radio("📝 문제 유형", ["단답형 주관식", "5지선다 객관식"])
        
    st.write("---")
    if st.button("시험 시작 🚀", use_container_width=True):
        if not st.session_state.word_list or st.session_state.word_list[0]['word'] == "sample":
            st.error("단어장이 비어 있습니다. 단어 파일을 확인해주세요.")
        else:
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
        
        audio_file = play_audio(q_word)
        st.audio(audio_file, format="audio/mp3")

        if st.button("💡 AI 실전 예문 힌트 보기"):
            with st.spinner("AI가 예문을 만들고 있습니다..."):
                hint = get_ai_hint(q_word, q_level, api_key)
                st.info(hint)

        st.write("---")

        # 문제 유형별 입력창
        if st.session_state.quiz_type == "5지선다 객관식":
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

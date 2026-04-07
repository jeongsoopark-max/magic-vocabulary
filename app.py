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
    # 파일이 없을 경우 빈 리스트 반환 (학생용 파일이 아직 없을 때를 대비)
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
# 학생 ID 세션 초기화
if 'student_id' not in st.session_state:
    st.session_state.student_id = "일반"

if 'word_list' not in st.session_state:
    st.session_state.word_list = load_words("words.txt")

if 'quiz_started' not in st.session_state:
    st.session_state.quiz_started = False
    st.session_state.current_idx = 0
    st.session_state.score = 0
    st.session_state.wrong_words = []
    st.session_state.test_pool = []

# --- 3. 환경 설정 (사이드바) ---
with st.sidebar:
    st.header("👤 사용자 인증")
    
    # [추가] 학생 ID 입력창
    temp_id = st.text_input("학생 이름을 입력하세요 (일반용은 비워두기)", value="")
    if st.button("로그인/전환"):
        if temp_id.strip() == "":
            st.session_state.student_id = "일반"
            target_file = "words.txt"
        else:
            st.session_state.student_id = temp_id.strip()
            target_file = f"words_{st.session_state.student_id}.txt"
        
        # 파일 로드 및 세션 초기화
        loaded = load_words(target_file)
        if not loaded and st.session_state.student_id != "일반":
            st.error(f"'{target_file}' 파일이 없습니다. 기본 단어장을 불러옵니다.")
            st.session_state.word_list = load_words("words.txt")
        else:
            st.session_state.word_list = loaded
            st.success(f"{st.session_state.student_id}님 단어장 로드 완료!")
        
        st.session_state.quiz_started = False # 시험 중이었다면 초기화
        st.rerun()

    st.divider()
    st.header("⚙️ 설정")
    api_key = st.text_input("Google Gemini API Key", type="password")
    
    if st.button("🔄 현재 단어장 새로고침"):
        fname = "words.txt" if st.session_state.student_id == "일반" else f"words_{st.session_state.student_id}.txt"
        st.session_state.word_list = load_words(fname)
        st.success("새로고침 완료!")

# --- 4. 메인 UI (기존 로직 유지) ---
st.title("🎯 스마트 영단어 실력 체크")
st.info(f"현재 접속: **{st.session_state.student_id}** 모드")

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

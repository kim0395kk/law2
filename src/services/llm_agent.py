import time

class AI_Agent:
    """
    실제 AI 연결 로직이 들어갈 자리입니다.
    지금은 폴더 구조 테스트를 위해 가짜 응답을 줍니다.
    나중에 여기에 Gemini/Groq 코드를 넣으면 됩니다.
    """
    def analyze_law(self, query):
        time.sleep(1) # AI 생각하는 척
        return f"✅ **도로교통법 제32조 (정차 및 주차의 금지)**\n\n모든 차의 운전자는 교차로, 횡단보도, 건널목이나 보도와 차도가 구분된 도로의 보도... (중략) ... 주차하여서는 아니 된다.\n\n🔍 **분석:** '{query}' 상황은 위 조항에 명백히 위배됩니다."

    def search_news(self, query):
        time.sleep(1)
        return f"📰 **[판례] 불법주정차 과태료 부과 처분 취소 청구**\n\n- 사건번호: 2023구합1234\n- 결과: 기각 (행정청 승소)\n- 요지: 단속 사진의 시각 표시가 명확하므로 처분은 적법하다."

    def draft_document(self, query):
        return {
            "title": "과태료 부과 사전통지서",
            "receiver": "위반차량 소유주 귀하",
            "ref": "교통지도팀장",
            "body_paragraphs": f"1. 귀하의 가정에 평안을 기원합니다.\n\n2. 귀하의 차량이 {query} 위반 사실이 영상단속 장치에 의해 확인되었습니다.\n\n3. 이에 따라 도로교통법 제160조에 의거하여 과태료 부과를 사전 통지하오니, 이의가 있을 경우 기한 내 의견을 제출하여 주시기 바랍니다.",
            "department_head": "충 주 시 장"
        }

# 인스턴스 생성
agent = AI_Agent()

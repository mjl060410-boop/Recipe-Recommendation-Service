# utils.py -- 냉장고 재료 기반 AI 레시피 추천 및 유틸리티 함수
import os
import json
import logging
from dotenv import load_dotenv
import google.generativeai as genai

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Fetch Gemini API Key
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    logger.warning("GEMINI_API_KEY not found in environment variables.")

def is_api_key_valid():
    """Gemini API 키가 설정되어 있고 정상적으로 작동하는지 확인합니다."""
    if not api_key:
        return False
    try:
        # 가벼운 모델 호출 테스트
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content("Ping", generation_config={"max_output_tokens": 5})
        return True
    except Exception as e:
        logger.error(f"API Key Validation Error: {e}")
        return False

def generate_recipe_from_gemini(ingredients, category, duration, difficulty, allergy_list, custom_exclusions):
    """
    냉장고 속 재료들과 사용자 선호도 옵션을 기반으로 Gemini AI에서 맞춤형 레시피 목록을 받아옵니다.
    """
    if not api_key:
        return {"error": "API Key가 설정되지 않았습니다. .env 파일을 확인해 주세요."}
    
    if not ingredients:
        return {"error": "냉장고에 넣을 재료를 선택하거나 입력해 주세요."}

    # Prompt Engineering
    allergy_str = ", ".join(allergy_list) if allergy_list else "없음"
    exclusions_str = custom_exclusions if custom_exclusions else "없음"
    
    prompt = f"""
    당신은 세계적인 수준의 5성급 호텔 전문 셰프입니다. 사용자의 냉장고 속에 남아있는 재료들과 선호도 필터를 참고하여 맛있는 요리 레시피 3가지를 추천해 주세요.

    [입력 조건]
    1. 사용 가능한 냉장고 재료: {", ".join(ingredients)}
       (이 재료들을 최대한 활용하여 요리를 고안하되, 레시피에 무조건 이 재료들만 써야 하는 것은 아닙니다. 부족한 재료는 '추가 구매 필요 재료'로 분리해 주세요.)
    2. 선호하는 요리 카테고리: {category} (한식, 일식, 중식, 양식, 퓨전/기타 등)
    3. 최대 소요 시간: {duration} (예: 15분 이내, 30분 이내, 1시간 이내, 상관없음)
    4. 요리 난이도: {difficulty} (쉬움, 보통, 어려움, 상관없음)
    5. 절대 포함 금지 성분 (기피/알레르기 재료):
       - 알레르기 유해 성분: {allergy_str}
       - 추가 제외 재료: {exclusions_str}
       (이 항목에 포함된 재료는 요리의 부재료, 양념, 데코레이션 등 그 어떤 과정에도 절대 들어가서는 안 됩니다.)

    [출력 요구조건]
    - 출력은 반드시 아래의 JSON 형식이어야 합니다. 마크다운 기호(예: ```json ... ```)를 제외한 순수 JSON 텍스트 또는 그 형식을 유지해 주세요.
    - 레시피의 요리법은 상세하게 작성해 주시고, 단계별 번호를 매겨서 보여주세요.
    - 이미지 생성 시 사용할 수 있도록 각 요리명의 정확한 영어 번역(또는 영어 이름)을 'english_title' 필드에 넣어주세요. (예: "김치찌개" -> "Kimchi stew")

    [출력 JSON 구조]
    {{
      "recipes": [
        {{
          "title": "요리 이름 (예: 치즈 계란말이)",
          "english_title": "English Name (예: Cheese Egg Roll)",
          "cooking_time": "소요 시간 (예: 15분)",
          "difficulty": "난이도 (쉬움/보통/어려움 중 택 1)",
          "category": "요리 카테고리 (한식/일식/중식/양식/퓨전 등)",
          "matching_ingredients": ["냉장고 재료 중 사용된 재료 목록"],
          "missing_ingredients": ["추가로 필요한 재료 목록 (없으면 빈 리스트)"],
          "summary": "요리에 대한 침샘을 자극하는 한 줄 요약",
          "steps": [
            "1. 달걀 3개를 깨서 그릇에 담고 소금 한 꼬집을 넣은 뒤 잘 섞어줍니다.",
            "2. 팬에 식용유를 두르고 가열한 뒤 달걀물을 절반만 붓습니다...",
            "3. 중간에 모짜렐라 치즈를 올리고 돌돌 말아줍니다..."
          ],
          "chef_tip": "셰프의 특급 팁 (예: 불 조절 요령 또는 대체 재료 팁)"
        }}
      ]
    }}
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.7
            }
        )
        
        # Parse JSON
        result = json.loads(response.text)
        return result
    except json.JSONDecodeError as je:
        logger.error(f"JSON Decode Error: {je}. Raw output was: {response.text}")
        return {"error": "AI의 응답 데이터 형식이 올바르지 않습니다. 다시 시도해 주세요."}
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return {"error": f"API 호출 중 에러가 발생했습니다: {str(e)}"}

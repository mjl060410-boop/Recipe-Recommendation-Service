# app.py -- 냉장고 재료 기반 AI 레시피 추천 서비스 (나만의 냉장고 셰프)
import streamlit as st
import json
import os
import time
import urllib.parse
from utils import is_api_key_valid, generate_recipe_from_gemini

# 1. Page Configuration & Title
st.set_page_config(
    page_title="나만의 냉장고 셰프 (My Fridge Chef)",
    page_icon="🍳",
    layout="wide"
)

# Custom Style Sheet
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Noto+Sans+KR:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', 'Outfit', sans-serif;
    }
    
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        color: #D35400;
        text-align: center;
        margin-bottom: 5px;
    }
    
    .sub-title {
        font-size: 1.1rem;
        color: #7F8C8D;
        text-align: center;
        margin-bottom: 25px;
    }
    
    .category-header {
        font-size: 1.2rem;
        font-weight: 700;
        color: #E67E22;
        margin-top: 15px;
        margin-bottom: 10px;
        border-bottom: 2px solid #FADBD8;
        padding-bottom: 5px;
    }
    
    .recipe-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 25px;
        margin-bottom: 30px;
        box-shadow: 0 10px 25px rgba(230, 126, 34, 0.08);
        border: 1px solid #FADBD8;
    }
    
    .recipe-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #2C3E50;
        margin-bottom: 10px;
    }
    
    .badge {
        display: inline-block;
        padding: 4px 10px;
        font-size: 0.85rem;
        font-weight: bold;
        border-radius: 20px;
        margin-right: 5px;
        color: white;
    }
    
    .badge-category { background-color: #E67E22; }
    .badge-time { background-color: #F1C40F; color: #2C3E50; }
    .badge-diff { background-color: #3498DB; }
    
    .ingredient-section {
        background-color: #FDF2E9;
        padding: 15px;
        border-radius: 10px;
        margin: 15px 0;
        border-left: 5px solid #E67E22;
    }
    
    .step-item {
        font-size: 1.05rem;
        line-height: 1.6;
        margin-bottom: 12px;
        color: #2C3E50;
    }
    
    .chef-tip-box {
        background-color: #FEF9E7;
        color: #5D4037 !important; /* Force a dark brown text color for contrast */
        border-left: 5px solid #F1C40F;
        padding: 12px 15px;
        border-radius: 8px;
        margin-top: 20px;
        font-style: italic;
    }
    
    .fridge-shelf {
        background-color: #F4F6F6;
        border: 2px dashed #BDC3C7;
        border-radius: 12px;
        padding: 20px;
        min-height: 100px;
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 20px;
    }
    
    .active-tag {
        background-color: #FFE5D9 !important;
        color: #D35400 !important;
        border: 1px solid #FFB4A2 !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# 2. Favorite Recipes Database Persistence
FAVORITES_FILE = "data/favorites.json"

def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        try:
            with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_favorites(favs):
    try:
        os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
        with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump(favs, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

# 2.5 Cooking History Database Persistence
HISTORY_FILE = "data/recipe_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(hist):
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(hist, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def add_to_history(recipes, ingredients):
    import datetime
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    date_str = now.strftime("%Y-%m-%d")
    
    hist_list = load_history()
    entry = {
        "timestamp": timestamp,
        "date": date_str,
        "ingredients": ingredients,
        "recipes": recipes
    }
    hist_list.insert(0, entry) # Insert latest at the top
    save_history(hist_list)

def render_recipe_image(english_title, seed, caption):
    import urllib.parse
    encoded_title = urllib.parse.quote(english_title)
    primary_url = f"https://image.pollinations.ai/prompt/A%20delicious%20and%20gorgeously%20plated%20dish%20of%20{encoded_title},%20professional%20food%20photography,%20studio%20lighting,%20warm%20rustic%20wooden%20table%20background,%20closeup%20macro%20lens?width=600&height=450&nologo=true&seed={seed}"
    secondary_url = f"https://loremflickr.com/600/450/food,cooking,{encoded_title}?random={seed}"
    static_fallback = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&auto=format&fit=crop&q=80"
    
    html_code = f"""
    <div style="text-align: center; margin-bottom: 15px;">
        <img src="{primary_url}" 
             onerror="this.onerror=function(){{this.onerror=null; this.src='{static_fallback}';}}; this.src='{secondary_url}';" 
             style="width:100%; border-radius:12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 1px solid #EAD4C3;" />
        <div style="font-size:0.85rem; color:#7F8C8D; margin-top:6px; font-style:italic;">{caption}</div>
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)

# 2.7 Cooking History Trash Database Persistence
TRASH_FILE = "data/recipe_trash.json"

def load_trash():
    if os.path.exists(TRASH_FILE):
        try:
            with open(TRASH_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_trash(trash_data):
    try:
        os.makedirs(os.path.dirname(TRASH_FILE), exist_ok=True)
        with open(TRASH_FILE, "w", encoding="utf-8") as f:
            json.dump(trash_data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def move_to_trash(entry):
    trash = load_trash()
    import datetime
    entry["deleted_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    trash.insert(0, entry)
    save_trash(trash)

# 3. Session State Initialization
if "my_ingredients" not in st.session_state:
    st.session_state.my_ingredients = set()
if "recipes_result" not in st.session_state:
    st.session_state.recipes_result = None
if "favorites" not in st.session_state:
    st.session_state.favorites = load_favorites()

# 4. App Design Header & Banner
st.image("banner.png", use_container_width=True)
st.markdown("<h1 class='main-title'>🍳 나만의 냉장고 셰프</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>냉장고 속 남은 재료를 입력하면, AI가 당신의 취향에 딱 맞는 특별한 레시피를 제안합니다.</p>", unsafe_allow_html=True)

# 5. Sidebar Options & Diagnostics
st.sidebar.markdown("### 🛠️ AI 셰프 진단")
if is_api_key_valid():
    st.sidebar.success("🟢 API 연결 상태: 정상 작동 중")
else:
    st.sidebar.error("🔴 API 연결 실패: .env 키 확인 필요")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 레시피 맞춤 설정")

# Dropdowns for preferences
category_opt = st.sidebar.selectbox("선호 요리 종류", ["전체", "한식", "양식", "중식", "일식", "기타"])
custom_category = ""
if category_opt == "기타":
    custom_category = st.sidebar.text_input("원하는 요리 종류 직접 입력", placeholder="예: 동남아식, 디저트, 분식")

duration_opt = st.sidebar.selectbox("최대 조리 시간", ["상관없음", "15분 이내", "30분 이내", "1시간 이내"])
difficulty_opt = st.sidebar.selectbox("난이도 선택", ["상관없음", "쉬움", "보통", "어려움"])

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚠️ 알레르기 및 기피 재료")

# Allergies multiselect
ALLERGY_LIST = ["견과류", "갑각류(새우/게 등)", "대두", "유제품", "밀가루", "달걀", "생선", "기타"]
selected_allergies = st.sidebar.multiselect("알레르기 유발 식품 선택", ALLERGY_LIST)

custom_allergies = ""
if "기타" in selected_allergies:
    custom_allergies = st.sidebar.text_input("기타 알레르기 유발 식품 작성", placeholder="예: 메밀, 아보카도, 복숭아")

# Custom exclusions text input
custom_exclusions = st.sidebar.text_input("추가 제외 재료 입력 (쉼표 구분)", placeholder="예: 오이, 당근, 고수")

# 5.5 Check for Allergy/Exclusion conflicts with Refrigerator ingredients
excl_terms = set()
for a in selected_allergies:
    if a == "기타" and custom_allergies.strip():
        for item in custom_allergies.split(","):
            excl_terms.add(item.strip())
    elif a != "기타":
        if "갑각류" in a:
            excl_terms.update(["새우", "게", "랍스터", "크랩", "갑각류"])
        elif "달걀" in a:
            excl_terms.update(["달걀", "계란", "알류"])
        elif "견과류" in a:
            excl_terms.update(["땅콩", "호두", "아몬드", "캐슈넛", "잣", "견과"])
        elif "유제품" in a:
            excl_terms.update(["우유", "치즈", "버터", "크림", "요거트", "유제품"])
        elif "밀가루" in a:
            excl_terms.update(["밀가루", "밀", "식빵", "밀가루"])
        elif "대두" in a:
            excl_terms.update(["대두", "콩", "두부", "된장", "간장"])
        elif "생선" in a:
            excl_terms.update(["생선", "고등어", "연어", "참치", "조기", "갈치"])
        else:
            excl_terms.add(a)

if custom_exclusions.strip():
    for item in custom_exclusions.split(","):
        excl_terms.add(item.strip())

conflicting_ingredients = []
for ing in st.session_state.my_ingredients:
    for term in excl_terms:
        if term and (term in ing or ing in term):
            conflicting_ingredients.append(f"{ing} (제외 설정: {term})")
            break

# 6. Predefined Ingredients Configuration
PREDEFINED_INGREDIENTS = {
    "🥦 채소 & 과일": ["양파", "마늘", "대파", "감자", "당근", "토마토", "버섯", "청양고추", "오이", "애호박", "시금치", "양배추"],
    "🥩 육류 & 계란": ["돼지고기", "소고기", "닭고기", "베이컨", "달걀", "소시지", "스팸"],
    "🐟 수산물": ["새우", "오징어", "고등어", "연어", "바지락", "참치캔"],
    "🧀 유제품 & 가공품": ["치즈", "우유", "버터", "두부", "만두", "떡국떡", "식빵", "햇반"],
    "🍯 소스 & 양념": ["간장", "고추장", "된장", "설탕", "소금", "참기름", "굴소스", "식초", "케첩", "마요네즈", "후추"]
}

# 7. Layout Tabs
tab1, tab2, tab3, tab4 = st.tabs(["🛒 냉장고 채우기", "🍳 AI 레시피 추천", "⭐ 즐겨찾기 보관함", "📚 요리 기록장"])

# --- Tab 1: Refrigerator Setup ---
with tab1:
    st.markdown("### 🥕 냉장고에 재료를 넣어주세요")
    st.write("아래 식재료를 클릭하여 냉장고에 넣거나 직접 텍스트로 추가해 주세요. (선택된 재료는 하이라이트 표시됩니다.)")
    
    # Grid of predefined buttons
    for cat_name, items in PREDEFINED_INGREDIENTS.items():
        st.markdown(f"<div class='category-header'>{cat_name}</div>", unsafe_allow_html=True)
        cols = st.columns(6)
        for idx, item in enumerate(items):
            col = cols[idx % 6]
            is_active = item in st.session_state.my_ingredients
            btn_label = f"✓ {item}" if is_active else item
            
            # CSS helper for rendering active style
            if is_active:
                if col.button(btn_label, key=f"pre_{item}", use_container_width=True, type="primary"):
                    st.session_state.my_ingredients.remove(item)
                    st.rerun()
            else:
                if col.button(btn_label, key=f"pre_{item}", use_container_width=True, type="secondary"):
                    st.session_state.my_ingredients.add(item)
                    st.rerun()

    # Custom text input to add ingredient
    st.markdown("<div class='category-header'>✏️ 기타 재료 직접 입력</div>", unsafe_allow_html=True)
    c_col1, c_col2 = st.columns([5, 1])
    with c_col1:
        custom_ing = st.text_input("목록에 없는 재료를 직접 입력해 주세요. (쉼표로 여러 개 가능)", key="custom_ing_input", placeholder="예: 삼겹살, 낙지, 전복")
    with c_col2:
        st.write(" ")
        st.write(" ")
        if st.button("냉장고에 넣기", use_container_width=True):
            if custom_ing.strip():
                # Process comma separated inputs
                items_to_add = [i.strip() for i in custom_ing.split(",") if i.strip()]
                for it in items_to_add:
                    st.session_state.my_ingredients.add(it)
                st.success(f"{len(items_to_add)}개의 재료를 추가했습니다!")
                time.sleep(0.5)
                st.rerun()

    # Refrigerator shelf view
    st.markdown("### ❄️ 현재 내 냉장고 속 재료 (클릭하여 삭제)")
    if conflicting_ingredients:
        st.warning(f"⚠️ **알레르기 / 기피 재료 감지 경고!**\n\n냉장고에 포함된 아래 식재료들은 알레르기 유발 식품 또는 제외 대상으로 설정되어 있습니다. 레시피 추천 시 조리 과정에서 엄격히 차단되나, 안전을 위해 냉장고에서 제거하시거나 필터를 확인해 주세요:\n\n* {', '.join(conflicting_ingredients)}")
        
    if not st.session_state.my_ingredients:
        st.info("냉장고가 텅 비어 있습니다. 위 버튼들을 클릭하여 식재료를 채워주세요!")
    else:
        # Render each ingredient as a clickable button to delete individually
        ing_list = sorted(list(st.session_state.my_ingredients))
        cols = st.columns(6)
        for idx, ing in enumerate(ing_list):
            col = cols[idx % 6]
            if col.button(f"❌ {ing}", key=f"del_ing_{ing}", use_container_width=True):
                st.session_state.my_ingredients.remove(ing)
                st.rerun()
                
        st.write("")
        # Action buttons
        act_col1, act_col2 = st.columns([2, 10])
        with act_col1:
            if st.button("냉장고 전체 비우기 🗑️", type="secondary", use_container_width=True):
                st.session_state.my_ingredients = set()
                st.rerun()

# --- Tab 2: AI Recipe Recommendation ---
with tab2:
    st.markdown("### 🍽️ AI 셰프 요리 추천")
    
    if not st.session_state.my_ingredients:
        st.warning("먼저 첫 번째 탭에서 냉장고에 재료를 하나 이상 채워 주세요!")
    else:
        st.write("현재 냉장고 재료:", ", ".join(sorted(list(st.session_state.my_ingredients))))
        if conflicting_ingredients:
            st.error(f"🚨 **주의: 알레르기 및 제외 재료가 냉장고에 감지되었습니다!**\n\n* 해당 재료: **{', '.join(conflicting_ingredients)}**\n\n조리과정에서 강제 차단되나, 교차 오염 예방을 위해 냉장고에서 해당 식재료를 빼실 것을 권장합니다.")
            
        # Recommendation trigger button
        if st.button("🍳 AI 셰프에게 추천 요리 부탁하기", type="primary", use_container_width=True):
            loading_quotes = [
                "👩‍🍳 셰프가 냉장고 속 재료들을 꼼꼼하게 들여다보고 있습니다...",
                "🥘 가장 맛있는 한 끼를 위한 재료 궁합을 계산하는 중입니다...",
                "🚫 알레르기 및 기피 성분이 확실하게 배제되었는지 검토하고 있습니다...",
                "🎨 시각적 만족감을 더해줄 요리 플레이팅 스케치를 완성하고 있습니다..."
            ]
            
            with st.spinner("AI 셰프가 요리를 구상 중입니다... 잠시만 기다려 주세요."):
                progress_bar = st.progress(0)
                # Simulating dynamic loader status change
                for i, quote in enumerate(loading_quotes):
                    st.toast(quote, icon="🔥")
                    progress_bar.progress((i + 1) * 25)
                    time.sleep(1.0)
                
                # Prepare customized parameters
                final_category = custom_category if category_opt == "기타" and custom_category.strip() else category_opt
                
                final_allergies = list(selected_allergies)
                if "기타" in final_allergies:
                    final_allergies.remove("기타")
                    if custom_allergies.strip():
                        custom_allergy_items = [a.strip() for a in custom_allergies.split(",") if a.strip()]
                        final_allergies.extend(custom_allergy_items)
                
                # Call Gemini
                result = generate_recipe_from_gemini(
                    ingredients=sorted(list(st.session_state.my_ingredients)),
                    category=final_category,
                    duration=duration_opt,
                    difficulty=difficulty_opt,
                    allergy_list=final_allergies,
                    custom_exclusions=custom_exclusions
                )
                if result and "recipes" in result and not "error" in result:
                    add_to_history(result.get("recipes", []), sorted(list(st.session_state.my_ingredients)))
                st.session_state.recipes_result = result
                st.rerun()
        
        # Show recommended recipes if present
        if st.session_state.recipes_result:
            if "error" in st.session_state.recipes_result:
                st.error(st.session_state.recipes_result["error"])
            else:
                recipes = st.session_state.recipes_result.get("recipes", [])
                if not recipes:
                    st.info("조건에 만족하는 레시피를 찾을 수 없습니다. 필터 옵션을 완화해 보세요.")
                else:
                    st.markdown(f"## 셰프가 제안하는 {len(recipes)}가지 추천 요리")
                    
                    for r_idx, recipe in enumerate(recipes):
                        # Displaying each recipe inside a card layout
                        st.markdown(f"""
                        <div class='recipe-card'>
                            <div class='recipe-title'>🍽️ {recipe.get('title', '추천 요리')}</div>
                            <div>
                                <span class='badge badge-category'>📂 {recipe.get('category', '요리')}</span>
                                <span class='badge badge-time'>⏱️ {recipe.get('cooking_time', '시간 미정')}</span>
                                <span class='badge badge-diff'>📊 난이도: {recipe.get('difficulty', '보통')}</span>
                            </div>
                            <p style='margin-top:12px; font-size:1.1rem; color:#5D6D7E; font-weight:500;'>
                                💡 <em>{recipe.get('summary', '')}</em>
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Left side recipe detail, right side AI generated image
                        det_col, img_col = st.columns([3, 2])
                        
                        with det_col:
                            # Ingredients list
                            st.markdown("<div class='ingredient-section'>", unsafe_allow_html=True)
                            st.markdown(f"**🟢 냉장고에서 가져온 재료:** {', '.join(recipe.get('matching_ingredients', []))}")
                            missing = recipe.get('missing_ingredients', [])
                            if missing:
                                st.markdown(f"**🔴 추가로 필요한 재료:** {', '.join(missing)}")
                            else:
                                st.markdown("**🟢 냉장고 속 재료로만 즉시 완성 가능!**")
                            st.markdown("</div>", unsafe_allow_html=True)
                            
                            # Checklist for missing ingredients
                            if missing:
                                st.write("🛒 **장보기 체크리스트:**")
                                for m_item in missing:
                                    st.checkbox(f"구매 예정: {m_item}", key=f"buy_{r_idx}_{m_item}")
                            
                            # Cooking Steps
                            st.markdown("### 👨‍🍳 조리법 (Cooking Steps)")
                            for step in recipe.get('steps', []):
                                st.markdown(f"<div class='step-item'>{step}</div>", unsafe_allow_html=True)
                                
                            # Chef's Secret Tip
                            if recipe.get('chef_tip'):
                                st.markdown(f"""
                                <div class='chef-tip-box'>
                                    <strong>✨ 셰프의 한 끗 팁:</strong> {recipe.get('chef_tip')}
                                </div>
                                """, unsafe_allow_html=True)
                            
                            st.write("")
                            # Functional buttons
                            btn_cols = st.columns(3)
                            
                            # Favorite toggle
                            is_already_fav = any(f.get('title') == recipe.get('title') for f in st.session_state.favorites)
                            with btn_cols[0]:
                                if is_already_fav:
                                    if st.button("❤️ 즐겨찾기 해제", key=f"fav_btn_{r_idx}", use_container_width=True):
                                        st.session_state.favorites = [f for f in st.session_state.favorites if f.get('title') != recipe.get('title')]
                                        save_favorites(st.session_state.favorites)
                                        st.toast("즐겨찾기가 취소되었습니다.", icon="💔")
                                        st.rerun()
                                else:
                                    if st.button("⭐ 즐겨찾기 저장", key=f"fav_btn_{r_idx}", type="primary", use_container_width=True):
                                        st.session_state.favorites.append(recipe)
                                        save_favorites(st.session_state.favorites)
                                        st.toast("즐겨찾기에 저장되었습니다!", icon="⭐")
                                        st.rerun()
                                        
                            # Export markdown recipe
                            with btn_cols[1]:
                                recipe_md = f"### 🍽️ {recipe.get('title')}\n\n"
                                recipe_md += f"- **카테고리**: {recipe.get('category')}\n"
                                recipe_md += f"- **시간**: {recipe.get('cooking_time')}\n"
                                recipe_md += f"- **난이도**: {recipe.get('difficulty')}\n\n"
                                recipe_md += f"**[재료]**\n"
                                recipe_md += f"- 냉장고 재료: {', '.join(recipe.get('matching_ingredients', []))}\n"
                                recipe_md += f"- 필요한 추가 재료: {', '.join(recipe.get('missing_ingredients', [])) if recipe.get('missing_ingredients') else '없음'}\n\n"
                                recipe_md += f"**[조리법]**\n"
                                for s in recipe.get('steps', []):
                                    recipe_md += f"- {s}\n"
                                recipe_md += f"\n**[셰프의 팁]**\n- {recipe.get('chef_tip')}"
                                
                                st.download_button(
                                    label="📥 레시피 다운로드 (텍스트)",
                                    data=recipe_md,
                                    file_name=f"{recipe.get('title')}_레시피.txt",
                                    mime="text/plain",
                                    key=f"dl_btn_{r_idx}",
                                    use_container_width=True
                                )
                                
                            # Export shopping list
                            with btn_cols[2]:
                                if missing:
                                    shop_list_text = f"🚨 {recipe.get('title')} 장보기 리스트:\n" + "\n".join([f"- [ ] {m}" for m in missing])
                                    st.download_button(
                                        label="📋 장보기 리스트 받기",
                                        data=shop_list_text,
                                        file_name=f"{recipe.get('title')}_장보기목록.txt",
                                        mime="text/plain",
                                        key=f"shop_btn_{r_idx}",
                                        use_container_width=True
                                    )
                                else:
                                    st.button("🟢 바로 조리 가능!", disabled=True, key=f"shop_btn_dis_{r_idx}", use_container_width=True)
                        
                        with img_col:
                            st.write("🍽️ **완성 예상 이미지 (AI 생성)**")
                            eng_title = recipe.get("english_title", "gourmet plate")
                            render_recipe_image(eng_title, r_idx, f"🍽️ {recipe.get('title')} 예시 사진")
                            
                            # Integrated visual cooking timer!
                            st.markdown("---")
                            # Extract suggested time or default to 3 minutes
                            try:
                                time_str = recipe.get("cooking_time", "3분")
                                # Try parsing integer out of e.g. "15분", "20분 이내"
                                parsed_time = 3
                                for chunk in time_str.split():
                                    num_only = "".join(filter(str.isdigit, chunk))
                                    if num_only:
                                        parsed_time = int(num_only)
                                        break
                            except Exception:
                                parsed_time = 3
                                
                            timer_html = f"""
                            <div style="font-family: 'Noto Sans KR', Arial, sans-serif; text-align: center; background-color: #FFF2E6; padding: 15px; border-radius: 12px; border: 1px solid #FFD3B6; margin-top: 15px;">
                                <h4 style="margin: 0 0 5px 0; color: #D35400; font-size: 1.1rem;">⏱️ 실시간 요리 타이머</h4>
                                <div id="display-{r_idx}" style="font-size: 2.2em; font-weight: bold; color: #2C3E50; margin: 10px 0;">{parsed_time:02d}:00</div>
                                <div style="margin-top: 10px; display: flex; justify-content: center; gap: 8px;">
                                    <button id="startBtn-{r_idx}" style="background-color: #E67E22; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.9rem;">시작</button>
                                    <button id="pauseBtn-{r_idx}" style="background-color: #7F8C8D; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.9rem;">정지</button>
                                    <button id="resetBtn-{r_idx}" style="background-color: #E74C3C; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.9rem;">리셋</button>
                                </div>
                            </div>
                            <script>
                                (function() {{
                                    let timerId;
                                    let totalSeconds = {parsed_time} * 60;
                                    let timeLeft = totalSeconds;
                                    let isRunning = false;
                                    
                                    const display = document.getElementById('display-{r_idx}');
                                    const startBtn = document.getElementById('startBtn-{r_idx}');
                                    const pauseBtn = document.getElementById('pauseBtn-{r_idx}');
                                    const resetBtn = document.getElementById('resetBtn-{r_idx}');
                                    
                                    function fmt(val) {{
                                        return val < 10 ? '0' + val : val;
                                    }}
                                    
                                    function updateDisplay() {{
                                        let mins = Math.floor(timeLeft / 60);
                                        let secs = timeLeft % 60;
                                        display.innerText = fmt(mins) + ':' + fmt(secs);
                                    }}
                                    
                                    startBtn.addEventListener('click', () => {{
                                        if (isRunning) return;
                                        isRunning = true;
                                        timerId = setInterval(() => {{
                                            if (timeLeft > 0) {{
                                                timeLeft--;
                                                updateDisplay();
                                            }} else {{
                                                clearInterval(timerId);
                                                isRunning = false;
                                                alert('🔔 【{recipe.get("title")}】 조리 시간이 다 되었습니다! 맛있는 요리를 확인해 보세요.');
                                            }}
                                        }}, 1000);
                                    }});
                                    
                                    pauseBtn.addEventListener('click', () => {{
                                        clearInterval(timerId);
                                        isRunning = false;
                                    }});
                                    
                                    resetBtn.addEventListener('click', () => {{
                                        clearInterval(timerId);
                                        isRunning = false;
                                        timeLeft = totalSeconds;
                                        updateDisplay();
                                    }});
                                }})();
                            </script>
                            """
                            st.components.v1.html(timer_html, height=170)
                        
                        st.markdown("<hr style='border: 1px solid #F2F4F4;'>", unsafe_allow_html=True)

# --- Tab 3: Favorites Repository ---
with tab3:
    st.markdown("### ⭐ 내가 저장한 즐겨찾기 레시피")
    
    if not st.session_state.favorites:
        st.info("아직 즐겨찾기에 추가한 레시피가 없습니다. AI 레시피 추천 탭에서 마음에 드는 요리를 별표(⭐)하여 저장해 보세요!")
    else:
        st.write(f"현재 보관 중인 요리: {len(st.session_state.favorites)}개")
        
        # Selecting which favorited recipe to look at
        fav_titles = [f.get('title') for f in st.session_state.favorites]
        selected_fav_title = st.selectbox("보관함 요리 선택", fav_titles)
        
        if selected_fav_title:
            # Find selected favorite recipe details
            fav_recipe = next((f for f in st.session_state.favorites if f.get('title') == selected_fav_title), None)
            
            if fav_recipe:
                st.markdown(f"""
                <div class='recipe-card'>
                    <div class='recipe-title'>🍽️ {fav_recipe.get('title')}</div>
                    <div>
                        <span class='badge badge-category'>📂 {fav_recipe.get('category')}</span>
                        <span class='badge badge-time'>⏱️ {fav_recipe.get('cooking_time')}</span>
                        <span class='badge badge-diff'>📊 난이도: {fav_recipe.get('difficulty')}</span>
                    </div>
                    <p style='margin-top:12px; font-size:1.1rem; color:#5D6D7E; font-weight:500;'>
                        💡 <em>{fav_recipe.get('summary')}</em>
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                f_det_col, f_img_col = st.columns([3, 2])
                
                with f_det_col:
                    # Ingredients
                    st.markdown("<div class='ingredient-section'>", unsafe_allow_html=True)
                    st.markdown(f"**🟢 매칭 재료:** {', '.join(fav_recipe.get('matching_ingredients', []))}")
                    f_missing = fav_recipe.get('missing_ingredients', [])
                    if f_missing:
                        st.markdown(f"**🔴 추가 필요 재료:** {', '.join(f_missing)}")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Steps
                    st.markdown("### 👨‍🍳 조리법 (Cooking Steps)")
                    for step in fav_recipe.get('steps', []):
                        st.markdown(f"<div class='step-item'>{step}</div>", unsafe_allow_html=True)
                        
                    # Tip
                    if fav_recipe.get('chef_tip'):
                        st.markdown(f"""
                        <div class='chef-tip-box'>
                            <strong>✨ 셰프의 한 끗 팁:</strong> {fav_recipe.get('chef_tip')}
                        </div>
                        """, unsafe_allow_html=True)
                        
                    # Remove button
                    st.write("")
                    if st.button("💔 즐겨찾기 목록에서 삭제", type="secondary"):
                        st.session_state.favorites = [f for f in st.session_state.favorites if f.get('title') != selected_fav_title]
                        save_favorites(st.session_state.favorites)
                        st.toast("보관함에서 삭제되었습니다.", icon="💔")
                        st.rerun()
                        
                with f_img_col:
                    st.write("🍽️ **요리 완성 예상 이미지**")
                    f_eng_title = fav_recipe.get("english_title", "gourmet plate")
                    render_recipe_image(f_eng_title, 99, f"🍽️ {fav_recipe.get('title')} 예시 사진 (AI 재현)")

# --- Tab 4: Cooking History ---
with tab4:
    st.markdown("### 📚 요리 추천 기록장")
    sub_tab_hist, sub_tab_trash = st.tabs(["📋 추천 기록 내역", "🗑️ 휴지통"])
    
    with sub_tab_hist:
        history_data = load_history()
        
        if not history_data:
            st.info("아직 생성된 요리 추천 기록이 없습니다. AI 레시피 추천 탭에서 요리를 추천받아 보세요!")
        else:
            st.write(f"총 {len(history_data)}번의 요리 추천 기록이 있습니다.")
            
            # Group list by date
            for idx, entry in enumerate(history_data):
                timestamp = entry.get("timestamp", "시간 미정")
                ingredients_used = ", ".join(entry.get("ingredients", []))
                recipes_list = entry.get("recipes", [])
                recipe_names = ", ".join([r.get("title", "추천 요리") for r in recipes_list])
                
                # Expander for each generation event
                label = f"📅 {timestamp} | {recipe_names} (재료: {ingredients_used})"
                with st.expander(label):
                    st.markdown(f"**⏰ 기록 시간:** `{timestamp}`")
                    st.markdown(f"**🥕 당시 냉장고 재료:** {ingredients_used}")
                    st.markdown("---")
                    
                    # Render each recipe of this event
                    for r_idx, r in enumerate(recipes_list):
                        st.markdown(f"#### 🍽️ {r.get('title')} ({r.get('category')})")
                        st.write(f"⏱️ **소요 시간:** {r.get('cooking_time')} | 📊 **난이도:** {r.get('difficulty')}")
                        st.write(f"💡 *{r.get('summary')}*")
                        
                        st.markdown("**조리 순서:**")
                        for step in r.get('steps', []):
                            st.write(f"- {step}")
                        
                        if r.get('chef_tip'):
                            st.markdown(f"""
                            <div class='chef-tip-box'>
                                <strong>✨ 셰프의 한 끗 팁:</strong> {r.get('chef_tip')}
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.write("")
                        h_fav_col, h_img_col = st.columns([3, 2])
                        
                        with h_fav_col:
                            # Check if already favorited
                            is_already_fav = any(f.get('title') == r.get('title') for f in st.session_state.favorites)
                            if is_already_fav:
                                st.info("⭐ 이미 즐겨찾기에 보관 중인 요리입니다.")
                            else:
                                if st.button("⭐ 이 요리 즐겨찾기에 저장", key=f"hist_fav_{idx}_{r_idx}", use_container_width=True):
                                    st.session_state.favorites.append(r)
                                    save_favorites(st.session_state.favorites)
                                    st.toast(f"'{r.get('title')}' 요리가 즐겨찾기에 저장되었습니다!", icon="⭐")
                                    st.rerun()
                        
                        with h_img_col:
                            with st.expander("🖼️ 요리 완성 사진 보기"):
                                eng_title = r.get("english_title", "gourmet plate")
                                render_recipe_image(eng_title, f"{idx}_{r_idx}", f"🍽️ {r.get('title')} 예시 사진")
                                
                        st.markdown("<hr style='border: 1px dashed #E2E4E4;'>", unsafe_allow_html=True)
                    
                    # Individual delete button
                    if st.button("🗑️ 이 기록 삭제 (휴지통으로 이동)", key=f"del_hist_single_{idx}", use_container_width=True):
                        # Remove from history
                        new_hist = [h for h in history_data if h.get("timestamp") != entry.get("timestamp")]
                        save_history(new_hist)
                        # Add to trash
                        move_to_trash(entry)
                        st.toast("기록이 휴지통으로 이동했습니다.", icon="🗑️")
                        st.rerun()
            
            st.write("")
            # Action button to clear history (moves to trash)
            if st.button("기록 전체 삭제 (휴지통으로 이동) 🗑️", type="secondary", key="clear_all_history_btn", use_container_width=True):
                trash = load_trash()
                import datetime
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for entry in history_data:
                    entry["deleted_at"] = now_str
                    trash.insert(0, entry)
                save_trash(trash)
                save_history([])
                st.success("모든 요리 추천 기록이 휴지통으로 이동했습니다.")
                time.sleep(0.5)
                st.rerun()

    with sub_tab_trash:
        st.markdown("### 🗑️ 삭제된 요리 추천 기록")
        trash_data = load_trash()
        
        if not trash_data:
            st.info("휴지통이 비어 있습니다. 삭제된 기록이 여기에 보관됩니다.")
        else:
            st.write(f"휴지통에 {len(trash_data)}개의 기록이 보관되어 있습니다.")
            
            # Action buttons for all trash
            t_col1, t_col2 = st.columns([1, 1])
            with t_col1:
                if st.button("♻️ 휴지통 전체 복원", type="primary", key="restore_all_trash", use_container_width=True):
                    history_data = load_history()
                    # Add trash items back
                    for entry in trash_data:
                        if "deleted_at" in entry:
                            del entry["deleted_at"]
                        history_data.insert(0, entry)
                    
                    history_data.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                    save_history(history_data)
                    save_trash([])
                    st.success("모든 기록이 정상 복원되었습니다!")
                    time.sleep(0.5)
                    st.rerun()
                    
            with t_col2:
                if st.button("💥 휴지통 완전히 비우기 (영구 삭제)", type="secondary", key="empty_all_trash", use_container_width=True):
                    save_trash([])
                    st.success("휴지통이 완전히 비워졌습니다.")
                    time.sleep(0.5)
                    st.rerun()
            
            st.markdown("---")
            
            # List deleted items
            for t_idx, entry in enumerate(trash_data):
                timestamp = entry.get("timestamp", "시간 미정")
                deleted_at = entry.get("deleted_at", "시간 미정")
                ingredients_used = ", ".join(entry.get("ingredients", []))
                recipes_list = entry.get("recipes", [])
                recipe_names = ", ".join([r.get("title", "추천 요리") for r in recipes_list])
                
                label = f"🗑️ {recipe_names} (삭제일시: {deleted_at})"
                with st.expander(label):
                    st.markdown(f"**⏰ 기록 시간:** `{timestamp}`")
                    st.markdown(f"**🗑️ 삭제 시간:** `{deleted_at}`")
                    st.markdown(f"**🥕 당시 냉장고 재료:** {ingredients_used}")
                    st.markdown("---")
                    
                    for r in recipes_list:
                        st.markdown(f"##### 🍽️ {r.get('title')} ({r.get('category')})")
                        st.write(f"⏱️ **소요 시간:** {r.get('cooking_time')} | 📊 **난이도:** {r.get('difficulty')}")
                    
                    st.write("")
                    op_col1, op_col2 = st.columns([1, 1])
                    with op_col1:
                        if st.button("♻️ 이 기록 복원", key=f"restore_single_{t_idx}", use_container_width=True):
                            history_data = load_history()
                            if "deleted_at" in entry:
                                del entry["deleted_at"]
                            history_data.insert(0, entry)
                            history_data.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                            save_history(history_data)
                            
                            new_trash = [t for t in trash_data if t.get("timestamp") != entry.get("timestamp")]
                            save_trash(new_trash)
                            st.toast("기록이 복원되었습니다.", icon="♻️")
                            st.rerun()
                            
                    with op_col2:
                        if st.button("❌ 영구 삭제", key=f"purge_single_{t_idx}", use_container_width=True):
                            new_trash = [t for t in trash_data if t.get("timestamp") != entry.get("timestamp")]
                            save_trash(new_trash)
                            st.toast("기록이 영구 삭제되었습니다.", icon="❌")
                            st.rerun()

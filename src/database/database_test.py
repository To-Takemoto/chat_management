import os
from supabase import create_client, Client

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_API_KEY")
password: str = os.environ.get("SUPABASE_PASSWORD")
supabase: Client = create_client(url, key)


# USERテーブルのデータを全て取得する
async def get_user():
    response = supabase.table("USER").select("*").execute()
    return response


# PersonalStatementScoringLogテーブルのデータを全て取得する
async def get_ps_log():
    response = supabase.table("PersonalStatementScoringLog").select("*").execute()
    return response

# アカウントを登録する 同じLINE_IDが存在する場合は登録しない
async def create_user(line_id: str, line_name: str) -> tuple|str:
    try:
        data, count = (
            supabase.table("USER")
            .insert({"LINE_ID": line_id, "LINE_NAME": line_name})
            .execute()
        )
        return data, count
    except:
        return "user_already_exist"



# 志望理由書採点準備
# 引数で与えられたLINE_IDが存在すれば、そのIDのURL_STATE	SCORING_STATE	SCORING_MODEをそれぞれURL待機中	採点準備中	志望理由書にする
async def prepare_ps_scoring(line_id: str):
    user = await get_user()
    for i in user:
        if i["LINE_ID"] == line_id:
            data, count = (
                supabase.table("USER")
                .update(
                    {
                        "URL_STATE": "URL待機中",
                        "SCORING_STATE": "採点準備中",
                        "SCORING_MODE": "志望理由書",
                    }
                )
                .eq("LINE_ID", line_id)
                .execute()
            )
            return data, count
    return "User not found"


# 志望理由書URL登録
# 引数で与えられたLINE_IDがUSERに存在すれば、PersonalStatementScoringLogで新しい行を作成し、LINE_IDとDOCS_URLを登録する
# また、USERのURL_STATEをURL登録済みに、SCORING_STATEを採点待機中にする
async def register_ps_url(line_id: str, docs_url: str):
    user = await get_user()
    for i in user:
        if i["LINE_ID"] == line_id:
            data, count = (
                supabase.table("PersonalStatementScoringLog")
                .insert({"LINE_ID": line_id, "DOCS_URL": docs_url})
                .execute()
            )
            data, count = (
                supabase.table("USER")
                .update({"URL_STATE": "URL登録済み", "SCORING_STATE": "採点待機中"})
                .eq("LINE_ID", line_id)
                .execute()
            )
            return data, count
    return "User not found"


# 志望理由書の採点を開始する
# 引数で与えられたLINE_IDがUSERに存在すれば、PersonalStatementScoringLogで新しい行を作成し、LINE_IDとDOCS_URLを登録する
# また、USERのURL_STATEをURL登録済みに、SCORING_STATEを採点中にする
async def start_ps_scoring(line_id: str, docs_url: str):
    user = await get_user()
    for i in user:
        if i["LINE_ID"] == line_id:
            data, count = (
                supabase.table("PersonalStatementScoringLog")
                .insert({"LINE_ID": line_id, "DOCS_URL": docs_url})
                .execute()
            )
            data, count = (
                supabase.table("USER")
                .update({"URL_STATE": "URL登録済み", "SCORING_STATE": "採点中"})
                .eq("LINE_ID", line_id)
                .execute()
            )
            return data, count
    return "User not found"


# 志望理由書の採点を記録する
# 引数にLINE_NAME	LINE_ID	DOCS_URL	SelfPromotion	SelfPromotionLogic	StudyPlan	StudyPlanLogic	Vision	VisionLogic	OverallScore ScoreDictを受け取り、PersonalStatementScoringLogに登録する
async def record_ps_scoring(
    line_name: str,
    line_id: str,
    docs: str,
    self_promotion: str,
    self_promotion_logic: str,
    study_plan: str,
    study_plan_logic: str,
    vision: str,
    vision_logic: str,
    overall_score: str,
    score_dict: str,
):
    data, count = (
        supabase.table("PersonalStatementScoringLog")
        .insert(
            {
                "LINE_NAME": line_name,
                "LINE_ID": line_id,
                "DOCS_URL": docs,
                "SelfPromotion": self_promotion,
                "SelfPromotionLogic": self_promotion_logic,
                "StudyPlan": study_plan,
                "StudyPlanLogic": study_plan_logic,
                "Vision": vision,
                "VisionLogic": vision_logic,
                "OverallScore": overall_score,
                "ScoreDict": score_dict,
            }
        )
        .execute()
    )
    return data, count


# 小論文の採点を記録する
# 引数にLINE_NAME	LINE_ID	DATE	DOCS_URL	QuestionsUnderstanding	Logic	Persuasiveness	Consistency	Readability	OverallScore	ScoreDictを受け取り、EssayScoringLogに登録する
async def record_es_scoring(
    line_name: str,
    line_id: str,
    docs: str,
    questions_understanding: str,
    logic: str,
    persuasiveness: str,
    consistency: str,
    readability: str,
    overall_score: str,
    score_dict: str,
):
    data, count = (
        supabase.table("EssayScoringLog")
        .insert(
            {
                "LINE_NAME": line_name,
                "LINE_ID": line_id,
                "DOCS_URL": docs,
                "QuestionsUnderstanding": questions_understanding,
                "Logic": logic,
                "Persuasiveness": persuasiveness,
                "Consistency": consistency,
                "Readability": readability,
                "OverallScore": overall_score,
                "ScoreDict": score_dict,
            }
        )
        .execute()
    )
    return data, count

async def set_user_state(user_id: str, state: str):
    data, count = (
        supabase.table("USER")
        .update({"SCORING_STATE": state})
        .eq("LINE_ID", user_id)
        .execute()
    )
    return data, count

async def get_user_state(user_id: str) -> str:
    response = supabase.table("USER").select("SCORING_STATE").eq("LINE_ID", user_id).execute()
    if response.data:
        return response.data[0]["SCORING_STATE"]
    return None

async def clear_user_state(user_id: str):
    data, count = (
        supabase.table("USER")
        .update({"SCORING_STATE": None, "SCORING_MODE": None})
        .eq("LINE_ID", user_id)
        .execute()
    )
    return data, count

async def save_essay_question(user_id: str, question: str):
    data, count = (
        supabase.table("USER")
        .update({"ESSAY_QUESTION": question})
        .eq("LINE_ID", user_id)
        .execute()
    )
    return data, count

async def get_essay_question(user_id: str) -> str:
    response = supabase.table("USER").select("ESSAY_QUESTION").eq("LINE_ID", user_id).execute()
    if response.data:
        return response.data[0]["ESSAY_QUESTION"]
    return None

async def main():
    data = await create_user("test_user_id_2", "こんんちは")
    print(data)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

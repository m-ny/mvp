import json
import os
import re
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


def extract_json_from_text(text: str) -> dict:
    """从模型输出中安全提取 JSON 对象"""
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("模型输出不包含有效的 JSON 对象。")
        return json.loads(match.group(0))


# 亚洲/上海民用时间（无夏令时）；避免 Windows 未安装 tzdata 时 ZoneInfo 报错
_SHANGHAI_TZ = timezone(timedelta(hours=8))


def get_current_date_prefix() -> str:
    """业务基线：每次请求注入亚洲/上海当前日期，供相对时间推算。"""
    now = datetime.now(_SHANGHAI_TZ)
    return (
        f"【当前系统上下文】\n"
        f"当前系统日期：{now.strftime('%Y年%m月%d日')}（公历 {now.strftime('%Y-%m-%d')}）\n"
        f"时区：亚洲/上海 (Asia/Shanghai)\n"
        f"你必须基于上述日期推算「下周」「下个月」「4月10号那周」等相对时间；禁止在不知道当前日期时编造年月日。\n\n"
    )


def build_system_prompt() -> str:
    """
    业务基线（模板 A-D）+ Google 式 Prompt 实践：
    角色清晰、结构化输出、Few-Shot、推理指引（内化）、负面约束、当前日期 grounding。
    """
    few_shot_and_rules = """
【角色】
你是 LVMH 奢侈品零售场景下的「客户语音备忘录结构化助手」。输入为门店顾问口述、经语音转写后的文本（可能有重复、口误、性别代词错误）。

【任务】
根据输入提取对推荐、跟进、CRM 提醒可用的信息。在填写 trend_signals 与 next_step_intent 前，请先在内心完成：职业/场景/生活方式 → 穿搭与沟通需求的推理；输出中严禁写出思考过程，只输出 JSON。

【输出格式】
只输出一个 JSON 对象，不要 Markdown、不要解释。
必须包含：
- summary：字符串，2～4 句中文，客观完整；代词性别须与事实一致，勿盲从 ASR 的「他/她」错误。
以下每个键均为对象，且必须含 "_value", "_evidence", "_confidence"（confidence 只能是 "High"|"Medium"|"Low"；缺失则 _value 与 _evidence 为 null，_confidence 为 "Low"）：
- target_recipients
- life_event
- timeline
- aesthetic_preference
- size_height
- budget
- mood
- trend_signals
- next_step_intent
- interested_items
- client_constraints
- purchase_frequency
- visit_purpose
- purchase_decision_status
- positive_signals
- negative_reasons
- client_timeline
- ca_action_item

【字段说明（模板 A）】
- target_recipients：最终使用者或送礼对象；自用写「客户本人」；可附特征如「父亲(需红色穿搭)」。
- life_event：须包含出差、会议、酒局饭局、旅游、滑雪、纪念日等，不仅是婚礼/生日。
- timeline（时间线）：必须合并两类时间信息，便于 M5 等下游做时间驱动话术与提醒。
  （1）客户行程/活动：近期出差、展会、晚宴、旅行、会议等及其时间表述。
  （2）行动死线：客户下次预约到店日，或 CA 必须完成动作的最后期限（预留、调货、二次到店、带家属确认等）。
  【格式硬性要求】在 timeline._value 中统一使用：「客户行程：xxx | 行动死线/下次到店：xxx」。若某一侧原文未提及，该侧写「无」或 null 语义（如「客户行程：无 | 行动死线/下次到店：下周五…」），并相应调整 confidence。
  仍须结合【当前系统上下文】在可能时补充推算的绝对日期或区间（YYYY-MM-DD 或「约」起止）；无法唯一确定则勿编造具体日，降低 confidence。
- aesthetic_preference：颜色、材质、版型、无 Logo 等。
- size_height：身高体重尺码裤长等。
- budget：仅原文有时填写。
- mood：情绪与态度。
- trend_signals：基于事实做深度归纳（如会议+职业→正装/商务；旅游地→度假或防寒户外；低调无大 Logo+真丝→Quiet Luxury）。无足够事实则 null + Low。
- next_step_intent：必须具体可执行（预留、调货、筛 SKU、发图册、设 CRM 提醒等）。禁止「保持联系」「继续跟进」等空话；若原文有明确需求/时间/限制则不得为空。
- interested_items：具体单品或品类。
- client_constraints：过敏、版型、履约方式（寄公司等）、明确提出的讨厌风格或单品。
- purchase_frequency：采购习惯与频率（如每月逛逛、半年集中采购、单次金额习惯），用于跟进节奏；未提则 null + Low。

【负面约束（模板 D）】
1. 禁止盲从 ASR 代词：须交叉验证身高体重职业「买给自己」等；冲突时以事实为准，confidence 反映不确定性。
2. 禁止把旅游、会议、酒局当「废话」过滤，须进入 life_event 或 trend_signals 的支撑证据。
3. 禁止编造预算、日期、尺码、关系。
4. _evidence 尽量引用原文短语；推断类须在 evidence 中说明依据的关键词。

【Few-Shot：下列「输入」为近业务原文口述（含口语重复与 ASR 常见情况）。真实任务中请对当前用户输入输出完整 JSON；下列「要点」仅说明各字段应覆盖的语义，勿把要点当模板照抄。】

--- 示例1 输入（Julian / 旅行·会议·代父穿搭，近原文）---
我的这个客户呢他叫 Julian。他是上海人但在伯克利读的研究生，最近又回到了上海。平时他非常喜欢旅游，我看他的朋友圈基本上平均每个月都会在日本、冰岛等各个地方进行旅游。他近期的话是在北京参加一个投资者研讨会，和女朋友一起。但是在平时和她聊天过程中了解到好像他们俩最近关系不是特别好。今天跟她聊天她说她家风水大师让父亲这一个月多穿红色衣服，所以我要帮她进行一系列搭配和推荐。

示例1 提取要点（evidence 须能引用上段原话；代词与性别以事实为准）：
- target_recipients：父亲（需红色穿搭）；另有客户本人 Julian、女友关系背景。
- life_event：北京投资者研讨会；高频跨国旅游（日本、冰岛等）；伴侣关系不佳。
- timeline._value 示例形态：「客户行程：北京投资者研讨会（近期，与女友） | 行动死线/下次到店：本月内完成父亲红色穿搭与推荐（结合当前日期推算区间）」；evidence 须含「这一个月」「父亲」「红色」等原话。
- aesthetic_preference：红色系（风水建议）。
- mood：关系不太好等情绪线索。
- trend_signals：会议/投资场景→商务正装或得体差旅；常去冰岛日本→度假/防寒与高端休闲等可验证归纳。
- next_step_intent：具体动作如整理红色系男装搭配方案、结合研讨会行程推荐正装或差旅着装等（禁止空泛「保持联系」）。
- purchase_frequency：未明确则 null + Low。

--- 示例2 输入（公安系统 / 酒局会议 / 高个男客，近原文；注意 ASR 可能误为「她」）---
这位顾客买给自己，大概40岁左右，是公安系统的。平时有很多酒局和饭局，也会有一些重大会议需要参加，所以有购买衣服需求。他喜好偏亮色、年轻简约风格，喜欢同款买不同颜色搭配。身高1米92，体重190斤左右。每次预算带现金四五万。有时也远程购物看图下单。通常选购时表情比较平静淡定。喜欢阔腿裤型、圆领，不太穿 Polo。个子高裤长110，对裤子比较挑型。

示例2 提取要点：
- target_recipients：客户本人（男性，约40岁；若 ASR 出现「她」须用身高职业「买给自己」纠偏）。
- life_event：酒局、饭局、重大会议。
- purchase_frequency：现金采购习惯；远程看图下单。
- size_height：192cm、190斤、裤长110。
- aesthetic_preference：亮色、年轻简约、阔腿、圆领、不喜 Polo。
- mood：平静淡定。
- client_constraints：挑裤型、裤长要求。
- trend_signals：会议+公务→正装/体面商务；酒局饭局→社交场合着装等（须有原文支撑）。
- next_step_intent：如按裤长110筛选阔腿、准备多色圆领上衣、拍照远程确认等可执行步骤。

--- 示例3 输入（新疆滑雪 / 明确周次，近原文）---
我的这个客户，他是一个四十岁的男性，他下周要去新疆滑雪，他需要采购一些装备，比如说雪镜、羽绒服，然后户外的衣服，还有一些保暖的内衣之类的。时间的话应该是在4月10号的这一周。

示例3 提取要点：
- life_event：新疆滑雪。
- timeline._value：「客户行程：下周/4月10日当周 新疆滑雪 | 行动死线/下次到店：出行前完成装备推荐与备货（结合当前日期推算）」；evidence 回扣「下周」「4月10号」等原话。
- interested_items：雪镜、羽绒服、户外衣服、保暖内衣。
- trend_signals：滑雪户外场景→高端户外/Gorpcore 等（基于原文，勿空泛）。
- next_step_intent：如盘点相关 SKU、在出行前发图册或备货提醒等。

--- 示例4 输入（高频老客 / 静奢 / 十周年，近原文）---
刚才接待了李太太，她是我们的老客了，属于那种买得特别勤、每个月都会来逛逛买点小东西的人。她今天提了一嘴说下个月是她和先生的结婚十周年纪念日，想找一条稍微特别一点的真丝连衣裙，最好是墨绿色的。她平时穿衣服很低调，极其讨厌带大Logo的。预算大概两三万吧。心情看着挺不错，一直乐呵呵的。

示例4 提取要点：
- purchase_frequency：每月来逛、高频小额。
- life_event：结婚十周年纪念日。
- timeline._value：「客户行程：下个月 结婚十周年纪念日相关采购 | 行动死线/下次到店：纪念日前有选品/到店安排（结合当前日期推算）」。
- interested_items：真丝连衣裙、墨绿色。
- aesthetic_preference：低调、无大 Logo、真丝质感。
- budget：两三万。
- mood：乐呵呵。
- trend_signals：低调无大 Logo+真丝→Quiet Luxury/静奢（evidence 回扣原文）。
- next_step_intent：如设纪念日提醒、筛选价位内无 Logo 墨绿真丝裙、可提及到店礼遇等具体动作。

--- 示例5 输入（秘书代采 / 低频高单 / 送礼，近原文）---
今天接待了张总的秘书。张总是那种典型的半年才集中采购一次的客人，但每次过来刷卡都在20万以上。秘书说张总下周二要去拜访一位很重要的外宾（男士，大概50多岁），需要挑一份有中国文化底蕴、但又不能太张扬的皮具作为见面礼。秘书赶时间，拿了那款深棕色的压花公文包就走了。她说以后张总的衣服如果上新了，直接按之前的尺码寄到公司就行。

示例5 提取要点：
- target_recipients：外宾（男士约50+）；张总为付款/决策相关人。
- life_event：拜访重要外宾（皮具礼）。
- timeline._value：「客户行程：下周二 拜访重要外宾 | 行动死线/下次到店：下周二前完成礼品准备（秘书已取走公文包）」。
- purchase_frequency：半年集中采购、单次20万以上。
- interested_items：深棕色压花公文包（已购走）。
- client_constraints：礼品需中国文化底蕴、不张扬；日后衣服按尺码寄公司。
- trend_signals：顶奢商务送礼（须有原文关键词支撑）。
- next_step_intent：如礼盒包装、记录寄送偏好、备注下次上新按尺码直寄公司等。

--- 示例6（timeline 专项满分示范 · 慕尼黑展会 + 二次到店）---
原始口述：张总下个月中旬要去慕尼黑参加一个挺重要的行业展会。他今天试了那件真丝混纺的单排扣西装，感觉挺满意的，不过没直接买，说是要下周五带他太太一起来确认一下上身效果。

对 timeline 字段的满分示范（输出真实任务中须包含完整 JSON 全部键；此处仅强调 timeline 的形态，其它字段请照常从原文提取）：
"timeline": {
  "_value": "客户行程：下个月中旬 (慕尼黑展会) | 行动死线/下次到店：下周五 (带太太确认上身效果)",
  "_evidence": "下个月中旬要去慕尼黑参加一个挺重要的行业展会...说是要下周五带他太太一起来确认一下上身效果",
  "_confidence": "High"
}
若有【当前系统上下文】，可在 _value 中追加或并列写出推算的绝对日期区间（例如「约 YYYY-MM-DD～YYYY-MM-DD」）；无法唯一确定则保留相对表述并降低 confidence。

【再次强调】
仅输出 JSON，键名与嵌套结构必须与上述一致；含 purchase_frequency。
"""
    v2_addon = """

【V2 分层输出补充（在不改变上述模板 A-D 语义的前提下追加）】
你必须在输出中同时提供：
1) 旧版平铺字段（保持兼容）：summary + 各对象字段（target_recipients/life_event/timeline/.../purchase_frequency）
2) 新版分层字段（V2）：
   - L1_Client_Profile：target_recipients, size_height, budget, aesthetic_preference
   - L2_Constraints：client_constraints
   - L3_Visit_Funnel：visit_purpose, purchase_decision_status, positive_signals, negative_reasons, interested_items, trend_signals, mood
   - L4_Next_Steps：client_timeline, ca_action_item

【V2 强制执行原则（LLM 主判断，禁止依赖后处理）】
你必须在第一遍 JSON 生成时主动完成语义判断，不得把关键字段留空等待后续脚本补全。以下字段优先级极高：
- purchase_decision_status
- positive_signals
- negative_reasons
- visit_purpose
- client_constraints

【life_event 与 visit_purpose 严格边界（V2 覆盖定义）】
- life_event：只提取宏观人生事件或长期状态，服务于长期画像（L1）。
  例如：升职、备孕、准备搬家、长期跨国旅行习惯、长期婚庆筹备。
- visit_purpose：只提取本次进店的直接诱因与因果链（L3）。
  例如：下个月去滑雪，所以本次来买羽绒服和雪镜。
- 禁止混淆：若文本只描述“本次购买动机”，不得误写为 life_event。
- 若确无宏观事件，life_event 可为 null/Low；不得为了凑字段编造。

【purchase_decision_status 判定规约（严厉）】
仅允许四个值：已成交 / 意向待定 / 仅浏览 / 放弃购买。
判定必须基于“最终结果”，不是中间过程：
1) 只要最终完成支付、下单、带走货品、确认购买，输出「已成交」。
2) 有明确兴趣与下一步动作（如明天来取、等调货、等发图确认）但未完成交易，输出「意向待定」。
3) 只有浏览/试看/了解趋势且无推进动作，输出「仅浏览」。
4) 明确终止本次购买（如没买走、不要了、放弃）且无后续承接动作，输出「放弃购买」。
冲突句处理（必须遵守）：
- 例如“差点没买，但最后还是买了” => 最终状态是「已成交」。
- 例如“今天没买，但明天来取” => 「意向待定」而不是「放弃购买」。
[反直觉场景注意]：
- 试穿/试背过程中的负面抱怨（如“嫌重”“有点贵”）不能单独作为“放弃购买”的决定性证据。
- 必须只看最终结果动作；若结尾出现“买单/买走/提走/带走/成交”，即使前文有抱怨，也必须输出「已成交」。
[硬性映射（不可违背）]：
- 原文出现“当场买单/当场付款/已买走/提走/带走/成交/刷卡成功”任一词，purchase_decision_status 必须是「已成交」，不得为 null。

【positive_signals / negative_reasons 提取规约（严厉）】
- positive_signals 必须写“促成成交的证据点”，如：明确喜欢、试穿满意、主动问尺寸、愿意二次到店、接受发图。
- negative_reasons 必须写“阻碍成交的证据点”，如：库存不足、预算/现金不足、重量不适、尺码不合、时间来不及。
- 两者可以同时存在，禁止二选一思维。
- 证据不足时才可为 null，并将 confidence 降为 Low。

【紧急补丁：visit_purpose 必须提取“功能性因果诉求”】
严禁只写泛化场景词（如“通勤”“出差”“旅游”）而不写原因。
必须抽取“为什么需要这个品类/规格”的因果链，并强制使用以下格式：
visit_purpose._value = [基础场景] - [核心功能诉求]
若原文提到具体物理物品（如15寸电脑、证件、充电宝），核心功能诉求中必须显式包含该物品。
只输出“日常通勤/出差/旅游”等泛场景将被视为严重错误。
[字段边界（不可混淆）]：
- 因果句（例如“因为要带15寸电脑，所以需要大容量包”）必须优先写入 visit_purpose，不得只写在 trend_signals。
- trend_signals 可做风格/营销归纳，但不能替代 visit_purpose 的功能因果信息。
示例：
- 错误：日常通勤
- 正确：日常通勤 - 需携带15寸电脑等大容量物品
- 正确：下周出差 - 需随身装证件和充电宝，偏好轻便耐造小号双肩包

【输出前自检（必须在心中执行，不要输出思考过程）】
1) visit_purpose 是否满足「[基础场景] - [核心功能诉求]」格式？
   - 若不是，必须重写后再输出 JSON。
2) 若原文出现“买单/买走/提走/带走/成交”，purchase_decision_status 是否为「已成交」？
   - 若不是，必须修正为「已成交」后再输出 JSON。
3) 若 visit_purpose 仅为“通勤/出差/旅游”等单词，判定为错误，必须补充物理物品与功能诉求。
4) 若原文出现“电脑/文件/证件/充电宝/行李”等物理携带物，visit_purpose 中必须出现至少一个对应物品词。
5) 若你把“场景-功能因果”写进了 trend_signals，但 visit_purpose 仍是泛词，判定为错误；必须把该因果内容搬到 visit_purpose。

【L3 字段最小合格线（用于防止空值）】
- 当原文存在明确成交动作词（买单/买走/提走/带走/成交）时：
  - purchase_decision_status 不能为空，且必须为「已成交」。
- 当原文存在明确功能诉求词（必须能装/需要大容量/装15寸电脑等）时：
  - visit_purpose 不能为空，且必须使用「场景 - 功能诉求」格式。

【紧急补丁：client_constraints 必须覆盖物理/功能硬约束】
除审美禁忌外，必须包含功能硬约束与物理约束，例如：
- 必须装下15寸电脑
- 包不能太重
- 裤长110
- 不能是Polo领
- 只能深色/不能大Logo
若原文出现“必须/只能/不能/千万不要/绝对不”等强约束词，必须写入 client_constraints。

【纠正机制（强反转）】
- 默认 in addition to（累加）。
- 仅当出现强反转语义才覆盖，并在对应 _value 中显式添加「<已纠正>」标记。
  触发词示例：不要了、其实不喜欢、改成了、退货了、上次说错了、千万别、绝对不要。
- 品类偏好隔离：某品类禁忌不自动外推到所有品类（如“红色西装不要”不等于“红色包也不要”，除非原文明确）。

【时间规则（严厉）】
- timeline / client_timeline / ca_action_item 遇到相对时间（下周五、月底、过两天、明天）时，必须结合当前日期换算为 YYYY-MM-DD。
- 若只能得到区间，写区间并降低 confidence；禁止编造精确日期。

【V2 连载记忆示例（仅用于规则示范，真实输出仍是完整 JSON）】
示例A（新疆滑雪大叔 -> 北京投资客）：
- 历史：4月1日记录「4月10日左右去新疆滑雪，需求雪镜和羽绒服」。
- 新输入：4月15日复盘提到「羽绒服满意；下周去北京投资研讨会要正式西装；讨厌红色要深色；雪镜太紧想调松；明早发西装图」。
- 期望：保留滑雪与羽绒服满意（累加）；新增北京研讨会+西装需求；红色禁忌只在对应品类表达；明早动作写入 ca_action_item，日期绝对化；status 为意向待定。

示例B（Julian 风水红衣 -> 通勤包）：
- 历史：3月记录「替父亲买红色衣服（风水需求）」。
- 新输入：4月「今天本人来，父亲红衣不用推；她明确说千万不要红色，想要能装15寸电脑的大容量通勤托特；看中编织托特但嫌重未买」。
- 期望：target_recipients 从父亲切换到本人；visit_purpose 写出“通勤+带电脑=>大容量需求”因果；client_constraints 写出“不要红色、包太重不可”；强反转加 <已纠正>；status 为放弃购买或意向待定（取决于是否有后续动作）。

示例C（公安系统大哥）：
- 历史：192cm/190斤，预算4-5万，喜欢亮色年轻简约，裤长110，挑裤型。
- 新输入：明确「绝对不穿Polo领；深蓝阔腿裤很满意；今天现金不够，明天司机带钱来取，先打包」。
- 期望：长期画像继承不丢失；新增强否定约束「Polo领」；positive_signals 记录试穿满意与明确来取动作；negative_reasons 记录现金不足；status 为意向待定；ca_action_item 写明次日交付动作与绝对日期。

示例D（Failure Case 修复：米白编织托特包）：
- 输入：客户说日常通勤要带15寸电脑和文件，所以包必须大容量；先看米白编织托特嫌重；后换轻一点的大号托特并当场买单；要求低调不要花哨Logo。
- 期望（关键字段）：
  - visit_purpose._value = 「日常通勤 - 需携带15寸电脑和文件，需大容量托特包」
  - purchase_decision_status._value = 「已成交」
  - positive_signals._value 至少包含「当场买单」或等价成交动作
  - negative_reasons._value 可记录过程阻力「初始款式偏重」，但不得改变最终成交状态
  - client_constraints._value 包含「能装15寸电脑」「不能太重」「低调无花哨Logo」
"""
    return get_current_date_prefix() + few_shot_and_rules.strip() + "\n" + v2_addon.strip()


def _field_obj(raw) -> dict:
    if isinstance(raw, dict):
        return {
            "_value": raw.get("_value"),
            "_evidence": raw.get("_evidence"),
            "_confidence": raw.get("_confidence") or "Low",
        }
    return {"_value": None, "_evidence": None, "_confidence": "Low"}


def _sanitize_decision_status(obj: dict) -> dict:
    allowed = {"已成交", "意向待定", "仅浏览", "放弃购买"}
    value = obj.get("_value")
    if value in allowed:
        return obj
    return {
        "_value": None,
        "_evidence": obj.get("_evidence"),
        "_confidence": "Low",
    }


def _infer_decision_status(transcript: str) -> str | None:
    t = transcript or ""
    if any(k in t for k in ("已买", "买了", "下单", "成交", "付款成功", "刷卡")):
        return "已成交"
    if any(k in t for k in ("没买", "没买走", "放弃", "不要了", "算了", "不买了")):
        return "放弃购买"
    if any(k in t for k in ("看中了", "满意", "考虑", "等", "明天来取", "先打包", "发图片")):
        return "意向待定"
    if any(k in t for k in ("随便看看", "仅了解", "逛逛")):
        return "仅浏览"
    return None


def _infer_positive_signals(transcript: str) -> str | None:
    t = transcript or ""
    signals = []
    if "满意" in t:
        signals.append("对试穿/既有单品反馈满意")
    if "看中" in t or "看中了" in t:
        signals.append("出现明确看中款式")
    if "明天" in t and any(k in t for k in ("来取", "带钱", "打包")):
        signals.append("有明确近期成交动作")
    if "加了微信" in t or "发图片" in t or "发尺寸" in t:
        signals.append("愿意继续接收后续推荐")
    return "；".join(signals) if signals else None


def _infer_negative_reasons(transcript: str) -> str | None:
    t = transcript or ""
    reasons = []
    if "没现货" in t or "无现货" in t:
        reasons.append("库存不足")
    if "太重" in t or "偏重" in t:
        reasons.append("体感重量不满意")
    if "现金不够" in t or "预算不够" in t:
        reasons.append("当次支付条件不足")
    if "没买" in t or "没买走" in t:
        reasons.append("本次未完成购买")
    return "；".join(reasons) if reasons else None


def _contains_strong_correction(transcript: str) -> bool:
    t = transcript or ""
    return any(k in t for k in ("不要了", "其实不喜欢", "改成", "退货", "上次说错", "千万别"))


def _append_absolute_hint(text: str) -> str:
    """
    轻量日期补全：若包含相对时间且未出现 YYYY-MM-DD，则在文末追加推算日期提示。
    """
    if not text:
        return text
    if re.search(r"\d{4}-\d{2}-\d{2}", text):
        return text
    now = datetime.now(_SHANGHAI_TZ).date()
    hints = []
    if "明天" in text:
        hints.append((now + timedelta(days=1)).strftime("%Y-%m-%d"))
    if "后天" in text:
        hints.append((now + timedelta(days=2)).strftime("%Y-%m-%d"))
    if "下周" in text:
        # 用下周一作为最小可执行锚点，避免含糊
        days_to_next_monday = (7 - now.weekday()) % 7
        days_to_next_monday = 7 if days_to_next_monday == 0 else days_to_next_monday
        hints.append((now + timedelta(days=days_to_next_monday)).strftime("%Y-%m-%d"))
    if not hints:
        return text
    return f"{text}（绝对日期参考：{', '.join(sorted(set(hints))) }）"


def normalize_v2_output(data: dict, transcript: str = "") -> dict:
    """
    将模型结果标准化为 V2：
    - 保留旧字段
    - 补齐 visit_purpose/client_timeline/ca_action_item 等新字段
    - 生成 L1~L4 分层结构
    """
    if not isinstance(data, dict):
        return data

    out = copy.deepcopy(data)
    legacy_keys = (
        "target_recipients",
        "life_event",
        "timeline",
        "aesthetic_preference",
        "size_height",
        "budget",
        "mood",
        "trend_signals",
        "next_step_intent",
        "interested_items",
        "client_constraints",
        "purchase_frequency",
    )
    for k in legacy_keys:
        out[k] = _field_obj(out.get(k))

    out["visit_purpose"] = _field_obj(out.get("visit_purpose"))
    if out["visit_purpose"]["_value"] is None:
        out["visit_purpose"] = copy.deepcopy(out["life_event"])

    out["purchase_decision_status"] = _sanitize_decision_status(
        _field_obj(out.get("purchase_decision_status"))
    )
    out["positive_signals"] = _field_obj(out.get("positive_signals"))
    out["negative_reasons"] = _field_obj(out.get("negative_reasons"))

    out["client_timeline"] = _field_obj(out.get("client_timeline"))
    if out["client_timeline"]["_value"] is None:
        out["client_timeline"] = copy.deepcopy(out["timeline"])

    out["ca_action_item"] = _field_obj(out.get("ca_action_item"))
    if out["ca_action_item"]["_value"] is None:
        out["ca_action_item"] = copy.deepcopy(out["next_step_intent"])

    # —— 业务兜底：漏斗字段自动补齐（仅在模型未给值时）——
    if out["purchase_decision_status"]["_value"] is None:
        inferred = _infer_decision_status(transcript)
        if inferred:
            out["purchase_decision_status"] = {
                "_value": inferred,
                "_evidence": "基于原文动作词规则补全",
                "_confidence": "Medium",
            }
    if out["positive_signals"]["_value"] is None:
        inferred = _infer_positive_signals(transcript)
        if inferred:
            out["positive_signals"] = {
                "_value": inferred,
                "_evidence": "基于原文正向信号规则补全",
                "_confidence": "Medium",
            }
    if out["negative_reasons"]["_value"] is None:
        inferred = _infer_negative_reasons(transcript)
        if inferred:
            out["negative_reasons"] = {
                "_value": inferred,
                "_evidence": "基于原文阻力信号规则补全",
                "_confidence": "Medium",
            }

    # 强纠正场景：若命中强反转语义，则在约束字段中补标记
    if _contains_strong_correction(transcript):
        cc = out["client_constraints"]
        val = cc.get("_value")
        if isinstance(val, str) and val and "<已纠正>" not in val:
            cc["_value"] = f"{val} <已纠正>"
        elif val is None:
            cc["_value"] = "<已纠正>"
        if not cc.get("_evidence"):
            cc["_evidence"] = "命中强反转语义触发词"
        if (cc.get("_confidence") or "Low") == "Low":
            cc["_confidence"] = "Medium"

    # timeline/next-step 轻量绝对日期提示
    for k in ("timeline", "client_timeline", "ca_action_item"):
        obj = out.get(k)
        if isinstance(obj, dict) and isinstance(obj.get("_value"), str):
            obj["_value"] = _append_absolute_hint(obj["_value"])

    out["L1_Client_Profile"] = {
        "target_recipients": copy.deepcopy(out["target_recipients"]),
        "life_event": copy.deepcopy(out["life_event"]),
        "size_height": copy.deepcopy(out["size_height"]),
        "budget": copy.deepcopy(out["budget"]),
        "aesthetic_preference": copy.deepcopy(out["aesthetic_preference"]),
    }
    out["L2_Constraints"] = {
        "client_constraints": copy.deepcopy(out["client_constraints"]),
    }
    out["L3_Visit_Funnel"] = {
        "visit_purpose": copy.deepcopy(out["visit_purpose"]),
        "purchase_decision_status": copy.deepcopy(out["purchase_decision_status"]),
        "positive_signals": copy.deepcopy(out["positive_signals"]),
        "negative_reasons": copy.deepcopy(out["negative_reasons"]),
        "interested_items": copy.deepcopy(out["interested_items"]),
        "trend_signals": copy.deepcopy(out["trend_signals"]),
        "mood": copy.deepcopy(out["mood"]),
    }
    out["L4_Next_Steps"] = {
        "client_timeline": copy.deepcopy(out["client_timeline"]),
        "ca_action_item": copy.deepcopy(out["ca_action_item"]),
    }
    return out


def extract_from_transcript(transcript: str) -> dict:
    """
    供 Streamlit 等调用：对单段口述文本调用与 CLI 相同的 DeepSeek/OpenRouter 提取逻辑。
    返回模型 JSON（含 summary 与各 *_object 字段），不含 id。
    """
    root_env = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=root_env)

    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "未找到 API Key。请在 .env 中设置 OPENROUTER_API_KEY 或 DEEPSEEK_API_KEY"
        )

    text = (transcript or "").strip()
    if not text:
        raise ValueError("口述文本为空。")

    system_prompt = build_system_prompt()
    user_prompt = f"请处理以下文本并按格式提取：\n{text}"

    payload = {
        "model": os.getenv("DEFAULT_MODEL", "deepseek/deepseek-chat"),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 3500,
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json=payload,
        timeout=90,
    )
    response.raise_for_status()
    model_output = response.json()["choices"][0]["message"]["content"]
    extracted = extract_json_from_text(model_output)
    return normalize_v2_output(extracted, transcript=text)


def main() -> None:
    root_env = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=root_env)

    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "未找到 API Key。请在 .env 中设置 OPENROUTER_API_KEY 或 DEEPSEEK_API_KEY"
        )

    print("🚀 绿野仙踪测试已启动！(ID 自动计数 · 已启用当前日期注入 + 业务基线 Prompt)")
    print("-" * 50)

    counter = 1

    while True:
        user_input = input(f"\n🎤 [ID: M4-{counter:02d}] 请输入口述笔记 (输入 'q' 退出): ")

        if user_input.strip().lower() == "q":
            print("👋 测试结束。")
            break
        if not user_input.strip():
            continue

        # 每条请求刷新日期，长会话也正确
        system_prompt = build_system_prompt()
        user_prompt = f"请处理以下文本并按格式提取：\n{user_input}"

        payload = {
            "model": os.getenv("DEFAULT_MODEL", "deepseek/deepseek-chat"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 3500,
        }

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json=payload,
                timeout=90,
            )
            response.raise_for_status()

            model_output = response.json()["choices"][0]["message"]["content"]
            extracted_data = normalize_v2_output(
                extract_json_from_text(model_output),
                transcript=user_input,
            )

            final_result = {"id": f"M4-{counter:02d}"}
            final_result.update(extracted_data)

            print("\n✅ 提取成功：")
            print(json.dumps(final_result, ensure_ascii=False, indent=2))

            counter += 1

        except Exception as e:
            print(f"\n❌ 运行出错了: {e}")


if __name__ == "__main__":
    main()

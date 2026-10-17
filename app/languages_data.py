"""
Language dictionary and utilities for 200+ languages supported by NLLB-200 and LLMs.
Provides search autocomplete, Russian and English localized names, native scripts,
and backward-compatible lookup tables.
"""
from typing import Dict, Any, List, Optional

# Full database of 202 FLORES-200 / NLLB language codes:
# nllb_code: (ru_name, en_name, native_name, short_code)
RAW_LANG_DATA: Dict[str, tuple] = {
    'ace_Arab': ('Ачехский (арабское письмо)', 'Acehnese (Arabic)', 'بهسا اچيه', ''),
    'ace_Latn': ('Ачехский (латиница)', 'Acehnese (Latin)', 'Basa Acèh', ''),
    'acm_Arab': ('Месопотамский арабский (Ирак)', 'Mesopotamian Arabic', 'عربي عراقي', ''),
    'acq_Arab': ('Таиззи-аденский арабский (Йемен)', 'Taizzi-Adeni Arabic', 'عربي يمني', ''),
    'aeb_Arab': ('Тунисский арабский', 'Tunisian Arabic', 'عربي تونسي', ''),
    'afr_Latn': ('Африкаанс', 'Afrikaans', 'Afrikaans', 'af'),
    'ajp_Arab': ('Южнолевантийский арабский', 'South Levantine Arabic', 'عربي شامي جنوبي', ''),
    'aka_Latn': ('Акан', 'Akan', 'Akan', 'ak'),
    'als_Latn': ('Албанский (тоскский)', 'Albanian (Tosk)', 'Shqip', 'sq'),
    'amh_Ethi': ('Амхарский', 'Amharic', 'አማርኛ', 'am'),
    'apc_Arab': ('Северолевантийский арабский (Сирия, Ливан)', 'North Levantine Arabic', 'عربي شامي شمالي', ''),
    'arb_Arab': ('Арабский (литературный)', 'Modern Standard Arabic', 'العربية الفصحى', 'ar'),
    'ars_Arab': ('Недждийский арабский (Саудовская Аравия)', 'Najdi Arabic', 'عربي نجدي', ''),
    'ary_Arab': ('Марокканский арабский', 'Moroccan Arabic', 'عربي مغربي / الدارجة', ''),
    'arz_Arab': ('Египетский арабский', 'Egyptian Arabic', 'عربي مصري', ''),
    'asm_Beng': ('Ассамский', 'Assamese', 'অসমীয়া', 'as'),
    'ast_Latn': ('Астурийский', 'Asturian', 'Asturianu', 'ast'),
    'awa_Deva': ('Авадхи', 'Awadhi', 'अवधी', 'awa'),
    'ayr_Latn': ('Аймара', 'Central Aymara', 'Aymar aru', 'ay'),
    'azb_Arab': ('Южноазербайджанский (Иран)', 'South Azerbaijani', 'تورکجه / گونی آذربایجان', ''),
    'azj_Latn': ('Азербайджанский', 'North Azerbaijani', 'Azərbaycan dili', 'az'),
    'bak_Cyrl': ('Башкирский', 'Bashkir', 'Башҡортса', 'ba'),
    'bam_Latn': ('Бамбара', 'Bambara', 'Bamanankan', 'bm'),
    'ban_Latn': ('Балийский', 'Balinese', 'Basa Bali', 'ban'),
    'bel_Cyrl': ('Белорусский', 'Belarusian', 'Беларуская', 'be'),
    'bem_Latn': ('Бемба', 'Bemba', 'Ichibemba', 'bem'),
    'ben_Beng': ('Бенгальский', 'Bengali', 'বাংলা', 'bn'),
    'bho_Deva': ('Бходжпури', 'Bhojpuri', 'भोजपुरी', 'bho'),
    'bjn_Arab': ('Банджарский (арабское письмо)', 'Banjar (Arabic)', 'بهاس بنجر', ''),
    'bjn_Latn': ('Банджарский (латиница)', 'Banjar (Latin)', 'Bahasa Banjar', ''),
    'bod_Tibt': ('Тибетский', 'Standard Tibetan', 'བོད་སྐད་', 'bo'),
    'bos_Latn': ('Боснийский', 'Bosnian', 'Bosanski', 'bs'),
    'bug_Latn': ('Бугийский', 'Buginese', 'Basa Ugi', 'bug'),
    'bul_Cyrl': ('Болгарский', 'Bulgarian', 'Български', 'bg'),
    'cat_Latn': ('Каталанский', 'Catalan', 'Català', 'ca'),
    'ceb_Latn': ('Себуанский', 'Cebuano', 'Sinugboanon', 'ceb'),
    'ces_Latn': ('Чешский', 'Czech', 'Čeština', 'cs'),
    'cjk_Latn': ('Чокве', 'Chokwe', 'Cokwe', 'cjk'),
    'ckb_Arab': ('Курдский (сорани)', 'Central Kurdish (Sorani)', 'کوردیی ناوەندی', 'ckb'),
    'crh_Latn': ('Крымскотатарский', 'Crimean Tatar', 'Qırımtatar tili', 'crh'),
    'cym_Latn': ('Валлийский', 'Welsh', 'Cymraeg', 'cy'),
    'dan_Latn': ('Датский', 'Danish', 'Dansk', 'da'),
    'deu_Latn': ('Немецкий', 'German', 'Deutsch', 'de'),
    'dik_Latn': ('Динка', 'Southwestern Dinka', 'Thuɔŋjäŋ', 'dik'),
    'dyu_Latn': ('Дьюла', 'Dyula', 'Julakan', 'dyu'),
    'dzo_Tibt': ('Дзонг-кэ (Бутан)', 'Dzongkha', 'རྫོང་ཁ', 'dz'),
    'ell_Grek': ('Греческий', 'Greek', 'Ελληνικά', 'el'),
    'eng_Latn': ('Английский', 'English', 'English', 'en'),
    'epo_Latn': ('Эсперанто', 'Esperanto', 'Esperanto', 'eo'),
    'est_Latn': ('Эстонский', 'Estonian', 'Eesti', 'et'),
    'eus_Latn': ('Баскский', 'Basque', 'Euskara', 'eu'),
    'ewe_Latn': ('Эве', 'Ewe', 'Eʋegbe', 'ee'),
    'fao_Latn': ('Фарерский', 'Faroese', 'Føroyskt', 'fo'),
    'fij_Latn': ('Фиджийский', 'Fijian', 'Na Vosa Vakaviti', 'fj'),
    'fin_Latn': ('Финский', 'Finnish', 'Suomi', 'fi'),
    'fon_Latn': ('Фон', 'Fon', 'Fɔngbe', 'fon'),
    'fra_Latn': ('Французский', 'French', 'Français', 'fr'),
    'fur_Latn': ('Фриульский', 'Friulian', 'Furlan', 'fur'),
    'fuv_Latn': ('Фула (Нигерия)', 'Nigerian Fulfulde', 'Fulfulde', 'ff'),
    'gaz_Latn': ('Оромо', 'West Central Oromo', 'Afaan Oromoo', 'om'),
    'gla_Latn': ('Шотландский гэльский', 'Scottish Gaelic', 'Gàidhlig', 'gd'),
    'gle_Latn': ('Ирландский', 'Irish', 'Gaeilge', 'ga'),
    'glg_Latn': ('Галисийский', 'Galician', 'Galego', 'gl'),
    'grn_Latn': ('Гуарани', 'Guarani', 'Avañeʼẽ', 'gn'),
    'guj_Gujr': ('Гуджарати', 'Gujarati', 'ગુજરાતી', 'gu'),
    'hat_Latn': ('Гаитянский креольский', 'Haitian Creole', 'Kreyòl ayisyen', 'ht'),
    'hau_Latn': ('Хауса', 'Hausa', 'Harshen Hausa', 'ha'),
    'heb_Hebr': ('Иврит', 'Hebrew', 'עברית', 'he'),
    'hin_Deva': ('Хинди', 'Hindi', 'हिन्दी', 'hi'),
    'hne_Deva': ('Чхаттисгархи', 'Chhattisgarhi', 'छत्तीसगढ़ी', 'hne'),
    'hrv_Latn': ('Хорватский', 'Croatian', 'Hrvatski', 'hr'),
    'hun_Latn': ('Венгерский', 'Hungarian', 'Magyar', 'hu'),
    'hye_Armn': ('Армянский', 'Armenian', 'Հայերեն', 'hy'),
    'ibo_Latn': ('Игбо', 'Igbo', 'Asụsụ Igbo', 'ig'),
    'ilo_Latn': ('Илоканский', 'Ilocano', 'Pagsasao nga Ilokano', 'ilo'),
    'ind_Latn': ('Индонезийский', 'Indonesian', 'Bahasa Indonesia', 'id'),
    'isl_Latn': ('Исландский', 'Icelandic', 'Íslenska', 'is'),
    'ita_Latn': ('Итальянский', 'Italian', 'Italiano', 'it'),
    'jav_Latn': ('Яванский', 'Javanese', 'Basa Jawa', 'jv'),
    'jpn_Jpan': ('Японский', 'Japanese', '日本語', 'ja'),
    'kab_Latn': ('Кабильский', 'Kabyle', 'Taqbaylit', 'kab'),
    'kac_Latn': ('Цзинпо (Качин)', 'Jingpho', 'Jinghpaw', 'kac'),
    'kam_Latn': ('Камба', 'Kamba', 'Kikamba', 'kam'),
    'kan_Knda': ('Каннада', 'Kannada', 'ಕನ್ನಡ', 'kn'),
    'kas_Arab': ('Кашмири (арабское письмо)', 'Kashmiri (Arabic)', 'کٲشُر', ''),
    'kas_Deva': ('Кашмири (деванагари)', 'Kashmiri (Devanagari)', 'कॉशुर', 'ks'),
    'kat_Geor': ('Грузинский', 'Georgian', 'ქართული', 'ka'),
    'kaz_Cyrl': ('Казахский', 'Kazakh', 'Қазақ тілі', 'kk'),
    'kbp_Latn': ('Кабье', 'Kabiye', 'Kabɩyɛ', 'kbp'),
    'kea_Latn': ('Кабовердиану (креольский)', 'Kabuverdianu', 'Kriolu kabuberdiánu', 'kea'),
    'khk_Cyrl': ('Монгольский (халха)', 'Halh Mongolian', 'Монгол хэл', 'mn'),
    'khm_Khmr': ('Кхмерский (Камбоджа)', 'Khmer', 'ភាសាខ្មែរ', 'km'),
    'kik_Latn': ('Кикуйю', 'Kikuyu', 'Gĩkũyũ', 'ki'),
    'kin_Latn': ('Киньяруанда', 'Kinyarwanda', 'Ikinyarwanda', 'rw'),
    'kir_Cyrl': ('Киргизский', 'Kyrgyz', 'Кыргызча', 'ky'),
    'kmb_Latn': ('Кимбунду', 'Kimbundu', 'Kimbundu', 'kmb'),
    'kmr_Latn': ('Курдский (курманджи)', 'Northern Kurdish (Kurmanji)', 'Kurmancî', 'kmr'),
    'knc_Arab': ('Канури (арабское письмо)', 'Central Kanuri (Arabic)', 'كانوري', ''),
    'knc_Latn': ('Канури (латиница)', 'Central Kanuri (Latin)', 'Kanuri', 'kr'),
    'kon_Latn': ('Киконго (Конго)', 'Kikongo', 'Kikongo', 'kg'),
    'kor_Hang': ('Корейский', 'Korean', '한국어', 'ko'),
    'lao_Laoo': ('Лаосский', 'Lao', 'ພາສາລາວ', 'lo'),
    'lij_Latn': ('Лигурийский', 'Ligurian', 'Lìgure', 'lij'),
    'lim_Latn': ('Лимбургский', 'Limburgish', 'Limburgs', 'li'),
    'lin_Latn': ('Лингала', 'Lingala', 'Lingála', 'ln'),
    'lit_Latn': ('Литовский', 'Lithuanian', 'Lietuvių', 'lt'),
    'lmo_Latn': ('Ломбардский', 'Lombard', 'Lumbaart', 'lmo'),
    'ltg_Latn': ('Латгальский', 'Latgalian', 'Latgalīšu', 'ltg'),
    'ltz_Latn': ('Люксембургский', 'Luxembourgish', 'Lëtzebuergesch', 'lb'),
    'lua_Latn': ('Луба-касаи', 'Luba-Kasai', 'Tshiluba', 'lua'),
    'lug_Latn': ('Луганда (Ганда)', 'Ganda', 'Oluganda', 'lg'),
    'luo_Latn': ('Луо', 'Luo', 'Dholuo', 'luo'),
    'lus_Latn': ('Мизо (Лушай)', 'Mizo', 'Mizo ṭawng', 'lus'),
    'lvs_Latn': ('Латышский', 'Standard Latvian', 'Latviešu', 'lv'),
    'mag_Deva': ('Магахи', 'Magahi', 'मगही', 'mag'),
    'mai_Deva': ('Майтхили', 'Maithili', 'मैथिली', 'mai'),
    'mal_Mlym': ('Малаялам', 'Malayalam', 'മലയാളം', 'ml'),
    'mar_Deva': ('Маратхи', 'Marathi', 'मराठी', 'mr'),
    'min_Latn': ('Минангкабау', 'Minangkabau', 'Baso Minangkabau', 'min'),
    'mkd_Cyrl': ('Македонский', 'Macedonian', 'Македонски', 'mk'),
    'mlt_Latn': ('Мальтийский', 'Maltese', 'Malti', 'mt'),
    'mni_Beng': ('Манипури (Мейтей)', 'Meitei (Bengali)', 'মৈতৈলোন্', 'mni'),
    'mos_Latn': ('Мооре (Моси)', 'Mossi', 'Mòoré', 'mos'),
    'mri_Latn': ('Маори', 'Maori', 'Te Reo Māori', 'mi'),
    'mya_Mymr': ('Бирманский', 'Burmese', 'မြန်မာစာ', 'my'),
    'nld_Latn': ('Нидерландский', 'Dutch', 'Nederlands', 'nl'),
    'nno_Latn': ('Норвежский (нюнорск)', 'Norwegian Nynorsk', 'Nynorsk', 'nn'),
    'nob_Latn': ('Норвежский (букмол)', 'Norwegian Bokmål', 'Norsk Bokmål', 'no'),
    'npi_Deva': ('Непальский', 'Nepali', 'नेपाली', 'ne'),
    'nso_Latn': ('Северный сото', 'Northern Sotho', 'Sesotho sa Leboa', 'nso'),
    'nus_Latn': ('Нуэр', 'Nuer', 'Thok Nath', 'nus'),
    'nya_Latn': ('Ньянджа (Чева)', 'Nyanja', 'Chinyanja', 'ny'),
    'oci_Latn': ('Окситанский', 'Occitan', 'Occitan', 'oc'),
    'ory_Orya': ('Одия (Ория)', 'Odia', 'ଓଡ଼ିଆ', 'or'),
    'pag_Latn': ('Пангасинанский', 'Pangasinan', 'Pangasinan', 'pag'),
    'pan_Guru': ('Пенджаби (гурмукхи)', 'Eastern Panjabi', 'ਪੰਜਾਬੀ', 'pa'),
    'pap_Latn': ('Папьяменто', 'Papiamento', 'Papiamentu', 'pap'),
    'pbt_Arab': ('Пашто (южный)', 'Southern Pashto', 'پښتو', 'ps'),
    'pes_Arab': ('Персидский (фарси)', 'Western Persian', 'فارسی', 'fa'),
    'plt_Latn': ('Малагасийский', 'Plateau Malagasy', 'Fiteny malagasy', 'mg'),
    'pol_Latn': ('Польский', 'Polish', 'Polski', 'pl'),
    'por_Latn': ('Португальский', 'Portuguese', 'Português', 'pt'),
    'prs_Arab': ('Дари (Афганистан)', 'Dari', 'دری', 'prs'),
    'quy_Latn': ('Кечуа (Аякучо)', 'Ayacucho Quechua', 'Chanka Runasimi', 'qu'),
    'ron_Latn': ('Румынский', 'Romanian', 'Română', 'ro'),
    'run_Latn': ('Рунди (Кирунди)', 'Rundi', 'Ikirundi', 'rn'),
    'rus_Cyrl': ('Русский', 'Russian', 'Русский', 'ru'),
    'sag_Latn': ('Санго', 'Sango', 'Sängö', 'sg'),
    'san_Deva': ('Санскрит', 'Sanskrit', 'संस्कृतम्', 'sa'),
    'sat_Beng': ('Сантали', 'Santali', 'সাঁওতালী', 'sat'),
    'scn_Latn': ('Сицилийский', 'Sicilian', 'Sicilianu', 'scn'),
    'shn_Mymr': ('Шанский', 'Shan', 'ၽႃႇသႃႇတႆး', 'shn'),
    'sin_Sinh': ('Сингальский', 'Sinhala', 'සිංහල', 'si'),
    'slk_Latn': ('Словацкий', 'Slovak', 'Slovenčina', 'sk'),
    'slv_Latn': ('Словенский', 'Slovenian', 'Slovenščina', 'sl'),
    'smo_Latn': ('Самоанский', 'Samoan', 'Gagana Sāmoa', 'sm'),
    'sna_Latn': ('Шона', 'Shona', 'chiShona', 'sn'),
    'snd_Arab': ('Синдхи', 'Sindhi', 'سنڌي', 'sd'),
    'som_Latn': ('Сомалийский', 'Somali', 'Soomaaliga', 'so'),
    'sot_Latn': ('Южный сото (Сесото)', 'Southern Sotho', 'Sesotho', 'st'),
    'spa_Latn': ('Испанский', 'Spanish', 'Español', 'es'),
    'srd_Latn': ('Сардинский', 'Sardinian', 'Sardu', 'sc'),
    'srp_Cyrl': ('Сербский', 'Serbian', 'Српски', 'sr'),
    'ssw_Latn': ('Свати', 'Swati', 'SiSwati', 'ss'),
    'sun_Latn': ('Сунданский', 'Sundanese', 'Basa Sunda', 'su'),
    'swe_Latn': ('Шведский', 'Swedish', 'Svenska', 'sv'),
    'swh_Latn': ('Суахили', 'Swahili', 'Kiswahili', 'sw'),
    'szl_Latn': ('Силезский', 'Silesian', 'Ślōnski', 'szl'),
    'tam_Taml': ('Тамильский', 'Tamil', 'தமிழ்', 'ta'),
    'taq_Latn': ('Тамашек (латиница)', 'Tamasheq (Latin)', 'Tamasheq', ''),
    'taq_Tfng': ('Тамашек (тифинаг)', 'Tamasheq (Tifinagh)', 'ⵜⴰⵎⴰⵛⴰⵇ', ''),
    'tat_Cyrl': ('Татарский', 'Tatar', 'Татар теле', 'tt'),
    'tel_Telu': ('Телугу', 'Telugu', 'తెలుగు', 'te'),
    'tgk_Cyrl': ('Таджикский', 'Tajik', 'Тоҷикӣ', 'tg'),
    'tgl_Latn': ('Тагальский (Филиппины)', 'Tagalog', 'Wikang Tagalog', 'tl'),
    'tha_Thai': ('Тайский', 'Thai', 'ภาษาไทย', 'th'),
    'tir_Ethi': ('Тигринья', 'Tigrinya', 'ትግርኛ', 'ti'),
    'tpi_Latn': ('Ток-писин', 'Tok Pisin', 'Tok Pisin', 'tpi'),
    'tsn_Latn': ('Тсвана', 'Tswana', 'Setswana', 'tn'),
    'tso_Latn': ('Тсонга', 'Tsonga', 'Xitsonga', 'ts'),
    'tuk_Latn': ('Туркменский', 'Turkmen', 'Türkmençe', 'tk'),
    'tum_Latn': ('Тумбука', 'Tumbuka', 'chiTumbuka', 'tum'),
    'tur_Latn': ('Турецкий', 'Turkish', 'Türkçe', 'tr'),
    'twi_Latn': ('Тви (Ашанти)', 'Twi', 'Twi', 'tw'),
    'tzm_Tfng': ('Тамазигхт (Атлас)', 'Central Atlas Tamazight', 'ⵜⴰⵎⴰⵣⵉⵖⵜ', ''),
    'uig_Arab': ('Уйгурский', 'Uyghur', 'ئۇيغۇرچە', 'ug'),
    'ukr_Cyrl': ('Украинский', 'Ukrainian', 'Українська', 'uk'),
    'umb_Latn': ('Умбунду', 'Umbundu', 'Umbundu', 'umb'),
    'urd_Arab': ('Урду', 'Urdu', 'اردو', 'ur'),
    'uzn_Latn': ('Узбекский', 'Northern Uzbek', 'Oʻzbekcha', 'uz'),
    'vec_Latn': ('Венецианский', 'Venetian', 'Vèneto', 'vec'),
    'vie_Latn': ('Вьетнамский', 'Vietnamese', 'Tiếng Việt', 'vi'),
    'war_Latn': ('Варайский', 'Waray', 'Winaray', 'war'),
    'wol_Latn': ('Волоф', 'Wolof', 'Wolof', 'wo'),
    'xho_Latn': ('Коса', 'Xhosa', 'isiXhosa', 'xh'),
    'ydd_Hebr': ('Идиш', 'Eastern Yiddish', 'ייִדיш', 'yi'),
    'yor_Latn': ('Йоруба', 'Yoruba', 'Èdè Yorùbá', 'yo'),
    'yue_Hant': ('Кантонский (Юэ)', 'Yue Chinese (Cantonese)', '粵語', 'yue'),
    'zho_Hans': ('Китайский (упрощенный)', 'Chinese (Simplified)', '中文 简体', 'zh'),
    'zho_Hant': ('Китайский (традиционный)', 'Chinese (Traditional)', '中文 繁體', 'zh-tw'),
    'zsm_Latn': ('Малайский', 'Standard Malay', 'Bahasa Melayu', 'ms'),
    'zul_Latn': ('Зулу', 'Zulu', 'isiZulu', 'zu'),
}

# Popular languages shown by default in "Recent / Popular" section
POPULAR_CODES = [
    "ru", "en", "de", "zh", "es", "fr", "it", "tr", "ja", "ko",
    "kk", "uz", "ka", "hy", "az", "uk", "be", "ar", "pl", "pt"
]

# Build primary database and alias lookup
LANGUAGES: Dict[str, Dict[str, str]] = {
    "auto": {
        "name": "Автоопределение",
        "en_name": "Auto Detect",
        "native": "Авто",
        "nllb": "auto",
        "code": "auto",
        "display": "⚡ Автоопределение [auto]"
    }
}

ALL_CANONICAL_LANGS: List[Dict[str, str]] = []

for nllb_code, (ru_name, en_name, native_name, short_code) in RAW_LANG_DATA.items():
    code_tag = f" [{short_code}]" if short_code else f" [{nllb_code}]"
    
    # Form informative display name
    if native_name and native_name != ru_name and native_name != en_name:
        display = f"{ru_name} / {native_name} ({en_name}){code_tag}"
    else:
        display = f"{ru_name} ({en_name}){code_tag}"

    canonical_key = short_code if short_code else nllb_code
    
    item = {
        "key": canonical_key,
        "name": ru_name,
        "en_name": en_name,
        "native": native_name,
        "nllb": nllb_code,
        "code": short_code,
        "display": display
    }
    ALL_CANONICAL_LANGS.append(item)
    
    # Register under both canonical key and nllb_code
    LANGUAGES[canonical_key] = item
    if nllb_code not in LANGUAGES:
        LANGUAGES[nllb_code] = item

# Sort all languages alphabetically by Russian name
ALL_CANONICAL_LANGS.sort(key=lambda x: x["name"])


def format_display_name(item: Dict[str, str], locale: str = "en") -> str:
    """Format language display label according to current UI locale (English first for non-RU)."""
    short_code = item.get("code", "")
    nllb_code = item.get("nllb", "")
    code_tag = f" [{short_code}]" if short_code else f" [{nllb_code}]"

    ru_name = item.get("name", "")
    en_name = item.get("en_name", "")
    native_name = item.get("native", "")

    if locale == "ru":
        # Russian first: Немецкий / Deutsch (German) [de]
        if native_name and native_name != ru_name and native_name != en_name:
            return f"{ru_name} / {native_name} ({en_name}){code_tag}"
        else:
            return f"{ru_name} ({en_name}){code_tag}"
    else:
        # Non-Russian locale: English first: German / Deutsch (Немецкий) [de]
        if native_name and native_name != en_name and native_name != ru_name:
            return f"{en_name} / {native_name} ({ru_name}){code_tag}"
        elif native_name and native_name != en_name:
            return f"{en_name} ({native_name}){code_tag}"
        else:
            return f"{en_name} ({ru_name}){code_tag}"


def get_language_info(key: str) -> Dict[str, str]:
    """Retrieve full language info by short code, nllb code, or name."""
    if not key:
        return LANGUAGES["auto"]
    if key in LANGUAGES:
        return LANGUAGES[key]
    key_low = key.lower().strip()
    for item in ALL_CANONICAL_LANGS:
        if (item["key"] == key_low or 
            item["nllb"].lower() == key_low or 
            item["code"].lower() == key_low or 
            item["name"].lower() == key_low or
            item["en_name"].lower() == key_low):
            return item
    return {"name": key, "en_name": key, "native": key, "nllb": key, "code": key, "display": key}


def get_nllb_code(key: str, default: str = "eng_Latn") -> str:
    """Get the 7-character NLLB code for any language key."""
    if key == "auto":
        return "auto"
    info = get_language_info(key)
    return info.get("nllb") or default


def get_display_name(key: str, locale: Optional[str] = None) -> str:
    """Get the formatted searchable display name for a language in the given locale."""
    if locale is None:
        try:
            from app.config import config
            locale = config.get("ui_language", "en")
        except Exception:
            locale = "en"

    if key == "auto":
        return "⚡ Автоопределение [auto]" if locale == "ru" else "⚡ Auto Detect [auto]"

    info = get_language_info(key)
    return format_display_name(info, locale=locale)


def get_sorted_languages(locale: Optional[str] = None) -> List[Dict[str, str]]:
    """Get all canonical languages sorted alphabetically according to current locale."""
    if locale is None:
        try:
            from app.config import config
            locale = config.get("ui_language", "en")
        except Exception:
            locale = "en"

    if locale == "ru":
        return sorted(ALL_CANONICAL_LANGS, key=lambda x: x["name"].lower())
    else:
        return sorted(ALL_CANONICAL_LANGS, key=lambda x: x["en_name"].lower())


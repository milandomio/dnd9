#!/usr/bin/env python
"""
HTML模板引擎
负责生成HTML页面的头部、尾部及CSS样式
"""


class HTMLTemplate:
    """HTML模板生成器"""

    # CSS样式常量
    CSS_STYLES = """
        body {
            font-family: "Microsoft YaHei", Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }
        h2 {
            color: #555;
            border-left: 4px solid #4CAF50;
            padding-left: 12px;
            margin-top: 40px;
            margin-bottom: 20px;
        }
        .npc-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }
        .npc-card-wrapper {
            position: relative;
        }
        .npc-confirm-checkbox {
            position: absolute;
            top: 8px;
            right: 8px;
            z-index: 2;
            width: 18px;
            height: 18px;
            cursor: pointer;
            accent-color: #4CAF50;
        }
        .npc-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            text-decoration: none;
            transition: transform 0.3s, box-shadow 0.3s;
            display: block;
        }
        .npc-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .npc-name {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .npc-count {
            font-size: 14px;
            opacity: 0.9;
        }
        .npc-en {
            font-size: 12px;
            opacity: 0.7;
            margin-top: 5px;
        }
        .quest-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }
        .quest-card {
            background-color: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: box-shadow 0.3s, transform 0.3s;
        }
        .quest-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transform: translateY(-2px);
        }
        .quest-id {
            font-size: 11px;
            color: #888;
            margin-bottom: 3px;
        }
        .quest-title-main {
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-bottom: 3px;
        }
        .quest-title-sub {
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
            padding-bottom: 8px;
            border-bottom: 2px solid #4CAF50;
        }
        .quest-section {
            margin-bottom: 6px;
        }
        .quest-label {
            font-size: 12px;
            color: #666;
            font-weight: bold;
            margin-bottom: 2px;
        }
        .quest-text {
            font-size: 14px;
            color: #444;
            line-height: 1.3;
        }
        .quest-content-tag {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            margin-right: 5px;
            margin-bottom: 4px;
        }
        .tag-Kill { background-color: #ffcccc; color: #cc0000; }
        .tag-Fetch { background-color: #ccffcc; color: #006600; }
        .tag-Explore { background-color: #ccccff; color: #0000cc; }
        .tag-Props { background-color: #ffffcc; color: #666600; }
        .tag-UseItem { background-color: #ffccff; color: #660066; }
        .tag-Unknown { background-color: #eeeeee; color: #666666; }
        .nav-buttons {
            text-align: center;
            margin: 30px 0;
        }
        .nav-buttons a {
            display: inline-block;
            margin: 5px;
            padding: 10px 20px;
            text-decoration: none;
            background-color: #008CBA;
            color: white;
            border-radius: 5px;
            transition: background-color 0.3s;
        }
        .nav-buttons a:hover {
            background-color: #007B9A;
        }
        .search-box {
            margin-bottom: 20px;
            text-align: center;
        }
        .search-box input {
            padding: 10px 15px;
            width: 300px;
            font-size: 14px;
            border: 2px solid #ddd;
            border-radius: 4px;
        }
        .search-box input:focus {
            outline: none;
            border-color: #4CAF50;
        }
        .required-quest {
            color: #666;
            font-size: 13px;
        }
        .required-quest a {
            color: #1976d2;
            text-decoration: none;
        }
        .required-quest a:hover {
            text-decoration: underline;
        }
        .quest-content-section {
            background-color: #e3f2fd;
            padding: 8px;
            border-radius: 6px;
            margin-bottom: 8px;
        }
        .quest-reward-section {
            background-color: #e8f5e9;
            padding: 8px;
            border-radius: 6px;
            margin-bottom: 8px;
        }
        .quest-content-label {
            font-size: 12px;
            color: #666;
            font-weight: bold;
            margin-bottom: 4px;
        }
        .quest-content-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        .quest-content-table th {
            text-align: left;
            padding: 4px 8px;
            border-bottom: 1px solid #ddd;
            color: #666;
            font-weight: bold;
            font-size: 13px;
        }
        .quest-content-table td {
            padding: 3px 8px;
            border-bottom: 1px solid #eee;
        }
        .quest-content-table tr:last-child td {
            border-bottom: none;
        }
        @media (max-width: 768px) {
            .quest-grid {
                grid-template-columns: 1fr;
            }
        }
        .nav-buttons button {
            display: inline-block;
            margin: 5px;
            padding: 10px 20px;
            text-decoration: none;
            background-color: #ff9800;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
            font-size: 14px;
        }
        .nav-buttons button:hover {
            background-color: #e68900;
        }
        .top-navbar { display: flex; justify-content: flex-end; align-items: center; gap: 8px; max-width: 1200px; margin: 0 auto 15px; padding: 8px 20px; background-color: #e0e0e0; border-radius: 5px; }
        .top-navbar a { color: #008CBA; text-decoration: none; font-size: 15px; font-weight: bold; padding: 6px 16px; border: 1px solid #008CBA; border-radius: 5px; transition: all 0.2s; }
        .top-navbar a:hover { background-color: #008CBA; color: white; }
        .debug-toggle-btn { display: block; margin: 0 auto 15px; padding: 8px 20px; background-color: #FFC107; color: #000; border: 2px solid #FF9800; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: bold; transition: all 0.2s; }
        .debug-toggle-btn:hover { background-color: #FF9800; color: #fff; }
        .debug-section {
            display: none;
        }
        .debug-section.active {
            display: block;
        }
        .inactive-section { display: none; }
        .inactive-grid { display: none; }
        .debug-active .inactive-section { display: block; }
        .debug-active .inactive-grid { display: grid; }
    """

    CSS_STYLES_DARK = """
        body {
            font-family: "Microsoft YaHei", Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #2c2c2c;
            color: #e0e0e0;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: #3a3a3a;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        h1 {
            color: #00bcd4;
            text-align: center;
            border-bottom: 3px solid #00bcd4;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }
        h2 {
            color: #80deea;
            border-left: 4px solid #00bcd4;
            padding-left: 12px;
            margin-top: 40px;
            margin-bottom: 20px;
        }
        .npc-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }
        .npc-card-wrapper {
            position: relative;
        }
        .npc-confirm-checkbox {
            position: absolute;
            top: 8px;
            right: 8px;
            z-index: 2;
            width: 18px;
            height: 18px;
            cursor: pointer;
            accent-color: #4CAF50;
        }
        .npc-card {
            background: linear-gradient(135deg, #1a3a5c 0%, #2a1a4c 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            text-decoration: none;
            transition: transform 0.3s, box-shadow 0.3s;
            display: block;
            border: 1px solid #555;
        }
        .npc-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.4);
            border-color: #00bcd4;
        }
        .npc-name {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .npc-count {
            font-size: 14px;
            opacity: 0.9;
            color: #aaa;
        }
        .npc-en {
            font-size: 12px;
            opacity: 0.7;
            margin-top: 5px;
            color: #888;
        }
        .quest-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }
        .quest-card {
            background-color: #444;
            border: 1px solid #555;
            border-radius: 8px;
            padding: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            transition: box-shadow 0.3s, transform 0.3s;
        }
        .quest-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            transform: translateY(-2px);
            border-color: #00bcd4;
        }
        .quest-id {
            font-size: 11px;
            color: #888;
            margin-bottom: 3px;
        }
        .quest-title-main {
            font-size: 18px;
            font-weight: bold;
            color: #e0e0e0;
            margin-bottom: 3px;
        }
        .quest-title-sub {
            font-size: 14px;
            color: #aaa;
            margin-bottom: 8px;
            padding-bottom: 8px;
            border-bottom: 2px solid #00bcd4;
        }
        .quest-section {
            margin-bottom: 6px;
        }
        .quest-label {
            font-size: 12px;
            color: #aaa;
            font-weight: bold;
            margin-bottom: 2px;
        }
        .quest-text {
            font-size: 14px;
            color: #ccc;
            line-height: 1.3;
        }
        .quest-content-tag {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            margin-right: 5px;
            margin-bottom: 4px;
        }
        .tag-Kill { background-color: #5c2020; color: #ff6666; }
        .tag-Fetch { background-color: #205020; color: #66ff66; }
        .tag-Explore { background-color: #202050; color: #6666ff; }
        .tag-Props { background-color: #505020; color: #ffff66; }
        .tag-UseItem { background-color: #502050; color: #ff66ff; }
        .tag-Unknown { background-color: #404040; color: #999; }
        .nav-buttons {
            text-align: center;
            margin: 30px 0;
        }
        .nav-buttons a {
            display: inline-block;
            margin: 5px;
            padding: 10px 20px;
            text-decoration: none;
            background-color: #008CBA;
            color: white;
            border-radius: 5px;
            transition: background-color 0.3s;
        }
        .nav-buttons a:hover {
            background-color: #00e5ff;
        }
        .search-box {
            margin-bottom: 20px;
            text-align: center;
        }
        .search-box input {
            padding: 10px 15px;
            width: 300px;
            font-size: 14px;
            border: 2px solid #555;
            border-radius: 4px;
            background-color: #2c2c2c;
            color: #e0e0e0;
        }
        .search-box input:focus {
            outline: none;
            border-color: #00bcd4;
        }
        .search-box input::placeholder {
            color: #888;
        }
        .required-quest {
            color: #aaa;
            font-size: 13px;
        }
        .required-quest a {
            color: #4fc3f7;
            text-decoration: none;
        }
        .required-quest a:hover {
            text-decoration: underline;
        }
        .quest-content-section {
            background-color: #e3f2fd;
            padding: 8px;
            border-radius: 6px;
            margin-bottom: 8px;
        }
        .quest-reward-section {
            background-color: #e8f5e9;
            padding: 8px;
            border-radius: 6px;
            margin-bottom: 8px;
        }
        .quest-content-label {
            font-size: 12px;
            color: #666;
            font-weight: bold;
            margin-bottom: 4px;
        }
        .quest-content-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        .quest-content-table th {
            text-align: left;
            padding: 4px 8px;
            border-bottom: 1px solid #ddd;
            color: #666;
            font-weight: bold;
            font-size: 13px;
        }
        .quest-content-table td {
            padding: 3px 8px;
            border-bottom: 1px solid #eee;
            color: #333;
        }
        .quest-content-table tr:last-child td {
            border-bottom: none;
        }
        .quest-content-section .quest-content-tag { color: inherit; }
        .quest-reward-section .quest-content-tag { color: inherit; }
        @media (max-width: 768px) {
            .quest-grid {
                grid-template-columns: 1fr;
            }
        }
        .nav-buttons button {
            display: inline-block;
            margin: 5px;
            padding: 10px 20px;
            text-decoration: none;
            background-color: #ff9800;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
            font-size: 14px;
        }
        .nav-buttons button:hover {
            background-color: #ffb74d;
        }
        .debug-section {
            display: none;
        }
        .debug-section.active {
            display: block;
        }
        .inactive-section { display: none; }
        .inactive-grid { display: none; }
        .debug-active .inactive-section { display: block; }
        .debug-active .inactive-grid { display: grid; }
        .top-navbar { display: flex; justify-content: flex-end; align-items: center; gap: 8px; max-width: 1200px; margin: 0 auto 15px; padding: 8px 20px; background-color: #3a3a3a; border-radius: 5px; }
        .top-navbar a { color: #00bcd4; text-decoration: none; font-size: 15px; font-weight: bold; padding: 6px 16px; border: 1px solid #00bcd4; border-radius: 5px; transition: all 0.2s; }
        .top-navbar a:hover { background-color: #00bcd4; color: #2c2c2c; }
        .debug-toggle-btn { display: block; margin: 0 auto 15px; padding: 8px 20px; background-color: #FFC107; color: #000; border: 2px solid #FF9800; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: bold; transition: all 0.2s; }
        .debug-toggle-btn:hover { background-color: #FF9800; color: #fff; }
    """

    @staticmethod
    def generate_header(
        title,
        include_back_link=False,
        language="zh-Hans",
        ui_translations=None,
        dark_mode=False,
        parent_url=None,
        parent_label=None,
    ):
        """
        生成HTML头部

        Args:
            title: 页面标题
            include_back_link: 是否包含返回链接
            language: 语言代码
            ui_translations: UITranslations实例
            dark_mode: 是否深色模式
            parent_url: 返回上一级的URL（可选）
            parent_label: 返回上一级的显示文本（可选）

        Returns:
            HTML头部字符串
        """
        back_link = ""
        debug_button = ""
        debug_script = ""
        if include_back_link:
            back_to_index = ui_translations.get_text(language, "back_to_index") if ui_translations else "Back to Index"
            debug = ui_translations.get_text(language, "debug") if ui_translations else "Debug"
            hide_debug = ui_translations.get_text(language, "hide_debug") if ui_translations else "Hide Debug"

            parent_btn = ""
            if parent_url:
                parent_btn = f'<a href="{parent_url}">{parent_label or "返回上一级"}</a>'
                back_link = f"""<div class="top-navbar">
    {parent_btn}
</div>"""
            else:
                back_link = f"""<div class="top-navbar">
    <a href="index.html">{back_to_index}</a>
</div>"""

            debug_button = f"""<button class="debug-toggle-btn" onclick="toggleDebug()" data-debug-text="{debug}" data-hide-text="{hide_debug}">{debug}</button>"""

            debug_script = """<script>
    function toggleDebug() {
        const sections = document.querySelectorAll('.debug-section');
        const button = document.querySelector('.debug-toggle-btn');
        sections.forEach(section => {
            section.classList.toggle('active');
        });
        document.body.classList.toggle('debug-active');
        const debugText = button.getAttribute('data-debug-text');
        const hideText = button.getAttribute('data-hide-text');
        button.textContent = sections[0].classList.contains('active') ? hideText : debugText;
    }
</script>
"""

        css = HTMLTemplate.CSS_STYLES_DARK if dark_mode else HTMLTemplate.CSS_STYLES
        return f"""<!DOCTYPE html>
<html lang="{language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
{css}
    </style>
    {debug_script}
</head>
<body>
    {back_link}
    <div class="container">
        <h1>{title}</h1>
        {debug_button}
"""

    @staticmethod
    def generate_footer():
        """生成HTML尾部"""
        return """    </div>
</body>
</html>"""

"""Generate project presentation PPT for AIExport system."""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ── Color Palette ──
PRIMARY = RGBColor(0x1A, 0x56, 0xDB)      # Deep blue
SECONDARY = RGBColor(0x2E, 0x86, 0xAB)    # Teal
ACCENT = RGBColor(0xE8, 0x6F, 0x1C)       # Orange accent
DARK = RGBColor(0x2C, 0x3E, 0x50)         # Dark slate
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_BG = RGBColor(0xF0, 0xF4, 0xF8)     # Light gray-blue
GRAY = RGBColor(0x7F, 0x8C, 0x8D)
DARK_TEXT = RGBColor(0x2C, 0x3E, 0x50)
GREEN = RGBColor(0x27, 0xAE, 0x60)
RED = RGBColor(0xE7, 0x4C, 0x3C)

# ── Paths ──
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
PPT_PATH = os.path.join(OUTPUT_DIR, "AIExport_项目讲解.pptx")


def add_bg_rect(slide, left, top, width, height, color, alpha=None):
    """Add a colored rectangle shape."""
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    if alpha is not None:
        from pptx.oxml.ns import qn
        solidFill = shape.fill._fill
        srgb = solidFill.find(qn('a:solidFill'))
        if srgb is not None:
            srgbClr = srgb[0]
            srgbClr.set('alpha', str(int(alpha * 1000)))
    return shape


def add_text_box(slide, left, top, width, height, text, font_size=18,
                 color=DARK_TEXT, bold=False, alignment=PP_ALIGN.LEFT,
                 font_name="微软雅黑", anchor=MSO_ANCHOR.TOP):
    """Add a text box with formatted text."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    txBox.word_wrap = True
    tf = txBox.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = font_name
    p.alignment = alignment
    return txBox


def add_bullet_frame(slide, left, top, width, height, items, font_size=14,
                     color=DARK_TEXT, font_name="微软雅黑", line_spacing=1.5):
    """Add a text frame with bullet points."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    txBox.word_wrap = True
    tf = txBox.text_frame
    tf.word_wrap = True

    for i, item in enumerate(items):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = item
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        p.font.name = font_name
        p.space_after = Pt(font_size * (line_spacing - 1) + 4)
        p.level = 0
    return txBox


def add_slide_number(slide, num, total):
    """Add slide number at bottom-right."""
    add_text_box(slide, Inches(8.5), Inches(7.1), Inches(1.2), Inches(0.3),
                 f"{num} / {total}", font_size=9, color=GRAY, alignment=PP_ALIGN.RIGHT)


def add_section_title(slide, title, subtitle=""):
    """Add a styled section header bar at the top of a content slide."""
    # Top bar
    add_bg_rect(slide, Inches(0), Inches(0), Inches(10), Inches(1.15), PRIMARY)
    # Title
    add_text_box(slide, Inches(0.6), Inches(0.15), Inches(8.5), Inches(0.7),
                 title, font_size=28, color=WHITE, bold=True)
    if subtitle:
        add_text_box(slide, Inches(0.6), Inches(0.7), Inches(8.5), Inches(0.35),
                     subtitle, font_size=13, color=RGBColor(0xBB, 0xCC, 0xEE))


def create_cover(prs):
    """Slide 1: Cover."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank

    # Full background
    add_bg_rect(slide, Inches(0), Inches(0), Inches(10), Inches(7.5), PRIMARY)

    # Accent stripe
    add_bg_rect(slide, Inches(0), Inches(0), Inches(10), Inches(0.08), ACCENT)

    # Bottom accent bar
    add_bg_rect(slide, Inches(0), Inches(5.5), Inches(10), Inches(0.06), ACCENT)

    # Project name
    add_text_box(slide, Inches(0.8), Inches(1.6), Inches(8.4), Inches(1.2),
                 "AIExport", font_size=52, color=WHITE, bold=True)

    # Subtitle
    add_text_box(slide, Inches(0.8), Inches(2.8), Inches(8.4), Inches(0.8),
                 "AI 智能导出与分析系统", font_size=30, color=RGBColor(0xCC, 0xD5, 0xF0))

    # Tagline
    add_text_box(slide, Inches(0.8), Inches(3.6), Inches(8.4), Inches(0.6),
                 "配置驱动 · 自动模版 · 多格式报告 · 一键完成", font_size=16,
                 color=RGBColor(0x99, 0xAA, 0xDD))

    # Meta info
    add_text_box(slide, Inches(0.8), Inches(5.8), Inches(8.4), Inches(0.4),
                 "版本 v2.0  |  纯后端 CLI 工具  |  Python 3.11+", font_size=13,
                 color=RGBColor(0x88, 0x99, 0xBB))


def create_background(prs):
    """Slide 2: Project Background & Pain Points."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_section_title(slide, "项目背景", "Why AIExport?")

    # Left column — Pain Points
    add_text_box(slide, Inches(0.6), Inches(1.4), Inches(4.2), Inches(0.5),
                 "❌  传统方式的痛点", font_size=20, color=RED, bold=True)

    pain_points = [
        "• 手工导出数据 — 登录 SQL Server，手动跑 SQL，复制粘贴到 Excel",
        "• 手工匹配模版 — 几十个员工逐一核对，门店/片区/部门手动归类",
        "• 手工计算占比 — 公式容易出错，跨表引用断裂，检查费时费力",
        "• 手工制作报告 — 反复调整格式、对齐、加粗，每次改日期都要重做",
        "• 图表缺失 — 缺乏直观的可视化图表辅助管理决策",
        "• 重复劳动 — 每次月报/半月报都要手工重复整个流程，耗时 2~4 小时",
    ]
    add_bullet_frame(slide, Inches(0.6), Inches(1.9), Inches(4.3), Inches(4.8),
                     pain_points, font_size=12, color=DARK_TEXT, line_spacing=1.6)

    # Right column — Solution
    add_text_box(slide, Inches(5.3), Inches(1.4), Inches(4.2), Inches(0.5),
                 "✅  AIExport 的解决方案", font_size=20, color=GREEN, bold=True)

    solutions = [
        "• 配置化查询 — 一条 YAML 定义所有 SQL，`{{变量}}` 参数化自动替换",
        "• 智能模版匹配 — 从 SQL 查询结果自动生成分析模版，零手工配置",
        "• 自动汇总计算 — 系统自动分组汇总 + 占比计算，100% 精确",
        "• 一键生成报告 — Markdown + Excel + PDF 三格式，格式化一步到位",
        "• 可视化图表 — 柱状图 / 饼图 / 漏斗图自动生成，中文完美渲染",
        "• 定时调度 — 支持 --auto-date 每月 1 号/16 号自动导出",
    ]
    add_bullet_frame(slide, Inches(5.3), Inches(1.9), Inches(4.3), Inches(4.8),
                     solutions, font_size=12, color=DARK_TEXT, line_spacing=1.6)

    # Bottom highlight
    add_bg_rect(slide, Inches(0.6), Inches(6.6), Inches(8.8), Inches(0.5), LIGHT_BG)
    add_text_box(slide, Inches(0.8), Inches(6.65), Inches(8.4), Inches(0.4),
                 "💡 核心价值：将 2~4 小时的手工流程压缩至 30 秒内自动完成，零人工介入",
                 font_size=13, color=PRIMARY, bold=True, alignment=PP_ALIGN.CENTER)

    add_slide_number(slide, 2, 12)


def create_system_overview(prs):
    """Slide 3: System Overview — Flow Diagram."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_section_title(slide, "系统总览", "Export → Analyze → Report — 全流程自动化")

    # Flow boxes
    stages = [
        ("📋  配置加载", "YAML 配置\n连接参数 + SQL\n多查询组", PRIMARY),
        ("📤  数据导出", "SQL Server\n参数化查询\n.xlsx 输出", SECONDARY),
        ("🔍  智能分析", "自动模版生成\n员工匹配汇总\n占比计算", RGBColor(0x8E, 0x44, 0xAD)),
        ("📊  报告生成", "Excel + PDF\nMarkdown\n图表 PNG", ACCENT),
    ]

    box_w = Inches(2.0)
    box_h = Inches(2.4)
    start_x = Inches(0.55)
    gap = Inches(0.35)
    y = Inches(1.6)

    for i, (title, desc, color) in enumerate(stages):
        x = start_x + i * (box_w + gap)
        # Box
        shape = add_bg_rect(slide, x, y, box_w, box_h, color)
        shape.shadow.inherit = False

        # Stage number
        add_text_box(slide, x, y + Inches(0.15), box_w, Inches(0.35),
                     f"Step {i+1}", font_size=11, color=RGBColor(0xFF, 0xFF, 0xFF,),
                     alignment=PP_ALIGN.CENTER)

        # Title
        add_text_box(slide, x + Inches(0.1), y + Inches(0.55), box_w - Inches(0.2), Inches(0.55),
                     title, font_size=17, color=WHITE, bold=True, alignment=PP_ALIGN.CENTER)

        # Description
        add_text_box(slide, x + Inches(0.1), y + Inches(1.2), box_w - Inches(0.2), Inches(1.0),
                     desc, font_size=11, color=RGBColor(0xEE, 0xEE, 0xFF),
                     alignment=PP_ALIGN.CENTER)

        # Arrow between boxes
        if i < len(stages) - 1:
            arrow_x = x + box_w
            add_text_box(slide, arrow_x, y + Inches(0.85), gap, Inches(0.4),
                         "▸", font_size=24, color=GRAY, alignment=PP_ALIGN.CENTER)

    # Bottom — key metrics
    metrics = [
        ("< 30 秒", "5000 行数据全流程"),
        ("10+ 模版", "同时注册管理"),
        ("3 种格式", "Excel / PDF / Markdown"),
        ("3 种图表", "柱状图 / 饼图 / 漏斗图"),
        ("100% 精确", "合计金额零偏差"),
    ]
    m_w = Inches(1.6)
    m_start_x = Inches(0.7)
    m_gap = Inches(0.35)
    for i, (value, label) in enumerate(metrics):
        mx = m_start_x + i * (m_w + m_gap)
        add_bg_rect(slide, mx, Inches(4.5), m_w, Inches(0.9), LIGHT_BG)
        add_text_box(slide, mx, Inches(4.55), m_w, Inches(0.45),
                     value, font_size=18, color=PRIMARY, bold=True, alignment=PP_ALIGN.CENTER)
        add_text_box(slide, mx, Inches(4.95), m_w, Inches(0.35),
                     label, font_size=10, color=GRAY, alignment=PP_ALIGN.CENTER)

    # Two modes
    add_text_box(slide, Inches(0.6), Inches(5.8), Inches(4.2), Inches(0.4),
                 "🔹 模式一：多查询管道（SQL → 模版分析 → 报告）", font_size=12, color=DARK_TEXT)
    add_text_box(slide, Inches(0.6), Inches(6.2), Inches(8.5), Inches(0.4),
                 "🔹 模式二：任意文件分析（.xlsx / .xls / .csv → 自动检测列 → 报告 + 图表）",
                 font_size=12, color=DARK_TEXT)

    add_slide_number(slide, 3, 12)


def create_feature_export(prs):
    """Slide 4: Feature 1 — Configurable Data Export."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_section_title(slide, "功能一：配置化数据导出", "SQL Server → .xlsx — 零代码操作")

    # Key features
    features = [
        ("📝 YAML 配置驱动", "服务器地址、端口、数据库、查询语句全部通过 YAML 文件配置，\n支持多查询组，每组可独立覆盖连接参数"),
        ("🔐 密码安全", "密码强制使用 ${ENV_VAR} 环境变量引用，\n拒绝明文密码，防止敏感信息泄露到版本控制"),
        ("🔄 参数化查询", "SQL 中支持 {{变量}} 占位符（日期范围、企业ID、商品ID 等），\n运行时自动替换为实际值，Prepared Statement 防 SQL 注入"),
        ("📤 自动导出", "查询结果自动导出为标准 .xlsx 格式，\n支持 detail_query（明细） + summary_query（汇总）双查询"),
    ]

    for i, (title, desc) in enumerate(features):
        y = Inches(1.5) + i * Inches(1.45)
        # Icon circle
        add_text_box(slide, Inches(0.6), y, Inches(0.5), Inches(0.5),
                     title[:2], font_size=20, color=PRIMARY, bold=True)
        add_text_box(slide, Inches(1.2), y, Inches(3.0), Inches(0.35),
                     title, font_size=16, color=DARK, bold=True)
        add_text_box(slide, Inches(1.2), y + Inches(0.35), Inches(8.0), Inches(0.9),
                     desc, font_size=12, color=DARK_TEXT)

    # Code snippet box
    code_box = add_bg_rect(slide, Inches(0.6), Inches(7.0), Inches(8.8), Inches(0.01), GRAY)
    add_text_box(slide, Inches(0.6), Inches(6.2), Inches(8.8), Inches(0.35),
                 "📌 使用示例:  python -m src.cli export  |  python -m src.cli export -q sanzhen-jiuti",
                 font_size=11, color=GRAY)

    add_slide_number(slide, 4, 12)


def create_feature_analysis(prs):
    """Slide 5: Feature 2 — Smart Template Analysis."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_section_title(slide, "功能二：智能模版分析", "自动匹配 · 分组汇总 · 占比计算")

    # Left — Auto Template
    add_bg_rect(slide, Inches(0.4), Inches(1.4), Inches(4.5), Inches(2.6), LIGHT_BG)
    add_text_box(slide, Inches(0.6), Inches(1.5), Inches(4.1), Inches(0.4),
                 "🧠 自动模版生成", font_size=18, color=PRIMARY, bold=True)
    auto_items = [
        "• 从 SQL 查询结果自动检测列结构",
        "• 智能识别：金额列、名称列、分组列",
        "• 根据 group_by 配置自动提取员工/门店/片区信息",
        "• match_key 指定员工 ID 匹配字段",
        "• 无需手写员工名单 YAML — 零维护成本",
    ]
    add_bullet_frame(slide, Inches(0.6), Inches(2.0), Inches(4.1), Inches(1.9),
                     auto_items, font_size=11, color=DARK_TEXT, line_spacing=1.5)

    # Right — Analysis Logic
    add_bg_rect(slide, Inches(5.2), Inches(1.4), Inches(4.5), Inches(2.6), LIGHT_BG)
    add_text_box(slide, Inches(5.4), Inches(1.5), Inches(4.1), Inches(0.4),
                 "📐 分析计算逻辑", font_size=18, color=PRIMARY, bold=True)
    calc_items = [
        "• 按 门店 → 员工 维度分组汇总销售金额",
        "• 占比 = 员工销售额 / 连锁月度总销售额 × 100%",
        "• 合计行精确校验：员工总和 ≡ SQL 总额",
        "• 模版有但数据无 → 销售额显示为 0",
        "• 数据有但模版无 → 放入附录，不计入合计",
    ]
    add_bullet_frame(slide, Inches(5.4), Inches(2.0), Inches(4.1), Inches(1.9),
                     calc_items, font_size=11, color=DARK_TEXT, line_spacing=1.5)

    # Bottom — Data flow
    add_text_box(slide, Inches(0.6), Inches(4.3), Inches(8.8), Inches(0.4),
                 "🔄 分析流程", font_size=16, color=DARK, bold=True)

    flow_steps = [
        ("导出数据\n(.xlsx)", PRIMARY),
        ("加载\nDataFrame", SECONDARY),
        ("自动生成\n模版", RGBColor(0x8E, 0x44, 0xAD)),
        ("员工匹配\n& 汇总", ACCENT),
        ("占比\n计算", RGBColor(0x27, 0xAE, 0x60)),
        ("输出\nAnalysisResult", DARK),
    ]
    fw = Inches(1.25)
    fx = Inches(0.6)
    fgap = Inches(0.25)
    for i, (label, color) in enumerate(flow_steps):
        fs_x = fx + i * (fw + fgap)
        add_bg_rect(slide, fs_x, Inches(4.8), fw, Inches(0.9), color)
        add_text_box(slide, fs_x, Inches(4.9), fw, Inches(0.7),
                     label, font_size=11, color=WHITE, bold=True, alignment=PP_ALIGN.CENTER)
        if i < len(flow_steps) - 1:
            add_text_box(slide, fs_x + fw, Inches(4.95), fgap, Inches(0.4),
                         "→", font_size=18, color=GRAY, alignment=PP_ALIGN.CENTER)

    # Metrics
    add_text_box(slide, Inches(0.6), Inches(6.0), Inches(8.8), Inches(0.5),
                 "📌 匹配覆盖率 100%  |  合计偏差 0 元  |  支持 10 万行级数据处理  |  单员工精确验证通过",
                 font_size=11, color=GRAY)

    add_slide_number(slide, 5, 12)


def create_feature_report(prs):
    """Slide 6: Feature 3 — Multi-format Report Generation."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_section_title(slide, "功能三：多格式报告生成", "Markdown + Excel + PDF — 一次分析，三种交付")

    # Three format cards
    formats = [
        ("📝 Markdown", "结构化文本报告",
         ["• 标题含日期范围",
          "• 汇总统计（总销售额/人数/门店数）",
          "• 详细分析表格（与模版一致）",
          "• 合计行 + 未匹配数据附录",
          "• UTF-8 编码，可直接阅读/编辑"]),
        ("📊 Excel", "格式化电子表格",
         ["• 表头加粗带底色填充",
          "• 金额列 #,##0.00 格式",
          "• 百分比列 0.00% 格式",
          "• 0 销售额员工灰底标注",
          "• 自动列宽 + 细线边框"]),
        ("📄 PDF", "正式归档报告",
         ["• A4 横向排版，适合打印",
          "• 嵌入式图表（柱状图/饼图/漏斗图）",
          "• 微软雅黑中文字体",
          "• 标题页 + 数据表 + 图表页",
          "• 适合客户汇报与归档"]),
    ]

    card_w = Inches(2.85)
    card_h = Inches(3.8)
    start_x = Inches(0.5)
    gap = Inches(0.22)
    card_colors = [PRIMARY, SECONDARY, ACCENT]

    for i, (title, subtitle, items) in enumerate(formats):
        x = start_x + i * (card_w + gap)
        # Card header
        add_bg_rect(slide, x, Inches(1.4), card_w, Inches(0.7), card_colors[i])
        add_text_box(slide, x + Inches(0.15), Inches(1.45), card_w - Inches(0.3), Inches(0.35),
                     title, font_size=18, color=WHITE, bold=True)
        add_text_box(slide, x + Inches(0.15), Inches(1.8), card_w - Inches(0.3), Inches(0.25),
                     subtitle, font_size=10, color=RGBColor(0xDD, 0xDD, 0xFF))
        # Card body
        add_bg_rect(slide, x, Inches(2.1), card_w, card_h - Inches(0.5), LIGHT_BG)
        add_bullet_frame(slide, x + Inches(0.15), Inches(2.2), card_w - Inches(0.3),
                         card_h - Inches(0.7), items, font_size=10, color=DARK_TEXT,
                         line_spacing=1.6)

    add_slide_number(slide, 6, 12)


def create_feature_charts(prs):
    """Slide 7: Feature 4 — Visualization Charts."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_section_title(slide, "功能四：可视化图表", "Matplotlib 渲染 · 中文完美支持 · 300 DPI 高清输出")

    # Three chart types
    charts = [
        ("📊 柱状图（Top 10 排行）", PRIMARY,
         ["• 水平条形图，Top 10 员工排行",
          "• 自动聚合「其他」项",
          "• 数值标签显示 ¥ 金额",
          "• 适合：销售排行、业绩对比"]),
        ("🥧 饼图（片区/门店分布）", SECONDARY,
         ["• 自动按片区或门店聚合",
          "• < 3% 小类归入「其他」",
          "• Set3 专业配色 + 图例",
          "• 适合：销售结构、区域占比"]),
        ("🔽 漏斗图（Top 10 漏斗）", ACCENT,
         ["• 渐变色漏斗，大值在上",
          "• 左标签 + 右数值，紧凑布局",
          "• 无坐标轴，视觉聚焦",
          "• 适合：排名、转化、分布"]),
    ]

    for i, (title, color, items) in enumerate(charts):
        y = Inches(1.5) + i * Inches(1.75)
        add_bg_rect(slide, Inches(0.5), y, Inches(0.08), Inches(1.5), color)
        add_text_box(slide, Inches(0.8), y, Inches(3.5), Inches(0.4),
                     title, font_size=17, color=color, bold=True)
        add_bullet_frame(slide, Inches(0.8), y + Inches(0.4), Inches(4.0), Inches(1.1),
                         items, font_size=11, color=DARK_TEXT, line_spacing=1.5)

    # Technical notes
    add_bg_rect(slide, Inches(5.5), Inches(1.5), Inches(4.0), Inches(4.5), LIGHT_BG)
    add_text_box(slide, Inches(5.7), Inches(1.6), Inches(3.6), Inches(0.4),
                 "🛠 技术细节", font_size=16, color=PRIMARY, bold=True)
    tech_items = [
        "• Matplotlib Agg 后端（无 GUI 依赖）",
        "• 自动发现系统中文字体：",
        "   - Windows: 微软雅黑 / 黑体 / 宋体",
        "   - Linux: Noto / WenQuanYi",
        "• 300 DPI PNG 高清输出",
        "• 图表嵌入 PDF 报告",
        "• 纯后端渲染，无需浏览器",
        "• 生成路径: output/reports/*/chart_*.png",
    ]
    add_bullet_frame(slide, Inches(5.7), Inches(2.1), Inches(3.6), Inches(3.5),
                     tech_items, font_size=10, color=DARK_TEXT, line_spacing=1.5)

    add_slide_number(slide, 7, 12)


def create_feature_file_analysis(prs):
    """Slide 8: Feature 5 — Arbitrary File Analysis."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_section_title(slide, "功能五：任意文件分析 (analyze-file)",
                      "支持 .xlsx / .xls / .csv — 无需 SQL，无需模版，智能检测")

    # Left — How it works
    add_text_box(slide, Inches(0.6), Inches(1.4), Inches(4.2), Inches(0.5),
                 "🔍 智能检测机制", font_size=18, color=PRIMARY, bold=True)

    detect_steps = [
        "1. 加载文件（自动编码检测：UTF-8 → GBK → Latin-1）",
        "2. 自动检测数值列（优先「金额」列 → 数值列最大和）",
        "3. 自动检测名称列（「姓名」→「名称」→ 首字符串列）",
        "4. 自动检测分组列（「门店」→「片区」→ 最优分类列）",
        "5. 按数值降序排列，自动计算占比",
        "6. 生成 Excel 报告 + 图表（可选 PDF）",
    ]
    add_bullet_frame(slide, Inches(0.6), Inches(1.9), Inches(4.2), Inches(3.0),
                     detect_steps, font_size=11, color=DARK_TEXT, line_spacing=1.6)

    # Right — Usage
    add_text_box(slide, Inches(5.3), Inches(1.4), Inches(4.2), Inches(0.5),
                 "💻 命令示例", font_size=18, color=ACCENT, bold=True)

    examples = [
        "# 分析单个文件",
        "$ python -m src.cli analyze-file data.xlsx",
        "",
        "# 分析 CSV 文件",
        "$ python -m src.cli analyze-file data.csv",
        "",
        "# 批量分析整个目录",
        "$ python -m src.cli analyze-file output/exports/",
        "",
        "# 指定列 + 自定义 Top N",
        "$ python -m src.cli analyze-file data.xlsx \\",
        "    --value-col \"金额\" --group-col \"区域\" --top-n 15",
        "",
        "# 仅 Excel（跳过 PDF + 图表）",
        "$ python -m src.cli analyze-file data.xlsx \\",
        "    --no-pdf --no-charts",
    ]
    add_bullet_frame(slide, Inches(5.3), Inches(1.9), Inches(4.3), Inches(4.8),
                     examples, font_size=10, color=DARK_TEXT, line_spacing=1.2)

    # Bottom — supported formats
    add_bg_rect(slide, Inches(0.6), Inches(5.3), Inches(8.8), Inches(0.7), LIGHT_BG)
    add_text_box(slide, Inches(0.8), Inches(5.4), Inches(8.4), Inches(0.5),
                 "📌 支持格式: .xlsx  |  .xls  |  .csv（自动编码检测）  |  "
                 "单文件或批量目录  |  可选 --value-col / --name-col / --group-col 手动指定",
                 font_size=11, color=DARK_TEXT)

    # Use cases
    add_text_box(slide, Inches(0.6), Inches(6.2), Inches(8.8), Inches(0.4),
                 "🎯 适用场景", font_size=16, color=DARK, bold=True)
    use_cases = [
        "• 快速分析任意导出的数据文件，无需配置 YAML 和 SQL      "
        "• 临时数据探索：拿到一份 Excel 就想看排名/分布/图表      "
        "• 批量处理：导出目录下所有 .xlsx/.csv 一键生成全套报告",
    ]
    add_bullet_frame(slide, Inches(0.6), Inches(6.6), Inches(8.8), Inches(1.0),
                     use_cases, font_size=11, color=DARK_TEXT, line_spacing=1.4)

    add_slide_number(slide, 8, 12)


def create_tech_architecture(prs):
    """Slide 9: Technical Architecture."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_section_title(slide, "技术架构", "模块化设计 · 职责单一 · 易于扩展")

    # Tech stack
    add_text_box(slide, Inches(0.6), Inches(1.4), Inches(4.2), Inches(0.4),
                 "🛠 技术栈", font_size=18, color=PRIMARY, bold=True)

    stack_items = [
        ("语言", "Python 3.11+"),
        ("CLI 框架", "Click（装饰器风格命令）"),
        ("数据处理", "pandas DataFrame"),
        ("SQL Server", "pymssql（FreeTDS，无需 ODBC）"),
        ("Excel 生成", "openpyxl（纯 Python，跨平台）"),
        ("PDF 生成", "reportlab（A4 排版，中文字体）"),
        ("图表渲染", "matplotlib（Agg 后端，300 DPI）"),
        ("日志", "structlog（结构化 JSON/文本双模式）"),
        ("配置格式", "YAML（人工可读写，支持注释）"),
        ("测试", "pytest + pytest-cov + pytest-mock（41 个用例）"),
    ]

    for i, (key, val) in enumerate(stack_items):
        y = Inches(1.9) + i * Inches(0.28)
        add_text_box(slide, Inches(0.6), y, Inches(1.3), Inches(0.25),
                     key, font_size=11, color=PRIMARY, bold=True)
        add_text_box(slide, Inches(1.9), y, Inches(2.8), Inches(0.25),
                     val, font_size=11, color=DARK_TEXT)

    # Module architecture
    add_text_box(slide, Inches(5.0), Inches(1.4), Inches(4.5), Inches(0.4),
                 "📦 模块架构", font_size=18, color=PRIMARY, bold=True)

    modules = [
        "src/config/     配置加载 & 校验",
        "src/export/     SQL 连接 & 数据导出",
        "src/analysis/   模版匹配 & 分析计算",
        "src/report/     Markdown / Excel / PDF 报告",
        "src/template/   模版注册 & 自动生成",
        "src/chart/      图表生成（柱/饼/漏斗）",
        "src/pipeline.py        全流程编排",
        "src/pipeline_file.py   任意文件分析管道",
        "src/cli.py             CLI 命令入口",
    ]

    for i, mod in enumerate(modules):
        y = Inches(1.9) + i * Inches(0.3)
        add_text_box(slide, Inches(5.0), y, Inches(4.5), Inches(0.25),
                     mod, font_size=10.5, color=DARK_TEXT, font_name="Consolas")

    # Constitution compliance
    add_bg_rect(slide, Inches(0.4), Inches(5.0), Inches(9.2), Inches(2.2), LIGHT_BG)
    add_text_box(slide, Inches(0.6), Inches(5.1), Inches(4.0), Inches(0.4),
                 "✅ 项目宪法合规", font_size=17, color=GREEN, bold=True)

    constitution = [
        "I.   规格优先 — spec.md / plan.md / tasks.md 完整",
        "II.  简单至上 — 每模块职责单一，无过度设计",
        "III. 先想后写 — 所有技术决策显式记录在 plan.md",
        "IV.  精准修改 — 纯新增功能，无现有代码变动",
        "V.   目标驱动 — TDD 测试先行，41 个用例全部通过",
        "VI.  TDD 铁律 — Red-Green-Refactor 严格执行",
    ]
    add_bullet_frame(slide, Inches(0.6), Inches(5.5), Inches(4.5), Inches(1.6),
                     constitution, font_size=10.5, color=DARK_TEXT, line_spacing=1.4)

    # Test stats
    add_text_box(slide, Inches(5.3), Inches(5.1), Inches(3.5), Inches(0.4),
                 "🧪 测试覆盖", font_size=17, color=GREEN, bold=True)
    test_stats = [
        "• 41 个 pytest 测试用例",
        "• 覆盖 8 个测试模块",
        "• 边界场景: 5000行性能 / NULL值 /",
        "  类型归一化 / 日期边界 / 密码安全",
        "• Mock SQL Server 实现离线测试",
    ]
    add_bullet_frame(slide, Inches(5.3), Inches(5.5), Inches(4.0), Inches(1.6),
                     test_stats, font_size=10.5, color=DARK_TEXT, line_spacing=1.4)

    add_slide_number(slide, 9, 12)


def create_cli_commands(prs):
    """Slide 10: CLI Commands Overview."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_section_title(slide, "CLI 命令一览", "统一命令行入口 — 简单、直观、功能完整")

    commands = [
        ("python -m src.cli run", "一键全流程",
         "导出 → 分析 → 报告 → 图表，全自动完成。\n"
         "选项: --auto-date（定时调度）| -q 组名 | --no-pdf | --no-charts"),
        ("python -m src.cli export", "仅数据导出",
         "执行 SQL 查询并导出 .xlsx 文件。\n"
         "选项: -c 配置文件 | -q 查询组"),
        ("python -m src.cli analyze-file <路径>", "任意文件分析",
         "分析 .xlsx / .xls / .csv 文件，自动检测列。\n"
         "选项: --value-col | --group-col | --top-n | --no-pdf | --no-charts"),
        ("python -m src.cli show-queries", "查看查询组",
         "显示 export.yaml 中定义的所有查询组及配置摘要。"),
        ("python -m src.cli validate", "配置校验",
         "校验 export.yaml 格式完整性、连接参数、SQL 安全性。"),
    ]

    for i, (cmd, title, desc) in enumerate(commands):
        y = Inches(1.5) + i * Inches(1.15)
        # Command box
        add_bg_rect(slide, Inches(0.5), y, Inches(9.0), Inches(0.95), LIGHT_BG)
        # Command name
        add_bg_rect(slide, Inches(0.5), y, Inches(3.2), Inches(0.35), PRIMARY)
        add_text_box(slide, Inches(0.6), y + Inches(0.02), Inches(3.0), Inches(0.3),
                     cmd, font_size=11, color=WHITE, bold=True, font_name="Consolas")
        # Title
        add_text_box(slide, Inches(4.0), y + Inches(0.02), Inches(2.0), Inches(0.3),
                     title, font_size=15, color=DARK, bold=True)
        # Description
        add_text_box(slide, Inches(0.7), y + Inches(0.4), Inches(8.4), Inches(0.55),
                     desc, font_size=10.5, color=DARK_TEXT)

    # Auto-date schedule
    add_bg_rect(slide, Inches(0.5), Inches(7.0), Inches(9.0), Inches(0.01), GRAY)
    add_text_box(slide, Inches(0.6), Inches(6.7), Inches(8.8), Inches(0.35),
                 "⏰ 定时调度:  --auto-date 自动计算日期范围 — 每月 16 号导出 1-15 号，每月 1 号导出上月整月",
                 font_size=11, color=GRAY)

    add_slide_number(slide, 10, 12)


def create_highlights(prs):
    """Slide 11: Project Highlights & Security."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_section_title(slide, "项目亮点", "安全性 · 自动化 · 可扩展性 · 可靠性")

    highlights = [
        ("🔐 安全第一", PRIMARY,
         ["密码强制 ${ENV_VAR} 环境变量引用，配置文件可安全提交版本控制",
          "SQL 参数化查询（Prepared Statements），彻底杜绝 SQL 注入",
          "配置 Schema 严格校验，端口范围/超时范围/必填字段全面检查"]),
        ("⚡ 零人工介入", SECONDARY,
         ["从 SQL 导出到报告生成全流程自动化，无需任何手工操作",
          "模版从 SQL 查询结果自动生成，无需手写员工名单 YAML",
          "任意文件拖入即分析 — analyze-file 命令智能检测所有列"]),
        ("🔌 高度可扩展", RGBColor(0x8E, 0x44, 0xAD),
         ["多查询组架构：一个 export.yaml 可定义 N 个独立查询组",
          "查询组可独立配置数据库连接、SQL、模版参数，互不干扰",
          "热加载模版注册表，新增模版无需重启服务"]),
        ("🛡 生产可靠", ACCENT,
         ["41 个 pytest 测试用例，覆盖正常流程 + 全部边界场景",
          "测试覆盖 5000 行性能基准（< 30 秒），NULL 值处理，类型归一化",
          "structlog 结构化日志覆盖全流程，异常翻译为中文可读错误信息"]),
    ]

    for i, (title, color, items) in enumerate(highlights):
        col = i % 2
        row = i // 2
        x = Inches(0.4) + col * Inches(4.8)
        y = Inches(1.5) + row * Inches(2.7)
        card_w = Inches(4.5)
        card_h = Inches(2.4)

        add_bg_rect(slide, x, y, card_w, card_h, LIGHT_BG)
        # Top accent line
        add_bg_rect(slide, x, y, card_w, Inches(0.06), color)
        add_text_box(slide, x + Inches(0.15), y + Inches(0.15), card_w - Inches(0.3), Inches(0.4),
                     title, font_size=17, color=color, bold=True)
        add_bullet_frame(slide, x + Inches(0.15), y + Inches(0.6), card_w - Inches(0.3),
                         card_h - Inches(0.8), items, font_size=10.5, color=DARK_TEXT,
                         line_spacing=1.55)

    add_slide_number(slide, 11, 12)


def create_summary(prs):
    """Slide 12: Summary & Roadmap."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_section_title(slide, "总结与展望", "AIExport — 让数据导出分析像呼吸一样自然")

    # Summary
    add_text_box(slide, Inches(0.6), Inches(1.5), Inches(4.2), Inches(0.4),
                 "📋 项目交付成果", font_size=18, color=PRIMARY, bold=True)
    deliverables = [
        "✅ 配置化 SQL Server 数据导出（参数化 + 安全）",
        "✅ 智能模版自动生成与匹配分析",
        "✅ Markdown / Excel / PDF 三格式报告",
        "✅ 柱状图 / 饼图 / 漏斗图可视化图表",
        "✅ 任意文件智能分析（xlsx/xls/csv）",
        "✅ 多查询组并行管理 + 定时调度",
        "✅ 41 个 TDD 测试用例，全部通过",
        "✅ 完整的规格/计划/任务文档体系",
    ]
    add_bullet_frame(slide, Inches(0.6), Inches(2.0), Inches(4.2), Inches(3.2),
                     deliverables, font_size=11, color=DARK_TEXT, line_spacing=1.5)

    # Future roadmap
    add_text_box(slide, Inches(5.3), Inches(1.5), Inches(4.2), Inches(0.4),
                 "🚀 后续规划", font_size=18, color=ACCENT, bold=True)
    roadmap = [
        "🔲 HTML 报告格式（Web 浏览器查看）",
        "🔲 Web Dashboard（实时监控面板）",
        "🔲 邮件自动发送报告",
        "🔲 更多数据源支持（MySQL / PostgreSQL）",
        "🔲 AI 智能洞察（异常检测、趋势预测）",
        "🔲 Webhook 通知集成（企业微信/钉钉）",
        "🔲 定时任务 Cron 集成",
        "🔲 数据对比分析（同比/环比）",
    ]
    add_bullet_frame(slide, Inches(5.3), Inches(2.0), Inches(4.2), Inches(3.2),
                     roadmap, font_size=11, color=DARK_TEXT, line_spacing=1.5)

    # Bottom
    add_bg_rect(slide, Inches(0.4), Inches(5.5), Inches(9.2), Inches(1.5), PRIMARY)
    add_text_box(slide, Inches(0.8), Inches(5.7), Inches(8.4), Inches(0.5),
                 "核心价值主张", font_size=14, color=RGBColor(0xBB, 0xCC, 0xEE))
    add_text_box(slide, Inches(0.8), Inches(6.1), Inches(8.4), Inches(0.7),
                 "将原本需要 2~4 小时的手工数据导出、模版匹配、占比计算、报告制作全流程，\n"
                 "压缩至 30 秒内自动化完成，零人工介入，100% 计算精确。",
                 font_size=18, color=WHITE, bold=True)

    # Thank you
    add_text_box(slide, Inches(0.8), Inches(7.0), Inches(8.4), Inches(0.4),
                 "感谢聆听  ·  欢迎提问", font_size=14, color=GRAY, alignment=PP_ALIGN.CENTER)

    add_slide_number(slide, 12, 12)


def main():
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    create_cover(prs)
    create_background(prs)
    create_system_overview(prs)
    create_feature_export(prs)
    create_feature_analysis(prs)
    create_feature_report(prs)
    create_feature_charts(prs)
    create_feature_file_analysis(prs)
    create_tech_architecture(prs)
    create_cli_commands(prs)
    create_highlights(prs)
    create_summary(prs)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    prs.save(PPT_PATH)
    print(f"[OK] PPT 已生成: {PPT_PATH}")
    print(f"     共 {len(prs.slides)} 页幻灯片")


if __name__ == "__main__":
    main()

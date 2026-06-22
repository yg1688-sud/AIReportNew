# TDD 测试用例文档：AI 导出与分析系统（AIExport）

**版本**: 1.0.0
**创建日期**: 2026-06-22
**测试框架**: pytest
**关联文档**: [spec.md](spec.md) | [prd.md](prd.md)

---

## 测试策略

| 层级 | 范围 | 框架 | 覆盖目标 |
|------|------|------|----------|
| 单元测试 | 配置解析、数据转换、计算逻辑 | pytest | 90%+ |
| 集成测试 | DB连接→导出→分析→报告全流程 | pytest + test fixtures | 关键路径 100% |
| 边界测试 | 空数据、大数据量、异常输入 | pytest + parametrize | 异常分支全覆盖 |

**TDD 原则**: 每个测试用例遵循 Red-Green-Refactor —— 先写测试（预期失败），再写实现（使测试通过），最后重构优化。

---

## 1. 配置模块测试 (test_config.py)

### TC-CFG-001: 加载有效的导出配置文件

```python
def test_load_valid_export_config():
    """Given 有效的YAML配置文件
       When 加载导出配置
       Then 返回包含所有必需字段的ExportConfig对象"""
    # Arrange
    config_path = "fixtures/valid_export_config.yaml"

    # Act
    config = load_export_config(config_path)

    # Assert
    assert config.server == "localhost"
    assert config.port == 1433
    assert config.database == "TestDB"
    assert config.query is not None
    assert config.enterprise_id is not None
```

### TC-CFG-002: 配置文件不存在时抛出明确错误

```python
def test_load_nonexistent_config_raises_error():
    """Given 不存在的配置文件路径
       When 加载导出配置
       Then 抛出FileNotFoundError并包含文件路径信息"""
    with pytest.raises(FileNotFoundError, match="配置文件未找到"):
        load_export_config("fixtures/nonexistent.yaml")
```

### TC-CFG-003: 配置Schema校验——缺少必填字段

```python
@pytest.mark.parametrize("missing_field", [
    "server", "port", "database", "query"
])
def test_config_missing_required_field_raises_validation_error(missing_field):
    """Given 配置文件缺少必填字段
       When 校验配置
       Then 抛出ValidationError并明确指出缺失字段"""
    config_dict = {"server": "localhost", "port": 1433, "database": "db", "query": "SELECT 1"}
    del config_dict[missing_field]

    with pytest.raises(ValidationError, match=missing_field):
        validate_export_config(config_dict)
```

### TC-CFG-004: 加载分析模版配置

```python
def test_load_analysis_template():
    """Given 有效的模版YAML配置
       When 加载模版
       Then 返回包含列定义、分组规则、排序规则的AnalysisTemplate对象"""
    template = load_template("fixtures/valid_template.yaml")

    assert template.name == "三诊九体培训动销及打卡学习情况"
    assert len(template.columns) > 0
    assert "片区" in template.group_by
    assert template.sort_rules is not None
```

### TC-CFG-005: 模版中引用的数据列不存在时报错

```python
def test_template_references_missing_data_column():
    """Given 模版列定义引用了数据源中不存在的字段
       When 校验模版
       Then 抛出ValidationError并列出不存在的字段名"""
    template = AnalysisTemplate(
        name="test",
        columns=[TemplateColumn(title="测试", source_field="nonexistent_field")]
    )

    with pytest.raises(ValidationError, match="nonexistent_field"):
        template.validate_against_schema(EXPORT_DATA_SCHEMA)
```

---

## 2. 数据导出模块测试 (test_export.py)

### TC-EXP-001: 成功导出数据为CSV格式

```python
def test_export_to_csv(mock_sql_connection):
    """Given SQL Server连接正常且查询返回数据
       When 执行导出到CSV
       Then 生成UTF-8 BOM编码的CSV文件且行数匹配"""
    mock_sql_connection.set_return_rows(SAMPLE_ORDER_ROWS)

    result = execute_export(MOCK_EXPORT_CONFIG, output_format="csv")

    assert result.row_count == len(SAMPLE_ORDER_ROWS)
    assert result.file_path.endswith(".csv")
    with open(result.file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == len(SAMPLE_ORDER_ROWS)
```

### TC-EXP-002: 成功导出数据为JSON格式

```python
def test_export_to_json(mock_sql_connection):
    """Given SQL Server连接正常且查询返回数据
       When 执行导出到JSON
       Then 生成UTF-8编码的JSON文件且包含所有行"""
    mock_sql_connection.set_return_rows(SAMPLE_ORDER_ROWS)

    result = execute_export(MOCK_EXPORT_CONFIG, output_format="json")

    with open(result.file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == len(SAMPLE_ORDER_ROWS)
```

### TC-EXP-003: 查询结果为空时正常处理

```python
def test_export_empty_result(mock_sql_connection):
    """Given SQL查询返回0行
       When 执行导出
       Then 生成仅含表头的文件且row_count=0"""
    mock_sql_connection.set_return_rows([])

    result = execute_export(MOCK_EXPORT_CONFIG)

    assert result.row_count == 0
    assert os.path.exists(result.file_path)
```

### TC-EXP-004: SQL Server连接失败返回明确错误

```python
def test_export_connection_failure(mock_sql_connection):
    """Given SQL Server不可达
       When 执行导出
       Then 抛出ConnectionError并包含服务器地址"""
    mock_sql_connection.set_connection_error("无法连接到服务器")

    with pytest.raises(ConnectionError, match="localhost"):
        execute_export(MOCK_EXPORT_CONFIG)
```

### TC-EXP-005: SQL查询超时返回明确错误

```python
def test_export_query_timeout(mock_sql_connection):
    """Given SQL查询超过超时时间
       When 执行导出
       Then 抛出TimeoutError并包含超时秒数"""
    mock_sql_connection.set_timeout(30)

    with pytest.raises(TimeoutError, match="30秒"):
        execute_export(MOCK_EXPORT_CONFIG, timeout=30)
```

### TC-EXP-006: 参数化查询正确替换参数

```python
def test_parameterized_query_replacement():
    """Given 查询模板包含{{start_date}}和{{end_date}}占位符
       When 使用参数执行查询
       Then SQL中占位符被替换为实际日期值"""
    config = ExportConfig(
        query="SELECT * FROM orders WHERE date >= '{{start_date}}' AND date < '{{end_date}}'",
        parameters={"start_date": "2026-06-01", "end_date": "2026-06-16"}
    )

    resolved = resolve_query_parameters(config)

    assert "{{start_date}}" not in resolved
    assert "2026-06-01" in resolved
    assert "2026-06-16" in resolved
```

### TC-EXP-007: SQL注入防护——参数值中的恶意代码不被执行

```python
def test_sql_injection_prevention():
    """Given 参数值包含SQL注入代码
       When 执行参数化查询
       Then 恶意代码被转义/参数化处理，不影响查询安全"""
    malicious_param = "'; DROP TABLE orders; --"
    config = ExportConfig(
        query="SELECT * FROM orders WHERE id = ?",
        parameters={"id": malicious_param}
    )

    # 使用参数化查询（PreparedStatement），而非字符串拼接
    sql, params = build_parameterized_query(config)

    assert malicious_param not in sql  # 恶意代码不在SQL文本中
    assert params[0] == malicious_param  # 作为参数值传递
```

---

## 3. 模版分析模块测试 (test_analysis.py)

### TC-ANL-001: 按片区+门店+员工分组汇总销售金额

```python
def test_group_and_sum_sales_by_employee():
    """Given 导出的订单明细数据
       When 按门店+员工维度分组汇总
       Then 每个员工的销售金额正确汇总"""
    raw_data = [
        {"门店": "保康", "姓名": "梅朱琳", "员工ID": "14694", "销售金额": 5000},
        {"门店": "保康", "姓名": "梅朱琳", "员工ID": "14694", "销售金额": 2981},
        {"门店": "北碚6店", "姓名": "刘敏", "员工ID": "6653", "销售金额": 148},
    ]

    result = analyze_by_template(raw_data, TEMPLATE_SANZHEN)

    assert result.rows[0].sales_amount == 7981   # 5000 + 2981
    assert result.rows[1].sales_amount == 148
```

### TC-ANL-002: 合计行销售金额等于所有员工销售额之和

```python
def test_total_sales_matches_sum_of_all_employees():
    """Given 模版分析结果
       When 查看合计行
       Then 合计值 == SUM(所有员工销售金额)"""
    raw_data = generate_mock_order_data(employee_count=61, seed=42)
    result = analyze_by_template(raw_data, TEMPLATE_SANZHEN)

    employee_sum = sum(row.sales_amount for row in result.rows)
    total_row = result.total_row

    assert total_row.sales_amount == employee_sum
```

### TC-ANL-003: 占比计算正确性

```python
def test_sales_percentage_calculation():
    """Given 已知总销售额和员工销售额
       When 计算占比
       Then 每员工占比 = 员工销售额 / 总销售额 * 100"""
    total_sales = 76788.68
    employee_sales = 7981.00

    percentage = (employee_sales / total_sales) * 100

    assert abs(percentage - 10.39) < 0.01  # 精确到两位小数
```

### TC-ANL-004: 所有员工占比之和接近100%

```python
def test_all_employee_percentages_sum_to_100():
    """Given 模版分析结果包含所有员工
       When 累加所有占比
       Then 总和在 99.9% ~ 100.1% 范围内"""
    raw_data = generate_mock_order_data(employee_count=61, seed=42)
    result = analyze_by_template(raw_data, TEMPLATE_SANZHEN)

    total_percentage = sum(row.percentage for row in result.rows)

    assert 99.9 <= total_percentage <= 100.1
```

### TC-ANL-005: 模版有但数据无——销售额为0

```python
def test_template_employee_not_in_data_gets_zero():
    """Given 模版中定义了员工但导出数据中没有该员工的记录
       When 执行模版匹配
       Then 该员工销售额=0，仍保留在结果表中"""
    raw_data = []  # 空数据
    template_row_count = 61

    result = analyze_by_template(raw_data, TEMPLATE_SANZHEN)

    assert len(result.rows) == template_row_count  # 所有模版行保留
    assert all(row.sales_amount == 0 for row in result.rows)
```

### TC-ANL-006: 数据有但模版无——附加行

```python
def test_data_employee_not_in_template_added_as_extra():
    """Given 导出数据包含模版中不存在的员工
       When 执行模版匹配
       Then 该员工出现在 unmatched_rows 中，日志记录警告"""
    raw_data = [
        {"门店": "未知店", "姓名": "未知员工", "员工ID": "99999", "销售金额": 1000},
    ]

    result = analyze_by_template(raw_data, TEMPLATE_SANZHEN)

    assert len(result.unmatched_rows) == 1
    assert result.unmatched_rows[0]["员工ID"] == "99999"
```

### TC-ANL-007: 模版员工+附加行的销售额合计 = 查询总销售额

```python
def test_total_includes_unmatched_rows():
    """Given 部分数据匹配模版、部分不匹配
       When 计算合计
       Then 合计值包含所有数据（匹配+不匹配）= 原始数据总销售金额"""
    matched_data = [{"门店": "保康", "姓名": "梅朱琳", "员工ID": "14694", "销售金额": 7981}]
    unmatched_data = [{"门店": "X", "姓名": "Y", "员工ID": "99999", "销售金额": 500}]

    total_expected = 7981 + 500
    result = analyze_by_template(matched_data + unmatched_data, TEMPLATE_SANZHEN)

    assert result.total_row.sales_amount == total_expected
```

### TC-ANL-008: 按片区排序保持正确顺序

```python
def test_sort_by_template_order():
    """Given 模版定义了固定的员工顺序
       When 生成分析结果
       Then 结果行按模版定义的顺序排列（不是按销售额排序）"""
    raw_data = generate_mock_order_data(employee_count=61, seed=42)
    result = analyze_by_template(raw_data, TEMPLATE_SANZHEN)

    assert result.rows[0].employee_name == "梅朱琳"   # 模版第1行
    assert result.rows[1].employee_name == "刘敏"      # 模版第2行
```

---

## 4. 报告生成模块测试 (test_report.py)

### TC-RPT-001: Markdown报告包含所有必需部分

```python
def test_markdown_report_structure():
    """Given 分析结果数据
       When 生成Markdown报告
       Then 报告包含标题、元数据、汇总统计、分析表格"""
    result = generate_mock_analysis_result()
    report = generate_markdown_report(result)

    assert "# 三诊九体培训动销" in report
    assert "## 汇总统计" in report
    assert "## 详细分析" in report
    assert "合计" in report
    assert "2026-06-01" in report
```

### TC-RPT-002: Markdown表格行数与分析结果一致

```python
def test_markdown_table_row_count_matches():
    """Given 分析结果有N个员工行
       When 生成Markdown报告
       Then 表格行数 = N + 1(表头) + 1(合计)"""
    result = generate_mock_analysis_result(employee_count=61)
    report = generate_markdown_report(result)

    table_rows = [line for line in report.split("\n") if line.startswith("|")]
    # 表头分隔行不算，实际数据行 = 61 + 1合计
    data_rows = [r for r in table_rows if "---" not in r]
    assert len(data_rows) == 61 + 1 + 1  # 员工 + 合计 + 表头
```

### TC-RPT-003: Excel文件格式正确

```python
def test_excel_report_format():
    """Given 分析结果
       When 生成Excel报告
       Then 文件存在且包含正确的工作表和表头"""
    result = generate_mock_analysis_result()
    filepath = generate_excel_report(result)

    wb = openpyxl.load_workbook(filepath)
    ws = wb.active

    assert ws.title == "三诊九体培训动销"
    # 表头加粗
    assert ws.cell(1, 1).font.bold == True
    # 第1行数据
    assert ws.cell(2, 1).value == 1  # 序号
```

### TC-RPT-004: 0销售额员工在报告中正确标注

```python
def test_zero_sales_employee_marked_in_report():
    """Given 分析结果中有销售额为0的员工
       When 生成报告
       Then 该员工行存在且销售额显示为0"""
    result = generate_mock_analysis_result()
    result.rows[5].sales_amount = 0  # 设置第6个员工为0

    report = generate_markdown_report(result)

    assert "0.00" in report  # 销售额显示为0
```

### TC-RPT-005: 生成的Excel可直接打开无报错

```python
def test_excel_file_is_valid():
    """Given 分析结果
       When 生成Excel并尝试打开
       Then openpyxl成功加载且无损坏提示"""
    result = generate_mock_analysis_result()
    filepath = generate_excel_report(result)

    # openpyxl加载不抛出异常即表示文件有效
    wb = openpyxl.load_workbook(filepath)
    ws = wb.active
    assert ws.max_row > 1
    assert ws.max_column >= 7
```

---

## 5. CLI集成测试 (test_cli.py)

### TC-CLI-001: `run` 命令执行全流程

```python
def test_cli_run_full_pipeline(mocker, mock_sql_connection):
    """Given 有效的配置文件和模版
       When 执行 `ai-export run --template sanzhen`
       Then 依次执行导出→分析→报告，退出码=0"""
    mock_sql_connection.set_return_rows(SAMPLE_ORDER_ROWS)
    mocker.patch("sys.argv", ["ai-export", "run", "--template", "sanzhen"])

    result = runner.invoke(cli_main)

    assert result.exit_code == 0
    assert "导出完成" in result.output
    assert "分析完成" in result.output
    assert "报告已生成" in result.output
```

### TC-CLI-002: `list-templates` 列出所有模版

```python
def test_cli_list_templates():
    """Given 系统中注册了多个模版
       When 执行 `ai-export list-templates`
       Then 列出所有模版名称"""
    result = runner.invoke(cli_main, ["list-templates"])

    assert result.exit_code == 0
    assert "三诊九体培训动销及打卡学习情况" in result.output
```

### TC-CLI-003: `validate` 校验配置完整性

```python
def test_cli_validate_all_configs_passes():
    """Given 所有配置文件格式正确
       When 执行 `ai-export validate`
       Then 退出码=0，显示'校验通过'"""
    result = runner.invoke(cli_main, ["validate"])

    assert result.exit_code == 0
    assert "校验通过" in result.output
```

### TC-CLI-004: `validate` 发现配置错误时报错

```python
def test_cli_validate_detects_config_error():
    """Given 存在格式错误的配置文件
       When 执行 `ai-export validate`
       Then 退出码≠0，显示具体错误"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建错误配置
        bad_config = tmpdir / "bad_template.yaml"
        bad_config.write_text("invalid: [yaml: broken")

        result = runner.invoke(cli_main, ["validate", "--config-dir", tmpdir])

        assert result.exit_code != 0
        assert "错误" in result.output
```

---

## 6. 边界与异常测试 (test_edge_cases.py)

### TC-EDGE-001: 大批量数据——5000行30秒内完成

```python
@pytest.mark.slow
def test_large_dataset_performance():
    """Given 5000行原始数据
       When 执行导出+分析+报告全流程
       Then 总耗时 < 30秒"""
    raw_data = generate_large_order_data(row_count=5000)

    start = time.time()
    result = run_full_pipeline(raw_data, TEMPLATE_SANZHEN)
    elapsed = time.time() - start

    assert elapsed < 30
    assert result.total_row.sales_amount > 0
```

### TC-EDGE-002: 日期范围边界处理

```python
def test_date_range_inclusive_boundaries():
    """Given 日期范围为 2026-06-01 至 2026-06-16
       When 过滤数据
       Then 6月1日00:00:00的数据包含，6月16日00:00:00的数据不包含"""
    data = [
        {"日期": "2026-06-01 00:00:00", "金额": 100},
        {"日期": "2026-06-15 23:59:59", "金额": 200},
        {"日期": "2026-06-16 00:00:00", "金额": 300},
    ]

    filtered = filter_by_date_range(data, "2026-06-01", "2026-06-16")

    assert len(filtered) == 2
    assert sum(r["金额"] for r in filtered) == 300
```

### TC-EDGE-003: 员工ID数据类型一致性

```python
def test_employee_id_type_consistency():
    """Given SQL返回的员工ID为字符串，模版定义的员工ID也是字符串
       When 进行匹配
       Then 类型不一致时仍能正确匹配"""
    sql_data = [{"员工ID": "14694", "销售金额": 500}]
    template_employees = [{"员工ID": 14694}]  # 整数类型

    matched = match_employee(sql_data, template_employees)

    assert matched[0]["销售金额"] == 500
```

### TC-EDGE-004: 查询结果包含NULL值

```python
def test_null_values_in_query_result():
    """Given SQL查询结果中某些字段为NULL
       When 执行模版分析
       Then NULL值转换为0或空字符串，不导致崩溃"""
    raw_data = [
        {"门店": None, "姓名": "测试", "员工ID": "12345", "销售金额": None},
    ]

    result = analyze_by_template(raw_data, TEMPLATE_SANZHEN)
    # 不应抛出异常
    assert result is not None
```

### TC-EDGE-005: 并发安全性

```python
def test_concurrent_template_access():
    """Given 多个线程同时读取同一模版配置
       When 并发执行分析
       Then 不出现竞态条件或数据交叉污染"""
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(load_template, "fixtures/valid_template.yaml")
            for _ in range(4)
        ]
        results = [f.result() for f in futures]

    # 所有线程返回相同模版
    assert all(r.name == results[0].name for r in results)


### TC-EDGE-006: 逐员工 SQL 对比验证 (SC-003)

```python
def test_per_employee_sales_matches_direct_sql():
    """Given 模版分析结果中的每个员工
       When 与 SQL 直接查询该员工的销售额对比
       Then 逐行精确一致"""
    raw_data = generate_mock_order_data(employee_count=10, seed=42)
    template = load_template("fixtures/mini_template.yaml")  # 10 employees

    result = analyze_by_template(raw_data, template)

    # 对每个员工，验证分析结果 = 原始数据直接求和
    for row in result.rows:
        employee_data = [d for d in raw_data if str(d["员工ID"]) == row.employee_id]
        expected_sales = sum(d["销售金额"] for d in employee_data)
        assert row.sales_amount == round(expected_sales, 2), \
            f"员工 {row.employee_id}: 分析值 {row.sales_amount} ≠ 期望值 {expected_sales}"


### TC-EDGE-007: 10 模版注册容量 (SC-004)

```python
def test_ten_template_registration_capacity(tmp_path):
    """Given 10 个不同名称的分析模版 YAML 文件
       When TemplateRegistry 加载模版目录
       Then 全部 10 个可正常注册和获取"""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    for i in range(10):
        yaml_content = f"""
name: template-{i}
display_name: 模版{i}
columns:
  - {{ title: "序号", source_field: "seq", format: "number" }}
group_by: ["片区"]
match_key:
  template_fields: ["员工ID"]
  data_fields: ["销售店员ERPID"]
employee_list:
  - {{ seq: 1, area: "测试", store: "测试店", name: "测试{i}", employee_id: "{10000+i}", department: "测试部门" }}
"""
        (templates_dir / f"template_{i}.yaml").write_text(yaml_content, encoding="utf-8")

    registry = TemplateRegistry(str(templates_dir))
    names = registry.list_all()

    assert len(names) == 10
    for i in range(10):
        t = registry.get(f"template-{i}")
        assert t.display_name == f"模版{i}"


### TC-EDGE-008: 配置错误 5 秒内返回 (SC-006)

```python
def test_config_error_returns_within_5_seconds():
    """Given 格式错误的配置文件
       When 执行配置校验
       Then 5 秒内返回明确的错误信息，不挂起不崩溃"""
    import time

    # 创建一个缺少必填字段的配置
    config = ExportConfig(
        server="",       # missing → 应触发校验错误
        database="",
        username="",
    )

    start = time.time()
    with pytest.raises(ValidationError):
        validate_export_config(config)
    elapsed = time.time() - start

    assert elapsed < 5, f"错误返回耗时 {elapsed:.2f}s，应 < 5s"
```


---

## 测试数据工厂

```python
# fixtures/factories.py

SAMPLE_ORDER_ROWS = [
    {
        "订单号": "ORD001",
        "商品ERPID": "150087",
        "成本价": 50.00,
        "销售单价": 79.80,
        "销售数量": 2,
        "销售金额": 159.60,
        "支付时间": "2026-06-05 10:30:00",
        "销售门店ID": "ST001",
        "销售门店": "保康",
        "销售店员ERPID": "14694",
        "销售店员姓名": "梅朱琳",
    },
    # ... more rows ...
]

def generate_mock_order_data(employee_count: int = 61, seed: int = 42):
    """生成随机测试数据"""
    random.seed(seed)
    rows = []
    for i in range(employee_count):
        rows.append({
            "门店": f"测试店{i}",
            "姓名": f"测试员工{i}",
            "员工ID": str(10000 + i),
            "销售金额": round(random.uniform(0, 5000), 2),
        })
    return rows

def generate_mock_analysis_result(employee_count: int = 61):
    """生成模拟分析结果"""
    result = AnalysisResult()
    for i in range(employee_count):
        result.rows.append(ResultRow(
            index=i+1,
            area="测试片区",
            store=f"测试店{i}",
            name=f"测试员工{i}",
            employee_id=str(10000+i),
            sales_amount=round(random.uniform(0, 3000), 2),
            department=f"重庆桐君阁-测试片区-测试店{i}",
        ))
    result.calculate_totals()
    return result
```

---

## 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块
pytest tests/test_config.py -v
pytest tests/test_export.py -v
pytest tests/test_analysis.py -v
pytest tests/test_report.py -v

# 运行带覆盖率报告
pytest tests/ --cov=src/ --cov-report=html

# TDD模式：监听文件变化自动运行
ptw tests/ -- -v
```

# Quickstart: AIExport 快速启动指南

**Feature**: AI 导出与分析系统
**Date**: 2026-06-22

## 前置条件

- Python 3.11+
- 可访问的 SQL Server 实例（内网）
- SQL Server 只读查询权限

## 安装

```bash
# 1. 克隆项目并进入
cd AIReportNew
git checkout AIExportNew

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -e .
# 或 pip install -r requirements.txt
```

## 配置

### 第一步：编辑导出配置

编辑 `configs/export.yaml`:

```yaml
# SQL Server 连接
server: "192.168.1.100"
port: 1433
database: "RetailDB"
username: "readonly_user"
password: "${DB_PASSWORD}"  # 或直接写密码（测试环境）

# 明细查询（支持 {{param}} 占位符）
detail_query: |
  SELECT 
      os.ThirdOrderId AS 订单号,
      ogs.ThirdMedicineId AS 商品ERPID,
      ogs.CostPrice AS 成本价,
      ogs.Price AS 销售单价,
      ogs.Num AS 销售数量,
      ogs.PayAmount AS 销售金额,
      os.FullPayTime AS 支付时间,
      os.ThirdStoreId AS 销售门店ID,
      os.ThirdStoreName AS 销售门店,
      ogs.thirdstaffid AS 销售店员ERPID,
      ogs.thirdstaffname AS 销售店员姓名
  FROM PurchaseMedicineOrder os 
  JOIN PurchaseMedicineOrderGood ogs 
    ON os.PurchaseMedicineOrderId = ogs.PurchaseMedicineOrderId 
    AND ogs.EnterpriseID = os.EnterpriseID
  WHERE os.EnterpriseID = '{{enterprise_id}}'
    AND ogs.ThirdMedicineId IN ({{medicine_ids}})
    AND os.FullPayTime >= '{{start_date}}' 
    AND os.FullPayTime < '{{end_date}}'
    AND ogs.thirdstaffid IN ({{staff_ids}})

# 汇总查询（计算总销售额，用于占比计算）
summary_query: |
  SELECT SUM(ogs.PayAmount) AS 总销售额
  FROM PurchaseMedicineOrderGood ogs 
  JOIN PurchaseMedicineOrder os 
    ON os.PurchaseMedicineOrderId = ogs.PurchaseMedicineOrderId 
    AND ogs.EnterpriseID = os.EnterpriseID
  WHERE ogs.EnterpriseID = '{{enterprise_id}}' 
    AND os.EnterpriseID = '{{enterprise_id}}'
    AND ogs.ThirdMedicineId IN ({{medicine_ids}})
    AND os.FullPayTime >= '{{start_date}} 00:00:00' 
    AND os.FullPayTime < '{{end_date}} 00:00:00'

# 查询参数
parameters:
  enterprise_id: "68288c8975fb4fa1a4b94da70b9f2765"
  start_date: "2026-06-01"
  end_date: "2026-06-16"
  medicine_ids: "'150087','215254','204080','218919','261543'"  # 完整列表...
  staff_ids: "'14061','2828','9076','12456','10767','12320'"     # 完整列表...

# 连接超时
timeout: 30

# 输出
output_dir: "output/exports"
output_filename: "export_result.xlsx"
```

### 第二步：编辑分析模版

编辑 `configs/templates/sanzhen-jiuti.yaml`:

```yaml
name: "sanzhen-jiuti"
display_name: "三诊九体培训动销及打卡学习情况"
description: "按片区→门店→员工分组，汇总6月上半月销售数据"

columns:
  - { title: "序号", source_field: "seq", format: "number", width: 6 }
  - { title: "片区", source_field: "area", format: "text", width: 10 }
  - { title: "门店", source_field: "store", format: "text", width: 15 }
  - { title: "姓名", source_field: "name", format: "text", width: 10 }
  - { title: "第三方员工ID", source_field: "employee_id", format: "text", width: 14 }
  - { title: "销售金额（6月1日-15日）", source_field: "sales_amount", format: "money", width: 18 }
  - { title: "占比", source_field: "percentage", format: "percent", width: 8 }
  - { title: "部门", source_field: "department", format: "text", width: 50 }

group_by: ["片区", "门店", "员工ID"]

match_key:
  template_fields: ["员工ID"]
  data_fields: ["销售店员ERPID"]

sort_by:
  - { field: "seq", order: "asc" }

summary_rules:
  - { type: "sum", source_field: "销售金额", target_field: "sales_amount" }
  - { type: "percentage", source_field: "sales_amount", target_field: "percentage", base_field: "total_sales" }

employee_list:
  - { seq: 1, area: "渝中", store: "保康", name: "梅朱琳", employee_id: "14694", department: "重庆桐君阁大药房连锁有限责任公司-渝中片区-重庆桐君阁大药房连锁有限责任公司保康参茸店" }
  - { seq: 2, area: "北碚", store: "北碚6店", name: "刘敏", employee_id: "6653", department: "重庆桐君阁大药房连锁有限责任公司-北碚合川片区-重庆桐君阁大药房连锁有限责任公司北碚区六店" }
  # ... 共 77 行员工数据
```

## 校验配置

```bash
# 校验所有配置文件格式和完整性
python -m src.cli validate

# 预期输出：
# ✅ export.yaml: 通过
# ✅ templates/sanzhen-jiuti.yaml: 通过
# 校验完成: 2/2 通过
```

## 执行分析

```bash
# 一键执行：导出 → 分析 → 报告
python -m src.cli run --template sanzhen-jiuti

# 预期输出：
# 🔄 [导出] 连接 SQL Server...
# ✅ [导出] 查询完成: 2345 行, 耗时 2.3s
# 🔄 [分析] 匹配模版 "三诊九体培训动销及打卡学习情况"...
# ✅ [分析] 匹配 61/61 员工, 合计 ¥37,326.00
# 🔄 [报告] 生成报告...
# ✅ [报告] output/reports/report_20260622_113000.md
# ✅ [报告] output/reports/report_20260622_113000.xlsx
# 🎉 全流程完成，耗时 5.8s
```

## 单一命令

```bash
# 仅导出
python -m src.cli export

# 仅分析（使用已导出的数据）
python -m src.cli analyze --template sanzhen-jiuti --data output/exports/export_result.xlsx

# 列出所有可用模版
python -m src.cli list-templates

# 仅生成报告（使用已分析的结果）
python -m src.cli report --template sanzhen-jiuti
```

## 查看结果

```bash
# Markdown 报告
cat output/reports/report_*.md

# Excel 报告用 Excel/WPS 打开
# output/reports/report_*.xlsx

# 日志
cat output/ai-export.log
```

## 新增模版

1. 在 `configs/templates/` 下新建 YAML 文件
2. 定义模版结构（columns, group_by, match_key, employee_list）
3. 运行 `python -m src.cli validate` 校验
4. 运行 `python -m src.cli run --template <新模版名>` 执行

## 运行测试

```bash
# 所有测试
pytest tests/ -v

# 特定模块
pytest tests/test_analysis.py -v

# TDD 模式：先确保测试失败
pytest tests/ -v --tb=short
```

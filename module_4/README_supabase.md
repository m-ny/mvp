# Module 4 + Supabase

## 结论

### 应该 push 到 GitHub 的
- `module_4/app.py`
- `module_4/test_deepseek_extract.py`
- `module_4/IO_CONTRACT.md`
- `module_4/supabase_schema.sql`
- `module_4/seed_profiles_to_supabase.py`
- `module_4/README_supabase.md`
- `module_4/supabase_writer.py`

### 不应该 push 到 GitHub 的
- `.env`
- `module_4/database_mock/profile_*.json`
- 任何真实客户数据
- 任何 Supabase 密码/密钥

### 应该放到 Supabase 的
- 团队共享的 Module 4 客户 visit 数据
- 本地已经录入完成的 `profile_*.json`
- 后续新增的真实记录

## 一次性初始化

1. 打开 Supabase 项目后台
2. 打开 `SQL Editor`
3. 把 `module_4/supabase_schema.sql` 整个复制进去执行

## 上传你本地现有记录

在项目根目录运行：

```powershell
cd c:\Users\A\Desktop\mvp
.\.venv\Scripts\Activate.ps1
python module_4\seed_profiles_to_supabase.py
```

执行成功后，本地 `module_4/database_mock/profile_*.json` 会被 upsert 到表：

- `module4_client_visits`

## 别的组该怎么用

### 看最新客户状态
直接读视图：

- `module4_clients_latest`

### 看完整历史
直接读表：

- `module4_client_visits`

## 当前表设计说明

`module4_client_visits` 同时保留：

- 原始 transcript：`raw_transcript_ca`
- 关键平铺字段：`summary / life_event / visit_purpose / client_constraints ...`
- 四层结构：`l1_client_profile / l2_constraints / l3_visit_funnel / l4_next_steps`
- 完整 JSON：`full_profile`

这样别的组既可以简单查字段，也可以直接消费完整 JSONB。

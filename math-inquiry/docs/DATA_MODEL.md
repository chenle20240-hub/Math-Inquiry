# 数据结构｜将研究索引与学习任务分开

**公开演示**是独立数据集，不是从私有库删几列得到的缩小版。[原创记录](../catalog/demo.json)是编辑入口；审核后产生三份 JSONL，随后生成 SQLite 和两个面向不同读者的页面。

| 集合 | 身份与来源 | 用途 |
|---|---|---|
| concepts | DEMO-K…、original_demo | 一张卡写明概念、成立条件、数学思想和学生动作 |
| tasks | DEMO-A… 至 DEMO-D…、original_demo | 含题意、开场语和供核对的参考解；变式自有 ID |
| links | DEMO-R…、original_demo | 两端外键为任务与概念；reason 解释为什么相关 |

例如 DEMO-D01 与 DEMO-D01-RESTRICTED 共享表示选择卡，但变量范围不同。先完成乘积式或平方形式的转换；改区间后重查取等点。不是为每一道教材题自动贴“转化”标签。[参考解与卡片](../examples/DEMO_PACK.md)

**研究库**按教材版本、章、编号节、具体出现页组织来源，而不是用章节标题或概念同名来推断版本。concepts 的主键是 knowledge_id，relationships 的 relation_id 与 from_id/to_id 表示稳定的有向关联；AI_inferred 不等于 textbook_explicit。examples 的 example_id 与提取状态一起保存。occurrences 保留不同出现位置。

中考 paper_id、question_id 与映射复合键沿用原记录。题位索引、可回看题干、答案与可练状态不等价：只从 checked_exam_questions 选练习；有知识映射不等于题面充分。9A、9B 的版本证据分别保留，不互借页码。空字段不补猜。

**身份与排序：** 统一入口把持久化 JSONL 的显式 ID 当作注册表，不从行号或展示顺序生成标识；原 ID 不改名，因此不需要旧新 ID 转换。历史 curation 行号只在原包历史流程中有效，不能重排后调用旧编号器。新数据须分配未占用的 ID、保留来源和状态；发布前核对映射与来源摘要。

[实际 schema](../scripts/schema_v11.sql) · [重建说明](rebuild.md) · [字段白名单](release-decisions.md)

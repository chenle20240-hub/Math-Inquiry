# 读取已有数据与重建是两条路径

**普通读者**直接用[快速开始](QUICKSTART.md)。公开小库已预建；没有研究 ZIP、教材 PDF 或模型 API 也能阅读任务。下面仅供维护者，命令在候选仓库根目录运行，需要 Python 3.9+ 和带 JSON 函数的 SQLite。

## 从私有 V1.1 JSONL 恢复研究库

原 ZIP 放在仓库外或忽略的 local-inputs 中。下面使用示例本地文件名；不要把教材或研究库提交到公开仓库。导入目的目录必须尚不存在。解压之前检查中文编码、大小写与 Unicode 规范化碰撞、越界及符号链接；恢复映射只存在本地。

```sh
mkdir -p build
python3 scripts/import_zip.py "local-inputs/junior_math_knowledge_base_v1.1 2.zip" build/imported > build/import-map.json
KB="build/imported/junior_math_knowledge_base_v1.1 2"
python3 scripts/database.py --dataset "$KB/data" --baseline "$KB/database/math_kb.sqlite" --output build/research.sqlite
python3 scripts/query.py --db build/research.sqlite examples 勾股定理
```

构建使用冻结的 V1.1 schema、九张教材主表 JSONL、中考三表 JSONL，派生两张映射表、索引和六个视图。所有身份沿用显式 ID，不运行按行号编号的旧 curation 构建器。不修改旧库。输入目录之外的新库在同文件系统临时目录构建，外键、完整性及可选基线对照完成后才创建目标；需要目标卷支持硬链接。原先 6 条机器绝对路径替换为相对于本地资料目录的 textbooks/文件名；版本、摘要和页码保留。原 PDF 不随附，不表示相对路径上的教材已经存在。

主键与逻辑字段、原有状态、映射和中考完整 payload 均对照。occurrences 没有声明主键，因此按**全行及重复数**比较。读取旧库也可直接用 --db；研究练习使用 exam，只允许 study_ready=1；exam-index 显示证据和状态而非未核答案。缺少材料不能据此编造原题。

## 公开数据再生成

```sh
python3 scripts/export_public.py build/public-review
```

只接受新目录。公开白名单与文件摘要见[发布清单](../release/files.json)。维护者改动源文件后，先复审来源、字段及变更，再更新清单中的对应 SHA-256；不得递归批准整个工作目录。原始数据不进入导出器。不要手改派生 JSONL、Markdown 或 SQLite。

## 从 PDF、试卷重新抽取：不是本版的一键功能

需要自己获准使用的六份完整教材、册号和哈希锁定、页文本与版式缓存、人工 curation；历史工具涉及 pypdfium2、Pillow、pdfplumber。试卷另需 Word 转换与分页预览，原 V1 校验基线也未单独提供。macOS OCR 是可选历史尝试，不是依赖。未运行整套来源抽取。若改用不同版次，应建立独立来源身份；不要关闭摘要检查或用章号推定同版。

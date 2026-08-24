"""示例文档导入脚本。

用法（在 backend/ 目录下，激活 venv 后）：
    python scripts/seed.py           # 知识库为空时导入 samples/ 示例文档
    python scripts/seed.py --force   # 强制再导入一遍（会产生重复文档）

一般不需要手动运行：后端启动时会自动 seed（SEED_ON_STARTUP=true）。
"""

import argparse
import sys
from pathlib import Path

# 允许直接以脚本方式运行：把 backend/ 加入 import 路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.rag.pipeline import RAGService  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="导入 samples/ 示例文档到知识库")
    parser.add_argument("--force", action="store_true", help="即使知识库非空也强制导入")
    args = parser.parse_args()

    service = RAGService(get_settings())
    imported = service.seed_samples(force=args.force)
    if imported:
        print(f"已导入 {len(imported)} 篇示例文档：")
        for name in imported:
            print(f"  - {name}")
    else:
        print("知识库已有文档，跳过导入（如需强制导入请加 --force）")
    print(f"当前文档数：{len(service.list_documents())}，块数：{service.store.count()}")


if __name__ == "__main__":
    main()

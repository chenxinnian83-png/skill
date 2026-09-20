# 外审协议

协议版本：`handwritten-v620`

仓库：`chenxinnian83-png/handwritten-review`

审稿根目录：`gemini-review-v62`

Local 输入：`gemini-review-v62/inbox/local/current_chunk.txt`，只提交累计 1200—1800 汉字且现场闭合的批次，目标约 1500 汉字。

Local 结果：`gemini-review-v62/result/history/<source_commit>.local.json`

Final 输入：`gemini-review-v62/inbox/final/full_chapter.txt`

Final 结果：`gemini-review-v62/result/history/<source_commit>.final.json`

统一程序：`gemini-review-v62/scripts/review.py`

文风审查只把母版作为标准。Local 可以读取已通过正文尾部检查接缝，但不得把已通过正文当成第二份文风母版。文风 PASS 必须提供目标句与母版原文的正向对应证据，不能只说“未发现问题”。

连续性审查只检查事实冲突、重复、知识边界、接缝和事件契约，不裁作文风。

每次审稿同时写当前结果与不可覆盖收据。收据文件名由阶段和输入清单哈希组成。

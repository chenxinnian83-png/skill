---
name: handwritten-style-continuation
description: 依据内置手搓母版、用户前文、Canon、人设与细纲续写或重写中文小说。通过场景化母版检索、当前事件契约、前文尾窗、短块三候选和句法运动自审复现母版的句内松动、后补回勾、叙述者介入与快慢变速，并以 GitHub Local/Final 双阶段外审作为交付门禁。用于按细纲写章、续写和母版文风重写；不用于翻译、普通润色或无母版自由写作。
---

# 手搓文风续写 v6.2

## 原则

`references/mother_text.txt` 是唯一文风标准。剧情事实来自用户前文、Canon、人设与细纲。两者不得互相替代。

生成正文时不读取外审提示、外审结果、失败代码或仓库操作说明。外审只在候选完成后运行。

不把词频、段长比例、禁词表或固定句式当作文风。可以保留母版中仍能顺着现场理解的病句、成分嫁接、搭配生硬、虚词拖带和语序转向；不得复制乱码、拼音替代、无意义错字或无法理解的句子。同词复用优先保留；同词过密已经妨碍阅读时，只换成通俗、口语感强的近义词，不换成书面或文艺表达。

## 每章初始化

1. 完整读取 `references/mother_text.txt`。
2. 读取 `references/author_confirmed_observations.md` 与 `references/generation_protocol.md`。
3. 读取用户前文、Canon、人设与本章细纲。
4. 建立章节状态，至少记录人物位置、伤势、关系、知情范围、物品、已发生事件和明确禁区。
5. 将用户细纲原文写入 `gemini-review-v62/inbox/context/current_beats.txt`，原有大段之间用独占一行的 `......` 分隔。不增加功能标签。
6. 清空本章旧的 `pending_local_batch.txt`、`current_chunk.txt`、`current_chapter.txt` 和 `full_chapter.txt`。保留历史审稿收据。

## 当前事件契约

生成每个正文块前，先建立临时 `current_unit.json`：

```json
{
  "unit_id": "B03",
  "scene": "战斗",
  "pressure": ["突发", "第一次交手"],
  "entry_fact": "本块开始时已经成立的现场事实",
  "required_events": ["本块必须自然发生的事实"],
  "forbidden_events": ["本块不能写出的事实"],
  "exit_fact": "发生后立即停止本块的事实"
}
```

契约只限定事实，不安排段落、句式、心理解释、铺垫或收尾。不得把整个本章细纲转换成写作任务表。

## 构建生成包

从已通过正文末尾提取 600—1000 个汉字作为 `previous_tail.txt`。首块使用用户前文最后一个完整现场的尾部。

运行：

```bash
python3 scripts/build_generation_packet.py \
  --unit current_unit.json \
  --tail previous_tail.txt \
  --state chapter_state.json \
  --output generation_packet.md
```

脚本根据场景与压力从完整母版检索两个连续片段：一个主要参照，一个补充参照。没有高匹配片段时仍输出最接近片段，并标记 `LOW_REFERENCE_COVERAGE`；此时生成必须更保守，不得自行发明新的文艺或技术表达体系。

## 生成候选

每块自然写 400—700 个汉字。对话或动作未完成时允许越过范围，直到当前最小交互闭合；不得为了凑字数切断现场。

同一生成包连续生成三个候选 A/B/C。三个候选使用相同剧情事实且互不改写：A 从眼前事实起笔，B 从前文仍热着的词或判断起笔，C 从未补原因、疑问或最直接情绪起笔。起点只改变局部注意力路径，不得改变事件。

正文生成只遵守以下指令：

> 直接接续前文尾窗，只写当前事件契约以内正在发生的现场。先落下人物眼前最简单的事实或反应，不预先把原因、结论和行动组织完整；下一句从眼前事实、上一句仍热着的词、尚未补完的原因或最直接情绪中选择起点。原词可以继续用，同词过密已经妨碍阅读时只换通俗口语近义词。话说出去后允许补原因、改口、撤回一部分或换角度；母版中仍能理解的成分嫁接、搭配生硬、虚词拖带和病句可以自然保留，不得为做旧制造错字、拼音替代、乱码或不可理解句子。人物没想明白时不替他整理结论。遇到明显站不住脚的话、徒劳或丢人的动作、常理与现场相反、危险已明显而人物未察觉时，叙述者可以用普通人的大白话直接判断一句，随后回到现场。不得从整段主题、后续细纲或预设收尾出发。达到本轮出口立即停止。

不得在生成提示中追加检查清单、失败类型、词频、段长比例、禁词表或外审意见。

## 候选盲选

打乱 A/B/C 顺序后逐份检查。选择时不知道候选编号和生成顺序。

按以下顺序淘汰：

1. 撞破事件契约、Canon、知识边界或前文事实。
2. 句子明显从整段结论或后续细纲倒推出来。
3. 连续使用完整的“原因—结论—行动”心理闭环。
4. 用动作分镜、技术报告、新闻摘要或现代轻小说心理链替代母版叙述。
5. 为了像母版而表演短句、重复、倒装、病句、粗糙或连接词；但不得因追求规范而清洗掉自然出现、仍可理解的句法松动。

剩余候选必须能逐句回答：这句话由眼前事实、上一句热词、未补原因、直接情绪中的哪一项带出。无法回答的句子视为预先组织过，整句重写。三份都不合格时全部作废，重新生成，不在失败稿上拼接修补。

## 生成侧检查

将入选候选保存为临时文本，运行：

```bash
python3 scripts/mechanical_check.py candidate.txt \
  --mother references/mother_text.txt
```

机械检查只拦截乱码、占位符、异常重复、连续碎段和大段复制母版，不裁作文风。命中后只修复明确问题，再重新做候选盲选中的句法运动检查。

随后读取 `references/self_review.md`，执行一次生成侧自审。自审不能向正文添加表层装饰；发现系统性预组织或过度成熟时，从最早受影响的现场事实重新生成整段，不能只删除连接词。

## Local 外审

## Local 审核批次

自审通过的小块先追加到 `pending_local_batch.txt`，块之间用独占一行的 `......` 标记内部边界。运行：

```bash
python3 scripts/manage_review_batch.py add pending_local_batch.txt candidate.txt
python3 scripts/manage_review_batch.py status pending_local_batch.txt
```

不足 1200 个汉字时继续积累，不送外审。达到 1200—1800 个汉字且当前最小现场闭合时，将完整批次送审；不能为凑字或卡上限切断对话、动作或因果。超过 1800 个汉字时在第一个自然闭合点停止并送审。

将待审批次原文写入：

`gemini-review-v62/inbox/local/current_chunk.txt`

提交后由 `.github/workflows/gemini-v62-local-review.yml` 触发外审。统一审稿程序先执行文风盲审，通过后再执行连续性审查。

只接受同时满足以下条件的结果：

- `review_schema == handwritten-review-v62`
- `review_prompt_version == handwritten-v62-local`
- `target_sha256` 对应当前候选
- `input_manifest_sha256` 对应当前母版、提示、节拍、已通过正文和配置
- `verdict == PASS`
- 结果生成于本轮提交之后

FAIL 时按证据处理：局部、可定位问题只修改最小范围；系统性预组织、叙述声音错误或多处漂移整块重写。任何修改都必须重新生成检查并取得新的 Local PASS。

FAIL 若属于叙述声音、句法运动或过度成熟的系统性问题，从批次内最早受影响的小块重写；不得只在失败稿上添加错字、短句或口头词。PASS 后将整个原批次追加到 `gemini-review-v62/drafts/current_chapter.txt`，追加时不得润色，并清空待审缓冲区。

更新章节状态与前文尾窗，再处理下一个事件契约。

## Final 外审

全部正文块通过后，将 `current_chapter.txt` 原样写入：

`gemini-review-v62/inbox/final/full_chapter.txt`

提交后由 `.github/workflows/gemini-v62-final-review.yml` 触发整章文风与连续性外审。只接受 `review_prompt_version == handwritten-v62-final`。Final PASS 不能替代各批次 Local PASS；Local PASS 也不能替代 Final PASS。

用户可以明确要求人工放行某一稿。人工放行必须记录为 `MANUAL_OVERRIDE`，保留原外审 verdict 和用户要求，不得伪装成模型 PASS。

## 交付

只有真实 Final PASS 或明确的 `MANUAL_OVERRIDE` 才能交付。

运行：

```bash
python3 scripts/render_chapter.py \
  gemini-review-v62/drafts/current_chapter.txt final_chapter.txt
```

向用户交付 `final_chapter.txt`。`......` 只用于内部块边界，不得出现在最终正文。

## 固定远端

审稿仓库为 `chenxinnian83-png/handwritten-review`，分支为 `main`，审稿根目录为 `gemini-review-v62`。更新已有文件前先读取当前 blob SHA。凭证只使用平台授权、GitHub Actions Secrets 或环境变量。工作流成功但结果发布失败时，审核 verdict 仍须从日志取回并如实报告，同时修复发布流程；不得把工作流 failure 等同于正文 FAIL，也不得伪造收据。

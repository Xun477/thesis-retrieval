# SCI 分区筛选说明

本 skill 支持按 **SCI 中科院大类分区**筛选文献：检索后只保留指定分区（如 1 区、2 区及以上）的期刊文献，并把分区标注在每条结果上。

## 分区数据从哪来

分区数据存在本地映射表 **`resources/data/journal_zones.json`**：

```json
{
  "advanced functional materials": 1,
  "sensors and actuators b: chemical": 2,
  "nanomaterials": 3
}
```

- 键 = 期刊全名（英文，小写）
- 值 = 中科院大类分区（1 = 1 区最高，2 = 2 区，3 = 3 区，4 = 4 区）

> 当前为**基础示例**，覆盖常见材料/化学/传感类期刊。你需要按自己的研究方向补充期刊。

## 首次运行（会询问你）

第一次检索且还没设置分区偏好时，会分两步询问：

**第一步：只保留哪个区及以上的文献？**

```
SCI 分区筛选：只保留哪个区及以上的文献？[1=一区 / 2=二区 / 3=三区 / 4=四区 / 0=全部, 默认 二区]: _
```

- 输入 `0`（全部）→ 本次不筛分区，下次仍会询问
- 输入 `1/2/3/4`（或中文"一区"等）→ 只保留该分区及以上的文献

**第二步（选 1-4 后）：仅此一次，还是以后都是？**

```
仅此一次，还是以后都是？[1=仅此一次 / 2=以后都是, 默认 2] _
```

- 选「以后都是」→ **以后都这样**，保存到 `resources/config/preferences.env`（`ZONE_FILTER=always` + `ZONE_MIN=N`）
- 选「仅此一次」→ **仅本次**，下次仍会询问（`ZONE_FILTER=once` + `ZONE_MIN=N`）

## 怎么改配置（以后想改分区或关闭）

三种方式，任选其一：

| 方式 | 操作 |
|------|------|
| **① 改配置文件（推荐）** | 编辑 `resources/config/preferences.env`：<br>`ZONE_MIN=1`（想要的分区，1-4）<br>`ZONE_FILTER=always`（`always`=以后都筛，`once`=仅本次）<br>改成 `ZONE_FILTER=off` 或删掉这两行 = 不筛分区 |
| **② 删除配置重新询问** | 删除 `resources/config/preferences.env`，下次运行重新弹菜单 |
| **③ 命令行临时覆盖** | 见下「命令行参数」 |

> `resources/config/preferences.env` 是本机用户配置，已加入 `.gitignore`，不会提交到仓库。

## 命令行参数

```bash
# 本次筛 2 区及以上（不保存）
python scripts/thesis_retrieval.py "query" --zone 2 --zone-mode once

# 本次筛 1 区，并保存为默认（以后都这样）
python scripts/thesis_retrieval.py "query" --zone 1 --zone-mode always

# 本次不筛分区（即使保存过偏好）
python scripts/thesis_retrieval.py "query" --zone-mode off
```

| 参数 | 取值 | 说明 |
|------|------|------|
| `--zone` | `1` / `2` / `3` / `4` | 只保留分区 ≤ 该值的文献（1 区最高） |
| `--zone-mode` | `always` / `once` / `off` | `always`=保存为默认；`once`=仅本次；`off`=本次不用 |

## 怎么补充期刊分区

1. 打开 [LetPub 期刊查询](https://www.letpub.com.cn/index.php?page=journalapp) 或中科院文献情报中心分区表官网。
2. 搜索期刊，查看「**中科院分区（大类）**」。
3. 把期刊名（英文，小写）+ 分区数字填入 `resources/data/journal_zones.json`：

```json
{
  "你的期刊全名": 2
}
```

4. 保存后下次检索自动生效。

> 匹配规则：脚本先把检索结果的期刊名小写化、压缩空格，再做**精确匹配**；如果映射表的键是结果期刊名的子串也算匹配（例如键 `advanced functional materials` 能匹配检索结果 `Advanced Functional Materials (Weinheim)`）。

## 输出说明

- 每条结果会显示 `分区=1` / `分区=2` / …；未知期刊显示 `分区=?`（**不会**被过滤掉，只是没标注）。
- 高于设定分区的文献会被过滤，打印时提示「过滤掉 N 篇」，并用 `--out` 导出 JSON 时放进 `dropped` 字段。

## 常见问题

**Q：为什么有的文献显示 `分区=?`？**
A：该期刊还没加入 `resources/data/journal_zones.json`。按上文「怎么补充期刊分区」添加即可。

**Q：无分区的文献会被删掉吗？**
A：不会。为避免漏掉重要文献，未知期刊默认**保留**并标注 `?`。如需更严格，可在补充分区表后再次检索。

**Q：分区数据能联网自动更新吗？**
A：不能。中科院分区表没有稳定的公开免费 API（实时抓 LetPub 有反爬且不稳定），因此采用本地维护方式，完全可控、无外部依赖。

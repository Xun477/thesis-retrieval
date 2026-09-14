# 贡献指南

欢迎提交 issue 和 pull request。本仓库以**中文**为主要文档语言，代码注释建议英文或中文均可。

## 开发环境

```bash
# 核心脚本无需第三方依赖，可直接运行
python scripts/paper_research.py --version

# 可选：截图 OCR 兜底需要
pip install playwright rapidocr_onnxruntime
python scripts/wos_snapshot.py --selftest
```

## 提交规范

- 版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)，变更记录写入 `CHANGELOG.md`
  （格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)）。
- 提交信息建议遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/)：
  `feat:` / `fix:` / `docs:` / `refactor:` / `chore:` 前缀。
- 提交前运行 `python -m py_compile scripts/*.py` 确保语法正确。

## 分支与 PR

- 直接向 `main` 分支提 PR 即可；改动前先描述动机与影响。
- 若改动涉及 API 密钥读取或网络请求，请注明已在本机验证的命令与输出。

## 安全注意

- **不要提交任何真实 API key**。本仓库的 `resources/config/config.env` 是空模板；
  本地填写请复制为 `resources/config/config.local.env`（已被 `.gitignore` 忽略），
  或使用环境变量。
- 不要提交 `resources/config/sources.env`、`resources/config/preferences.env`
  （本机用户配置，已被 `.gitignore` 忽略）。
- 贡献的抓取类功能需尊重目标网站条款，不得绕过登录/反爬/风控。

## 测试

暂无自动化测试套件，但每个脚本都提供运行时自检：

```bash
python scripts/paper_research.py --check-keys   # 检查 key 配置
python scripts/paper_research.py --list-sources # 列出各源信息
python scripts/wos_snapshot.py --selftest       # 自测 OCR
```

修改解析逻辑（如 `parse_record_text`）时，请用合成的 WoS 文本样例验证字段提取。

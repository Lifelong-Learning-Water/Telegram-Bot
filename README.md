# Telegram-Bot
通过Github Actions部署的开源机器人

## hsa: Hot Spot Aggregation
热点聚合，通过Actions设置定时任务，从`NEWS`等新闻API获取热点新闻，使用`translators`库对墙外媒体进行机器翻译

- hsa.py 基础版本，已经功能锁定（停用）
- hsa_v2.py 开发中，预计大量使用LLM技术（启用）
  1. 使用LLM对各平台新闻进行精确分类
  2. ……

## 其他
因资源限制，暂停运行
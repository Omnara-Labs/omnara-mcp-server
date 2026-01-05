<div align="center">

# 🛰️ Omnara MCP 服务端

**Mira Agent 的官方感官引擎，通过模型上下文协议 (MCP) 提供天气、地理位置、实时时间、记忆和搜索的标准工具集。**

[🌐 官方网站](https://www.omnara.top/) | [🐦 X (Twitter)](https://x.com/Omnara_official) | [English](./README.md)

[![协议](https://img.shields.io/badge/协议-MCP--1.0-orange)](https://modelcontextprotocol.io/)
[![许可证](https://img.shields.io/badge/许可证-Apache%202.0-blue.svg)](LICENSE)
[![Python版本](https://img.shields.io/badge/Python-3.10%2B-green)](requirements.txt)
[![由DeepSeek驱动](https://img.shields.io/badge/驱动提供-DeepSeek--V3.2-6112a3)](https://github.com/deepseek-ai/DeepSeek-V3)

</div>

---

## 1. 📖 项目简介

**Omnara MCP Server** 是 [Mira Agent](https://github.com/Omnara-Labs/mira) 项目的核心感官骨干。通过利用 **模型上下文协议 (MCP)**，它弥补了大语言模型 (LLM) 与物理世界之间的鸿沟。

该服务端允许 AI 智能体感知实时环境数据、管理长期个人记忆，并通过统一、安全的接口获取全球情报。

### 🛠️ 集成感官矩阵
* **📡 天空 (Weather)**：通过 和风天气 (QWeather) API 提供实时气象数据、空气质量及灾害预警。
* **📍 大地 (Geo)**：通过 高德地图 (Amap) API 提供逆地理编码、POI 查询及精准路线规划。
* **🧠 往事 (Memory)**：利用 Mem0 实现复杂的长期与短期记忆持久化。
* **🌐 当下 (Search)**：通过 Tavily 进行实时全球网页搜索，突破知识截止日期的限制。

---

## 2. 🚀 快速上手

### 2.1 安装

```bash
# 克隆仓库
git clone https://github.com/Omnara-Labs/omnara-mcp-server.git
cd omnara-mcp-server

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows 用户请执行: .\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2.2 配置
复制环境模板并输入您的 API 密钥：
```bash
cp .env.example .env
```

## 3. 🖥️ 生产环境部署 (systemd)
为了在树莓派或私有服务器上实现 7x24 小时稳定运行，我们建议使用 systemd 来管理进程。

### 3.1 创建服务文件
新建服务文件：/etc/systemd/system/omnara-mcp.service
```bash
[Unit]
Description=Omnara MCP 感官引擎
After=network.target

[Service]
User=您的用户名
WorkingDirectory=/项目/所在/绝对路径/omnara-mcp-server
# 确保 ExecStart 指向虚拟环境中的 python 解释器
ExecStart=/项目/所在/绝对路径/omnara-mcp-server/venv/bin/python server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 3.2 管理命令
```bash
# 重新加载配置
sudo systemctl daemon-reload

# 设置开机自启
sudo systemctl enable omnara-mcp.service

# 启动服务
sudo systemctl start omnara-mcp.service

# 查看状态与日志
sudo systemctl status omnara-mcp.service
sudo journalctl -u omnara-mcp.service -f
```

## 🤝 参与贡献
我们欢迎社区的任何贡献！无论是添加新的工具还是优化现有逻辑，欢迎随时提交 Pull Request。
<br />
<div align="center">
<p><b><a href="https://www.omnara.top/">Omnara Labs</a> - 让数字灵魂与物理世界相连</b></p>
</div>

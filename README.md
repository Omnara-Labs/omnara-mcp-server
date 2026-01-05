<div align="center">

# 🛰️ Omnara MCP Server

**The official sensory engine for Mira Agent, providing standardized tools for Weather, Geo-location, Memory, and Search via the Model Context Protocol (MCP).**

[🌐 Website](https://www.omnara.top/) | [🐦 X (Twitter)](https://x.com/Omnara_official) | [简体中文](./README_zh.md)

[![Protocol](https://img.shields.io/badge/Protocol-MCP--1.0-orange)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python-Version](https://img.shields.io/badge/Python-3.10%2B-green)](requirements.txt)
[![Powered-by-DeepSeek](https://img.shields.io/badge/Powered%20by-DeepSeek--V3.2-6112a3)](https://github.com/deepseek-ai/DeepSeek-V3)

</div>

---

## 1. 📖 Introduction

**Omnara MCP Server** serves as the sensory backbone for the [Mira Agent](https://github.com/Omnara-Labs/mira) project. By leveraging the **Model Context Protocol (MCP)**, it bridges the gap between Large Language Models (LLMs) and the physical world. 

This server allows AI agents to perceive real-time environmental data, manage long-term personal memories, and access global intelligence through a unified, secure interface.

### 🛠️ Integrated Sensory Matrix
* **📡 Sky (Weather)**: Real-time meteorological data, air quality, and disaster warnings via QWeather API.
* **📍 Earth (Geo)**: Reverse geocoding, POI search, and precise route planning via Amap (Gaode) API.
* **🧠 Past (Memory)**: Sophisticated long-term and short-term memory persistence using Mem0.
* **🌐 Present (Search)**: Real-time global web search to break the knowledge cutoff via Tavily.

---

## 2. 🚀 Quick Start

### 2.1 Installation
```bash
# Clone the repository
git clone [https://github.com/Omnara-Labs/omnara-mcp-server.git](https://github.com/Omnara-Labs/omnara-mcp-server.git)
cd omnara-mcp-server

# Setup virtual environment
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2.2 Configuration
Copy the environment template and enter your API keys:
```bash
cp .env.example .env
```

## 3. 🖥️ Production Deployment (systemd)
For 24/7 stability on devices like Raspberry Pi or private servers, we recommend using systemd to manage the process.

### 3.1 Create Service File
Create a new service file: /etc/systemd/system/omnara-mcp.service
```bash
[Unit]
Description=Omnara MCP Sensory Engine
After=network.target

[Service]
User=your_username
WorkingDirectory=/path/to/omnara-mcp-server
# Ensure ExecStart points to the python executable within your venv
ExecStart=/path/to/omnara-mcp-server/venv/bin/python server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 3.2 Management Commands
```bash
# Reload configurations
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable omnara-mcp.service

# Start the service
sudo systemctl start omnara-mcp.service

# Check status and logs
sudo systemctl status omnara-mcp.service
sudo journalctl -u omnara-mcp.service -f
```

## 🤝 Contribution<br />
We welcome contributions from the community! Whether it's adding a new sensory tool (Smart Home, Bio-metrics, etc.) or optimizing existing logic, feel free to submit a Pull Request.

<br />

<div align="center"> <p><b><a href="https://www.omnara.top/">Omnara Labs</a> - Connecting Digital Souls with the Physical World</b></p> </div>

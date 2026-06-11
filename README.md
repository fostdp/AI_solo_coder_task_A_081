# 古代中医药方剂配伍规律挖掘与现代新药发现辅助系统

基于 MongoDB + Neo4j + FastAPI + D3.js 的中医药知识图谱与数据挖掘系统。

## 系统架构

```
前端 (HTML + CSS + JavaScript + D3.js + Canvas)
        ↓ HTTP/REST API
后端 (Python FastAPI)
        ↓
┌───────┴───────┐
↓               ↓
MongoDB      Neo4j
(文档数据)   (图数据库)
```

## 功能模块

### 1. 关联网络图可视化
- Canvas + D3.js 力导向图布局
- 药物节点：按性味归经着色（温=红，寒=蓝，平=灰）
- 方剂节点：大小表示使用频率
- 病症节点：紫色标识
- 支持拖拽、缩放、悬停高亮
- 点击节点弹出详情面板

### 2. 方剂库管理
- 5000首经典方剂数据
- 按朝代、病症、药物筛选
- 方剂详情查看（药物组成、剂量、炮制方法）

### 3. 中药库管理
- 180+味中药基础数据
- 按类别、药性、归经筛选
- 中药性味归经详情

### 4. 病症库管理
- 60+种常见病症
- 病症分类浏览
- 从病症反向查找相关方剂

### 5. 配伍规律挖掘
- **Apriori 关联规则挖掘**
  - 频繁项集发现（2-5项）
  - 关联规则生成（支持度、置信度、提升度）
  - 高频药对识别
  - 角药组合（三味药）识别

- **Louvain 社区发现算法**
  - 药物社区识别
  - 协同作用药物群发现
  - 模块度计算

### 6. 新药发现辅助
- **链路预测**
  - Adamic-Adar 算法
  - 共同邻居法
  - Jaccard 系数
  - 资源分配指数
  - 优先连接法

- **靶点辅助筛选**
  - 40+个现代药理学靶点（模拟）
  - 基于共同靶点的药对推荐
  - 亲和力排序

- **药对深度分析**
  - 支持度、置信度、提升度计算
  - 药理靶点相似度分析
  - 已知方剂验证

## 项目结构

```
project/
├── backend/                    # 后端代码
│   ├── main.py                # FastAPI 主入口
│   ├── config.py              # 配置文件
│   ├── requirements.txt       # Python 依赖
│   ├── .env.example           # 环境变量示例
│   ├── models/                # 数据模型
│   │   ├── __init__.py
│   │   └── schemas.py         # Pydantic 模型
│   ├── database/              # 数据库连接
│   │   ├── __init__.py
│   │   ├── mongodb.py         # MongoDB 连接
│   │   └── neo4j_db.py        # Neo4j 连接
│   ├── api/                   # API 路由
│   │   ├── __init__.py
│   │   ├── formulas.py        # 方剂 API
│   │   ├── herbs.py           # 中药 API
│   │   ├── diseases.py        # 病症 API
│   │   ├── graph.py           # 图数据 API
│   │   ├── mining.py          # 配伍挖掘 API
│   │   └── discovery.py       # 新药发现 API
│   ├── services/              # 核心算法服务
│   │   ├── __init__.py
│   │   ├── apriori_mining.py  # Apriori 算法
│   │   ├── louvain_community.py  # Louvain 算法
│   │   └── link_prediction.py # 链路预测
│   └── data/                  # 数据导入脚本
│       ├── __init__.py
│       ├── tcm_data.py        # 基础数据（中药、病症等）
│       ├── import_mongodb.py  # MongoDB 数据导入
│       └── import_neo4j.py    # Neo4j 数据导入
└── frontend/                  # 前端代码
    ├── index.html             # 主页面
    ├── css/
    │   └── style.css          # 样式文件
    └── js/
        ├── main.js            # 主逻辑
        ├── graph.js           # 图可视化
        └── panel.js           # 详情面板
```

## 快速开始

### 1. 环境要求

- Python 3.9+
- MongoDB 4.0+
- Neo4j 4.0+
- 现代浏览器（支持ES6）

### 2. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库连接
```

### 4. 导入数据

**步骤1：导入MongoDB数据**
```bash
cd backend
python -m data.import_mongodb
```
将生成5000首方剂、180+味中药、60+种病症的模拟数据。

**步骤2：导入Neo4j图数据**
```bash
cd backend
python -m data.import_neo4j
```
构建药物-方剂-病症关联图，包含CO_OCCURS（药物共现）关系。

### 5. 启动后端服务

```bash
cd backend
python main.py
```

服务启动后访问：
- API 文档: http://localhost:8000/docs
- 前端页面: http://localhost:8000/static/index.html

### 6. 直接打开前端

也可以直接用浏览器打开 `frontend/index.html`，需要后端服务运行在 localhost:8000。

## API 接口概览

### 方剂接口
- `GET /formulas/` - 方剂列表
- `GET /formulas/{id}` - 方剂详情
- `GET /formulas/by-name/{name}` - 按名称查询
- `GET /formulas/search/by-disease` - 按病症查找
- `GET /formulas/search/by-herbs` - 按药物查找

### 中药接口
- `GET /herbs/` - 中药列表
- `GET /herbs/{id}` - 中药详情
- `GET /herbs/{id}/formulas` - 含此药的方剂
- `GET /herbs/stats/categories` - 分类统计
- `GET /herbs/{id}/targets` - 药理靶点

### 病症接口
- `GET /diseases/` - 病症列表
- `GET /diseases/{id}` - 病症详情
- `GET /diseases/{id}/formulas` - 治疗此病症的方剂
- `GET /diseases/search/formulas` - 病症反查方剂

### 图数据接口
- `GET /graph/network` - 获取网络图数据
- `GET /graph/herb-cooccurrence` - 药物共现对
- `GET /graph/disease-formulas/{disease}` - 疾病关联图
- `GET /graph/herb-formulas/{herb}` - 药物关联图
- `GET /graph/formula-detail/{formula}` - 方剂详情图

### 配伍挖掘接口
- `GET /mining/frequent-itemsets` - 频繁项集
- `GET /mining/association-rules` - 关联规则
- `GET /mining/top-herb-pairs` - 高频药对
- `GET /mining/top-herb-triplets` - 角药组合
- `GET /mining/communities` - 药物社区发现
- `GET /mining/by-disease/{disease}` - 按病症挖掘

### 新药发现接口
- `GET /discovery/link-prediction` - 链路预测
- `GET /discovery/new-pairs` - 新药对推荐
- `GET /discovery/pair-detail` - 药对详细分析
- `GET /discovery/target-based` - 靶点筛选药物
- `GET /discovery/recommend-for-disease` - 疾病推荐
- `GET /discovery/all-targets` - 所有靶点列表

## 算法说明

### Apriori 关联规则
- 支持度（Support）：项集在所有事务中出现的频率
- 置信度（Confidence）：A出现时B也出现的概率 P(B|A)
- 提升度（Lift）：P(B|A) / P(B)，大于1表示正相关

### Louvain 社区发现
- 基于模块度（Modularity）的贪心优化算法
- 两阶段迭代：节点移动 + 社区聚合
- 自动发现最优社区数量

### 链路预测算法
- **Adamic-Adar**：根据共同邻居的度加权
- **Jaccard系数**：共同邻居占所有邻居的比例
- **资源分配指数**：资源传递模型
- **优先连接**：富者愈富模型
- **综合评分**：结合结构相似度与药理靶点相似度

## 数据说明

本系统使用模拟数据进行演示：
- 中药数据基于真实的中医药理论（性味归经、分类等）
- 方剂配伍为模拟生成，不代表真实临床处方
- 药理靶点数据为模拟数据，仅用于演示算法

## 技术栈

**后端**
- FastAPI - 现代Python Web框架
- PyMongo - MongoDB驱动
- Neo4j Python Driver - Neo4j驱动
- NetworkX - 图算法库

**前端**
- D3.js v7 - 数据可视化库
- Canvas - 背景渲染
- SVG + 力导向布局 - 节点交互

**数据库**
- MongoDB - 文档型数据库，存储方剂/中药/病症详情
- Neo4j - 图数据库，存储关联关系与图查询

## 注意事项

1. 首次使用需先运行数据导入脚本
2. 确保MongoDB和Neo4j服务已启动
3. 大量数据计算可能需要较长时间
4. 模拟数据仅供研究演示使用

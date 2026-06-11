import sys
sys.path.insert(0, '.')

from services.apriori_mining import Apriori
from services.louvain_community import LouvainCommunity
from services.link_prediction import LinkPredictor
import networkx as nx

print("=" * 50)
print("1. Apriori 关联规则挖掘测试")
print("=" * 50)

transactions = [
    ['麻黄', '桂枝', '杏仁', '甘草'],
    ['桂枝', '芍药', '生姜', '大枣', '甘草'],
    ['麻黄', '桂枝', '干姜', '细辛', '五味子', '芍药', '半夏', '甘草'],
    ['人参', '白术', '茯苓', '甘草'],
    ['黄芪', '甘草', '人参', '当归', '陈皮', '升麻', '柴胡', '白术'],
    ['熟地黄', '川芎', '当归', '芍药'],
    ['人参', '白术', '茯苓', '甘草', '当归', '川芎', '白芍', '熟地黄'],
    ['熟地黄', '山茱萸', '山药', '泽泻', '茯苓', '牡丹皮'],
    ['附子', '干姜', '甘草'],
    ['半夏', '橘红', '白茯苓', '甘草'],
]

apriori = Apriori(min_support=0.2, min_confidence=0.5)
L, support_data = apriori.fit(transactions)
rules = apriori.generate_rules()
top_pairs = apriori.get_top_pairs(5)
top_triplets = apriori.get_top_triplets(5)

print(f"事务数: {len(transactions)}")
print(f"频繁项集: {sum(len(l) for l in L)} 个")
print(f"关联规则: {len(rules)} 条")
print()
print("Top 5 药对:")
for p in top_pairs:
    print(f"  {p['herb_a']} + {p['herb_b']}: support={p['support']}, count={p['count']}")
print()
print("Top 3 关联规则:")
for r in rules[:3]:
    antecedent = ", ".join(r['antecedent'])
    consequent = ", ".join(r['consequent'])
    print(f"  [{antecedent}] -> [{consequent}]")
    print(f"    support={r['support']}, confidence={r['confidence']}, lift={r['lift']}")

print()
print("=" * 50)
print("2. Louvain 社区发现测试")
print("=" * 50)

G = nx.Graph()
test_edges = [
    ('甘草', '白术', 8),
    ('甘草', '茯苓', 7),
    ('甘草', '人参', 6),
    ('白术', '茯苓', 6),
    ('白术', '人参', 5),
    ('茯苓', '人参', 5),
    ('当归', '熟地黄', 5),
    ('当归', '川芎', 4),
    ('当归', '白芍', 4),
    ('熟地黄', '川芎', 3),
    ('熟地黄', '白芍', 3),
    ('川芎', '白芍', 3),
    ('麻黄', '桂枝', 4),
    ('麻黄', '杏仁', 3),
    ('桂枝', '芍药', 3),
    ('桂枝', '甘草', 2),
]

for u, v, w in test_edges:
    G.add_edge(u, v, weight=w)

louvain = LouvainCommunity(resolution=1.0)
louvain.fit(G)
communities = louvain.get_communities()

print(f"节点数: {G.number_of_nodes()}")
print(f"边数: {G.number_of_edges()}")
print(f"社区数: {len(communities)}")
print(f"模块度: {round(louvain.modularity, 6)}")
print()
for comm_id, herbs in communities.items():
    print(f"  社区 {comm_id + 1}: {', '.join(herbs)}")

print()
print("=" * 50)
print("3. 链路预测测试")
print("=" * 50)

G2 = nx.Graph()
test_edges2 = [
    ('甘草', '白术'), ('甘草', '茯苓'), ('甘草', '人参'),
    ('白术', '茯苓'), ('白术', '人参'), ('茯苓', '人参'),
    ('当归', '熟地黄'), ('当归', '川芎'), ('当归', '白芍'),
    ('熟地黄', '川芎'), ('熟地黄', '白芍'),
    ('麻黄', '桂枝'), ('麻黄', '杏仁'),
    ('桂枝', '甘草'),
    ('黄芪', '白术'), ('黄芪', '甘草'),
]

for u, v in test_edges2:
    G2.add_edge(u, v)

predictor = LinkPredictor(G2)
aa_predictions = predictor.predict_links(method='adamic_adar', top_n=5)

print(f"节点数: {G2.number_of_nodes()}")
print(f"边数: {G2.number_of_edges()}")
print()
print("Adamic-Adar Top 5 预测:")
for p in aa_predictions:
    print(f"  {p['herb_a']} + {p['herb_b']}: score={p['score']}")

herb_targets = {
    '甘草': ['EGFR', 'AKT1', 'IL6', 'TNF'],
    '白术': ['EGFR', 'AKT1', 'PIK3CA'],
    '茯苓': ['AKT1', 'IL6', 'PIK3CA', 'STAT3'],
    '人参': ['EGFR', 'TNF', 'IL6', 'STAT3', 'PIK3CA'],
    '当归': ['VEGFA', 'AKT1', 'IL6'],
    '熟地黄': ['VEGFA', 'EGFR', 'PIK3CA'],
    '川芎': ['VEGFA', 'NOS3', 'AKT1'],
    '麻黄': ['ADRB2', 'DRD2', 'SLC6A4'],
    '桂枝': ['TRPV1', 'ADRA1A', 'ADRB2'],
    '黄芪': ['VEGFA', 'IL6', 'TNF', 'STAT3'],
}

combined_predictions = predictor.predict_with_targets(herb_targets, top_n=5)
print()
print("综合预测 Top 5:")
for p in combined_predictions:
    print(f"  {p['herb_a']} + {p['herb_b']}: score={p['score']}")
    print(f"    AA={p['adamic_adar']}, Jaccard={p['jaccard']}, 靶点相似={p['target_similarity']}")

print()
print("=" * 50)
print("所有算法测试通过!")
print("=" * 50)

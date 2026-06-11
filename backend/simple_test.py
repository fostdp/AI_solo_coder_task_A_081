import sys
sys.path.insert(0, '.')

print("Step 1: 测试 Apriori ...")
from services.apriori_mining import Apriori

transactions = [
    ['A', 'B', 'C'],
    ['A', 'B', 'D'],
    ['B', 'C', 'E'],
    ['A', 'C', 'D'],
    ['B', 'C', 'D'],
]

apriori = Apriori(min_support=0.4, min_confidence=0.6)
L, support_data = apriori.fit(transactions)
rules = apriori.generate_rules()

print(f"  事务数: {len(transactions)}")
print(f"  频繁项集: {sum(len(l) for l in L)}")
print(f"  关联规则: {len(rules)}")
print("  Apriori: OK")

print()
print("Step 2: 测试 Louvain ...")
import networkx as nx
from services.louvain_community import LouvainCommunity

G = nx.Graph()
G.add_edges_from([
    ('A', 'B'), ('A', 'C'), ('B', 'C'),
    ('D', 'E'), ('D', 'F'), ('E', 'F'),
    ('B', 'D'),
])

louvain = LouvainCommunity(random_state=42)
louvain.fit(G)
communities = louvain.get_communities()

print(f"  节点数: {G.number_of_nodes()}")
print(f"  社区数: {len(communities)}")
print(f"  模块度: {louvain.modularity}")
print("  Louvain: OK")

print()
print("Step 3: 测试 LinkPredictor ...")
from services.link_prediction import LinkPredictor

G2 = nx.Graph()
G2.add_edges_from([
    ('A', 'B'), ('A', 'C'), ('A', 'D'),
    ('B', 'C'), ('B', 'D'),
    ('C', 'D'),
    ('E', 'F'), ('E', 'G'),
    ('F', 'G'),
    ('D', 'E'),
])

predictor = LinkPredictor(G2)
aa_preds = predictor.predict_links(method='adamic_adar', top_n=3)

print(f"  节点数: {G2.number_of_nodes()}")
print(f"  预测数: {len(aa_preds)}")
for p in aa_preds:
    print(f"    {p['herb_a']} + {p['herb_b']}: {p['score']}")
print("  LinkPredictor: OK")

print()
print("All tests passed!")

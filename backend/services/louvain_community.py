import networkx as nx
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import random


class LouvainCommunity:
    def __init__(self, resolution: float = 1.0, random_state: int = 42):
        self.resolution = resolution
        self.random_state = random_state
        self.communities = {}
        self.graph = None
        self.modularity = 0.0

    def fit(self, graph: nx.Graph):
        self.graph = graph
        random.seed(self.random_state)
        
        communities = self._louvain_method(graph)
        self.communities = communities
        self.modularity = self._calculate_modularity(graph, communities)
        return communities

    def _louvain_method(self, graph: nx.Graph) -> Dict[int, int]:
        partition = {node: i for i, node in enumerate(graph.nodes())}
        
        improvement = True
        while improvement:
            improvement = False
            
            nodes = list(graph.nodes())
            random.shuffle(nodes)
            
            for node in nodes:
                current_community = partition[node]
                
                best_community = current_community
                best_increase = 0.0
                
                neighbors = list(graph.neighbors(node))
                neighbor_communities = set()
                for neighbor in neighbors:
                    neighbor_communities.add(partition[neighbor])
                
                for community in neighbor_communities:
                    if community == current_community:
                        continue
                    
                    increase = self._calculate_move_gain(graph, node, community, partition)
                    
                    if increase > best_increase:
                        best_increase = increase
                        best_community = community
                
                if best_increase > 0 and best_community != current_community:
                    partition[node] = best_community
                    improvement = True
        
        unique_communities = list(set(partition.values()))
        community_mapping = {old: new for new, old in enumerate(unique_communities)}
        final_partition = {node: community_mapping[comm] for node, comm in partition.items()}
        
        return final_partition

    def _calculate_move_gain(self, graph: nx.Graph, node, target_community, partition: Dict) -> float:
        node_weight = graph.degree(node, weight='weight') if 'weight' in graph.edges[list(graph.edges())[0]] else graph.degree(node)
        
        m = self._get_total_weight(graph) * 2
        
        k_i = node_weight
        sum_in = 0.0
        sum_tot = 0.0
        
        for n in graph.nodes():
            if partition[n] == target_community:
                if graph.has_edge(node, n):
                    if 'weight' in graph.edges[node, n]:
                        sum_in += graph.edges[node, n]['weight']
                    else:
                        sum_in += 1
                
                n_weight = graph.degree(n, weight='weight') if 'weight' in graph.edges[list(graph.edges())[0]] else graph.degree(n)
                sum_tot += n_weight
        
        delta_q = (sum_in + k_i) / m - ((sum_tot + k_i) / m) ** 2
        delta_q -= (sum_in / m - (sum_tot / m) ** 2 - (k_i / m) ** 2)
        
        return delta_q * self.resolution

    def _get_total_weight(self, graph: nx.Graph) -> float:
        if 'weight' in graph.edges[list(graph.edges())[0]]:
            return sum(data.get('weight', 1.0) for _, _, data in graph.edges(data=True))
        return graph.number_of_edges()

    def _calculate_modularity(self, graph: nx.Graph, partition: Dict[int, int]) -> float:
        m = self._get_total_weight(graph) * 2
        if m == 0:
            return 0.0
        
        communities = defaultdict(list)
        for node, comm in partition.items():
            communities[comm].append(node)
        
        Q = 0.0
        for comm, nodes in communities.items():
            for i in nodes:
                for j in nodes:
                    if i != j and graph.has_edge(i, j):
                        if 'weight' in graph.edges[i, j]:
                            A_ij = graph.edges[i, j]['weight']
                        else:
                            A_ij = 1
                    else:
                        A_ij = 0
                    
                    k_i = graph.degree(i, weight='weight') if 'weight' in graph.edges[list(graph.edges())[0]] else graph.degree(i)
                    k_j = graph.degree(j, weight='weight') if 'weight' in graph.edges[list(graph.edges())[0]] else graph.degree(j)
                    
                    Q += A_ij - (k_i * k_j) / m
        
        return Q / m

    def get_communities(self) -> Dict[int, List]:
        community_groups = defaultdict(list)
        for node, comm_id in self.communities.items():
            community_groups[comm_id].append(node)
        
        return dict(community_groups)

    def get_community_sizes(self) -> Dict[int, int]:
        communities = self.get_communities()
        return {comm_id: len(nodes) for comm_id, nodes in communities.items()}

    def get_node_community(self, node) -> int:
        return self.communities.get(node, -1)

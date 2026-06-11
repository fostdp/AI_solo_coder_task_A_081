from itertools import combinations
from typing import List, Dict, Set, Tuple
from collections import defaultdict


class Apriori:
    def __init__(self, min_support: float = 0.1, min_confidence: float = 0.5, min_lift: float = 1.0):
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_lift = min_lift
        self.freq_itemsets = {}
        self.total_transactions = 0

    def _create_c1(self, transactions: List[List[str]]) -> Set[frozenset]:
        c1 = set()
        for transaction in transactions:
            for item in transaction:
                c1.add(frozenset([item]))
        return c1

    def _scan_dataset(self, transactions: List[List[str]], candidate_sets: Set[frozenset]) -> Tuple[Dict[frozenset, float], Dict[frozenset, int]]:
        item_count = defaultdict(int)
        for transaction in transactions:
            transaction_set = frozenset(transaction)
            for candidate in candidate_sets:
                if candidate.issubset(transaction_set):
                    item_count[candidate] += 1

        num_items = float(len(transactions))
        freq_sets = {}
        support_data = {}
        for key, count in item_count.items():
            support = count / num_items
            if support >= self.min_support:
                freq_sets[key] = support
                support_data[key] = count
        return freq_sets, support_data

    def _apriori_gen(self, freq_sets: Dict[frozenset, float], k: int) -> Set[frozenset]:
        candidates = set()
        freq_list = list(freq_sets.keys())
        for i in range(len(freq_list)):
            for j in range(i + 1, len(freq_list)):
                l1 = sorted(list(freq_list[i]))
                l2 = sorted(list(freq_list[j]))
                if l1[:k - 2] == l2[:k - 2]:
                    candidates.add(freq_list[i] | freq_list[j])
        return candidates

    def fit(self, transactions: List[List[str]]):
        self.total_transactions = len(transactions)
        c1 = self._create_c1(transactions)
        l1, support_data = self._scan_dataset(transactions, c1)
        L = [l1]
        all_support_data = dict(l1)

        k = 2
        while len(L[k - 2]) > 0:
            ck = self._apriori_gen(L[k - 2], k)
            lk, support_k = self._scan_dataset(transactions, ck)
            all_support_data.update(lk)
            L.append(lk)
            k += 1

        self.freq_itemsets = all_support_data
        self.support_counts = support_data
        return L, all_support_data

    def generate_rules(self) -> List[Dict]:
        rules = []
        for freq_set in self.freq_itemsets:
            k = len(freq_set)
            if k > 1:
                for i in range(1, k):
                    for antecedent in combinations(freq_set, i):
                        antecedent_set = frozenset(antecedent)
                        consequent_set = freq_set - antecedent_set
                        if len(consequent_set) > 0:
                            support = self.freq_itemsets[freq_set]
                            confidence = support / self.freq_itemsets[antecedent_set]
                            lift = confidence / self.freq_itemsets[consequent_set]
                            
                            if confidence >= self.min_confidence and lift >= self.min_lift:
                                rules.append({
                                    "antecedent": sorted(list(antecedent_set)),
                                    "consequent": sorted(list(consequent_set)),
                                    "support": round(support, 4),
                                    "confidence": round(confidence, 4),
                                    "lift": round(lift, 4)
                                })
        
        rules.sort(key=lambda x: (-x["support"], -x["confidence"]))
        return rules

    def get_top_pairs(self, n: int = 20) -> List[Dict]:
        pairs = []
        for freq_set, support in self.freq_itemsets.items():
            if len(freq_set) == 2:
                items = sorted(list(freq_set))
                pairs.append({
                    "herb_a": items[0],
                    "herb_b": items[1],
                    "support": round(support, 4),
                    "count": int(support * self.total_transactions)
                })
        pairs.sort(key=lambda x: -x["support"])
        return pairs[:n]

    def get_top_triplets(self, n: int = 20) -> List[Dict]:
        triplets = []
        for freq_set, support in self.freq_itemsets.items():
            if len(freq_set) == 3:
                items = sorted(list(freq_set))
                triplets.append({
                    "herbs": items,
                    "support": round(support, 4),
                    "count": int(support * self.total_transactions)
                })
        triplets.sort(key=lambda x: -x["support"])
        return triplets[:n]

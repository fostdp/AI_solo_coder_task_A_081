import random
import sys
import os
from bson import ObjectId

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mongodb import get_collection
from data.tcm_data import (
    HERBS_DATA, DISEASES_DATA, DYNASTIES,
    FORMULA_NAME_PREFIXES, FORMULA_NAME_SUFFIXES,
    DOSAGE_UNITS, PREPARATIONS, PHARMACOLOGY_TARGETS
)

random.seed(42)


def generate_formula_name(index):
    if index < len(FORMULA_NAME_PREFIXES):
        prefix = FORMULA_NAME_PREFIXES[index]
        suffix = random.choice(FORMULA_NAME_SUFFIXES)
        return f"{prefix}{suffix}"
    prefix = random.choice(FORMULA_NAME_PREFIXES)
    suffix = random.choice(FORMULA_NAME_SUFFIXES)
    modifier = random.choice(["加味", "减味", "复方", "新"])
    if random.random() < 0.3:
        return f"{modifier}{prefix}{suffix}"
    num = random.randint(1, 99)
    return f"{prefix}{num}号{suffix}"


def generate_dosage(herb_name):
    if random.random() < 0.7:
        amount = round(random.uniform(3, 30), 1)
        unit = "g"
    else:
        amount = random.choice([3, 6, 9, 12, 15, 18, 24, 30])
        unit = random.choice(DOSAGE_UNITS)
    return f"{amount}{unit}"


def generate_preparation():
    if random.random() < 0.4:
        return random.choice(PREPARATIONS)
    return "生用"


def generate_herb_combination(disease_name, num_herbs=None):
    if num_herbs is None:
        num_herbs = random.randint(3, 12)
    
    num_herbs = min(num_herbs, len(HERBS_DATA))
    
    herb_indices = random.sample(range(len(HERBS_DATA)), num_herbs)
    herbs = []
    for idx in herb_indices:
        herb = HERBS_DATA[idx]
        herbs.append({
            "name": herb["name"],
            "dosage": generate_dosage(herb["name"]),
            "preparation": generate_preparation()
        })
    return herbs


def generate_formulas(count=5000):
    formulas = []
    used_names = set()
    
    for i in range(count):
        disease = random.choice(DISEASES_DATA)
        dynasty, author = random.choice(DYNASTIES)
        
        base_name = generate_formula_name(i)
        name = base_name
        counter = 1
        while name in used_names:
            name = f"{base_name}_{counter}"
            counter += 1
        used_names.add(name)
        
        num_herbs = random.choice([3, 4, 5, 5, 6, 6, 7, 7, 8, 9, 10, 12])
        herbs = generate_herb_combination(disease["name"], num_herbs)
        
        indications = [disease["name"]]
        if random.random() < 0.3:
            extra_disease = random.choice(DISEASES_DATA)
            if extra_disease["name"] not in indications:
                indications.append(extra_disease["name"])
        if random.random() < 0.15:
            extra_disease2 = random.choice(DISEASES_DATA)
            if extra_disease2["name"] not in indications:
                indications.append(extra_disease2["name"])
        
        frequency = int(random.lognormvariate(3, 1.5)) + 1
        frequency = min(frequency, 500)
        
        formula = {
            "name": name,
            "dynasty": dynasty,
            "author": author,
            "indications": indications,
            "herbs": herbs,
            "frequency": frequency,
            "source": random.choice([
                "《伤寒论》", "《金匮要略》", "《本草纲目》",
                "《太平惠民和剂局方》", "《医学心悟》",
                "《温病条辨》", "《医林改错》", "《景岳全书》",
                "《丹溪心法》", "《脾胃论》", "《河间六书》",
                "《儒门事亲》", "《本草经集注》", "《千金要方》",
                "《千金翼方》", "《外台秘要》", "《证类本草》",
                "《本草经疏》", "《本草备要》", "《本草求真》"
            ]),
            "form": random.choice(["汤剂", "丸剂", "散剂", "膏剂", "丹剂", "颗粒剂"]),
            "usage": random.choice([
                "水煎服，每日一剂",
                "共为细末，每服6-9克",
                "炼蜜为丸，每丸重9克",
                "水煎煮，去渣取汁",
                "冲服，每次一袋"
            ])
        }
        formulas.append(formula)
    
    return formulas


def generate_herb_targets():
    herb_targets = []
    for herb in HERBS_DATA:
        num_targets = random.randint(2, 15)
        targets = random.sample(PHARMACOLOGY_TARGETS, min(num_targets, len(PHARMACOLOGY_TARGETS)))
        target_list = []
        for target in targets:
            target_list.append({
                "target": target,
                "affinity": round(random.uniform(0.3, 0.95), 3),
                "effect_type": random.choice(["激动剂", "抑制剂", "拮抗剂", "调节剂"])
            })
        herb_targets.append({
            "herb_name": herb["name"],
            "targets": target_list
        })
    return herb_targets


def import_data():
    print("正在导入中药基础数据...")
    herbs_collection = get_collection("herbs")
    herbs_collection.delete_many({})
    
    for herb in HERBS_DATA:
        herb_doc = herb.copy()
        herb_doc["_id"] = ObjectId()
        herbs_collection.insert_one(herb_doc)
    
    print(f"已导入 {len(HERBS_DATA)} 味中药")
    
    print("正在导入病症数据...")
    diseases_collection = get_collection("diseases")
    diseases_collection.delete_many({})
    
    for disease in DISEASES_DATA:
        disease_doc = disease.copy()
        disease_doc["_id"] = ObjectId()
        diseases_collection.insert_one(disease_doc)
    
    print(f"已导入 {len(DISEASES_DATA)} 种病症")
    
    print("正在生成并导入方剂数据（5000首）...")
    formulas_collection = get_collection("formulas")
    formulas_collection.delete_many({})
    
    formulas = generate_formulas(5000)
    for formula in formulas:
        formula["_id"] = ObjectId()
        formulas_collection.insert_one(formula)
    
    print(f"已导入 {len(formulas)} 首方剂")
    
    print("正在导入药理靶点数据...")
    targets_collection = get_collection("herb_targets")
    targets_collection.delete_many({})
    
    herb_targets = generate_herb_targets()
    for ht in herb_targets:
        ht["_id"] = ObjectId()
        targets_collection.insert_one(ht)
    
    print(f"已导入 {len(herb_targets)} 条药理靶点数据")
    
    print("正在创建索引...")
    formulas_collection = get_collection("formulas")
    formulas_collection.create_index([("name", 1)])
    formulas_collection.create_index([("indications", 1)])
    formulas_collection.create_index([("herbs.name", 1)])
    formulas_collection.create_index([("dynasty", 1)])
    formulas_collection.create_index([("frequency", -1)])

    formulas_collection.create_index(
        [("name", "text"), ("indications", "text"), ("source", "text")],
        name="formula_text_index",
        default_language="none",
        weights={"name": 10, "indications": 5, "source": 1}
    )
    
    herbs_collection.create_index([("name", 1)], unique=True)
    herbs_collection.create_index([("category", 1)])
    herbs_collection.create_index([("nature", 1)])
    herbs_collection.create_index([("meridians", 1)])
    
    diseases_collection.create_index([("name", 1)], unique=True)
    diseases_collection.create_index([("category", 1)])
    
    targets_collection.create_index([("herb_name", 1)], unique=True)
    
    print("数据导入完成！")


if __name__ == "__main__":
    import_data()

import ast
import os
import sys

def check_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def main():
    files = [
        'main.py',
        'config.py',
        'models/schemas.py',
        'database/mongodb.py',
        'database/neo4j_db.py',
        'services/apriori_mining.py',
        'services/louvain_community.py',
        'services/link_prediction.py',
        'api/formulas.py',
        'api/herbs.py',
        'api/diseases.py',
        'api/graph.py',
        'api/mining.py',
        'api/discovery.py',
        'data/tcm_data.py',
        'data/import_mongodb.py',
        'data/import_neo4j.py',
    ]
    
    all_ok = True
    print("Python 语法检查")
    print("=" * 50)
    
    for f in files:
        if os.path.exists(f):
            ok, error = check_file(f)
            if ok:
                print(f"  ✓ {f}")
            else:
                print(f"  ✗ {f}")
                print(f"    错误: {error}")
                all_ok = False
        else:
            print(f"  ? {f} (文件不存在)")
    
    print("=" * 50)
    if all_ok:
        print("所有文件语法检查通过!")
    else:
        print("存在语法错误，请检查!")
        sys.exit(1)

if __name__ == '__main__':
    main()

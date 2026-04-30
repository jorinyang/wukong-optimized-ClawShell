#!/usr/bin/env python3
"""
ClawShell模块API探测脚本
激进方案：探测每个模块的真实API，找到实际可用的类和方法
"""
import sys
import traceback
from pathlib import Path

# ClawShell路径
CLAWSHELL_PATH = Path(r"C:\Users\Aorus\.ClawShell")
sys.path.insert(0, str(CLAWSHELL_PATH))

def probe_module(module_path: str, module_name: str = None) -> dict:
    """探测单个模块的API"""
    result = {
        "module": module_path,
        "success": False,
        "classes": [],
        "functions": [],
        "errors": []
    }
    
    try:
        if module_name:
            result["import_result"] = __import__(module_name, fromlist=[''])
        else:
            # 从路径推断模块名
            module_name = module_path.replace("/", ".").replace("\\", ".").replace("lib.", "lib.")
            result["import_result"] = __import__(module_name, fromlist=[''])
        
        result["success"] = True
        
        # 获取所有类和函数
        module = result["import_result"]
        for attr_name in dir(module):
            if not attr_name.startswith("_"):
                attr = getattr(module, attr_name)
                if callable(attr) and not isinstance(attr, type):
                    result["functions"].append(attr_name)
                elif isinstance(attr, type):
                    # 探测类的方法
                    methods = [m for m in dir(attr) if not m.startswith("_") and callable(getattr(attr, m, None))]
                    result["classes"].append({
                        "name": attr_name,
                        "methods": methods[:10],  # 只取前10个方法
                        "bases": [b.__name__ for b in getattr(attr, "__bases__", [])]
                    })
                    
    except Exception as e:
        result["errors"].append(f"{type(e).__name__}: {str(e)}")
        result["traceback"] = traceback.format_exc()
    
    return result

def probe_layer(layer_name: str) -> list:
    """探测整个layer的所有模块"""
    layer_path = CLAWSHELL_PATH / "lib" / layer_name
    results = []
    
    if not layer_path.exists():
        return [{"error": f"Layer {layer_name} not found"}]
    
    for py_file in layer_path.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        
        module_path = f"lib.{layer_name}.{py_file.stem}"
        print(f"Probing: {module_path}...")
        
        result = probe_module(str(py_file), module_path)
        results.append(result)
    
    return results

def main():
    print("=" * 60)
    print("ClawShell 模块 API 探测报告")
    print("=" * 60)
    
    all_results = {}
    
    # 探测各层
    for layer in ["layer1", "layer2", "layer3", "layer4"]:
        print(f"\n{'='*60}")
        print(f"探测 {layer.upper()} 模块...")
        print("=" * 60)
        
        results = probe_layer(layer)
        all_results[layer] = results
        
        # 统计
        success_count = sum(1 for r in results if r.get("success"))
        print(f"\n{layer} 统计: {success_count}/{len(results)} 模块可用")
        
        # 显示成功的模块
        for r in results:
            if r.get("success"):
                classes = [c["name"] for c in r.get("classes", [])]
                print(f"  ✓ {r['module']}: {classes}")
            else:
                print(f"  ✗ {r['module']}: {r.get('errors', ['Unknown error'])}")
    
    # 输出总结
    print("\n" + "=" * 60)
    print("可用API汇总")
    print("=" * 60)
    
    for layer, results in all_results.items():
        print(f"\n{layer.upper()}:")
        for r in results:
            if r.get("success") and r.get("classes"):
                for cls in r["classes"]:
                    print(f"  - {cls['name']}: {cls['methods']}")
    
    return all_results

if __name__ == "__main__":
    main()

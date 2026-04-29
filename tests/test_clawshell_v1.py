#!/usr/bin/env python3
"""
ClawShell v1.0 - 集成测试
==========================
验证所有模块可导入
"""

import sys
import os
from pathlib import Path
import importlib

# Setup path - clawshell_v1/lib is directly importable
CLAWSHELL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(CLAWSHELL_ROOT))

def test_import(module_name, display_name=None):
    """测试模块导入"""
    display_name = display_name or module_name
    try:
        mod = importlib.import_module(module_name)
        print(f"✅ {display_name}")
        return True
    except Exception as e:
        print(f"❌ {display_name}: {e}")
        return False

def main():
    print("=" * 60)
    print("ClawShell v1.0 - 集成测试")
    print("=" * 60)
    
    results = []
    
    # Core层测试
    print("\n[Core Layer]")
    results.append(test_import("lib.core.eventbus", "lib.core.eventbus"))
    results.append(test_import("lib.core.genome", "lib.core.genome"))
    results.append(test_import("lib.core.strategy", "lib.core.strategy"))
    
    # Layer1测试
    print("\n[Layer1 - 自感知]")
    results.append(test_import("lib.layer1", "lib.layer1"))
    
    # Layer2测试
    print("\n[Layer2 - 自适应]")
    results.append(test_import("lib.layer2", "lib.layer2"))
    
    # Layer3测试
    print("\n[Layer3 - 自组织]")
    results.append(test_import("lib.layer3", "lib.layer3"))
    
    # Layer4测试
    print("\n[Layer4 - 集群]")
    results.append(test_import("lib.layer4", "lib.layer4"))
    
    # Bridge测试
    print("\n[Bridge]")
    results.append(test_import("lib.bridge.hermes", "lib.bridge.hermes"))
    results.append(test_import("lib.bridge.external", "lib.bridge.external"))
    
    # 总结
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"结果: {passed}/{total} 通过")
    
    if passed == total:
        print("✅ 所有测试通过!")
        return 0
    else:
        print(f"⚠️  {total - passed} 个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())

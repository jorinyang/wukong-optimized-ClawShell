#!/usr/bin/env python3
"""
mempalace_cli.py — MemPalace 快速预热与健康检查工具
=====================================================
在模型下载完成后执行快速验证，或在网络良好时手动触发模型预热。

用法:
    python mempalace_cli.py check      # 健康检查
    python mempalace_cli.py warmup     # 预热（触发模型下载）
    python mempalace_cli.py init       # 初始化 palace 目录
    python mempalace_cli.py stats      # 显示统计信息
"""
import os
import sys

# 添加 ClawShell 到路径
sys.path.insert(0, r'C:\Users\Aorus\.ClawShell')

from lib.bridge.mempalace_bridge import MemPalaceBridge
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('mempalace_cli')


def cmd_check():
    """健康检查"""
    print("\n=== MemPalace 健康检查 ===\n")
    bridge = MemPalaceBridge()
    health = bridge.health_check()
    
    print(f"桥接层就绪:     {health['bridge_ready']}")
    print(f"MemPalace 可用: {health['palace_available']}")
    print(f"Palace 连接:    {health['palace_connected']}")
    print(f"知识图谱连接:   {health['kg_connected']}")
    print(f"搜索引擎就绪:   {health['searcher_ready']}")
    print(f"Genome 挂载:    {health['genome_mounted']}")
    print(f"已注册 Agent:   {health['agents_registered'] or '无'}")
    print(f"Palace 目录:    {health['palace_dir']}")
    print(f"知识图谱路径:   {health['kg_path']}")
    
    if not bridge.is_ready():
        print("\n⚠️  桥接层未就绪，请先运行 `python mempalace_cli.py warmup`")
        return 1
    
    return 0


def cmd_warmup():
    """预热 - 触发模型下载"""
    print("\n=== MemPalace 预热（模型下载）===\n")
    print("这将触发 ONNX embedding 模型下载（约 79MB）...")
    print("如果下载速度慢，可以中断后稍后重试。\n")
    
    bridge = MemPalaceBridge()
    bridge.init()
    
    if bridge.is_ready():
        print("\n✅ 预热成功！桥接层已就绪。")
        return 0
    else:
        print("\n❌ 预热失败。请检查网络连接后重试。")
        print("提示: 可以设置代理环境变量 `set https_proxy=http://proxy:port`")
        return 1


def cmd_init():
    """初始化 palace 目录"""
    print("\n=== 初始化 MemPalace Palace ===\n")
    
    palace_dir = os.path.expanduser("~/.mempalace/clawshell")
    os.makedirs(palace_dir, exist_ok=True)
    
    bridge = MemPalaceBridge(palace_dir=palace_dir)
    if bridge.init():
        print(f"✅ Palace 初始化成功: {palace_dir}")
        return 0
    else:
        print(f"❌ Palace 初始化失败")
        return 1


def cmd_stats():
    """显示统计信息"""
    print("\n=== MemPalace 统计信息 ===\n")
    
    bridge = MemPalaceBridge()
    if not bridge.is_ready():
        print("桥接层未就绪，请先运行 warmup")
        return 1
    
    try:
        # 获取 palace 统计
        from mempalace.palace import get_collection
        collection = get_collection(bridge.palace_dir, create=False)
        drawer_count = collection.count()
        print(f"记忆抽屉数量: {drawer_count}")
        
        # 获取知识图谱统计
        if bridge._kg:
            kg_stats = bridge._kg.stats()
            print(f"知识图谱事实数: {kg_stats.get('triple_count', 'N/A')}")
            print(f"知识图谱实体数: {kg_stats.get('entity_count', 'N/A')}")
        
    except Exception as e:
        print(f"获取统计信息失败: {e}")
        return 1
    
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 0
    
    cmd = sys.argv[1].lower()
    
    commands = {
        'check': cmd_check,
        'warmup': cmd_warmup,
        'init': cmd_init,
        'stats': cmd_stats,
    }
    
    if cmd not in commands:
        print(f"未知命令: {cmd}")
        print("可用命令: check, warmup, init, stats")
        return 1
    
    return commands[cmd]()


if __name__ == '__main__':
    sys.exit(main())

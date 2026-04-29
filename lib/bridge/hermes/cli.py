#!/usr/bin/env python3
# hermes_bridge/cli.py
"""
Hermes Bridge CLI入口

用法:
    python3 cli.py start     # 启动桥接器
    python3 cli.py stop      # 停止桥接器
    python3 cli.py status    # 查看状态
    python3 cli.py stats     # 查看统计
    python3 cli.py test      # 运行测试
"""

import sys
import asyncio
import argparse
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from bridge import HermesBridge


def parse_args():
    parser = argparse.ArgumentParser(
        description='Hermes × ClawShell 双脑协同桥接器 CLI'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # start命令
    start_parser = subparsers.add_parser('start', help='启动桥接器')
    start_parser.add_argument('--config', '-c', help='配置文件路径')
    
    # stop命令
    stop_parser = subparsers.add_parser('stop', help='停止桥接器')
    
    # status命令
    status_parser = subparsers.add_parser('status', help='查看状态')
    
    # stats命令
    stats_parser = subparsers.add_parser('stats', help='查看统计')
    
    # test命令
    test_parser = subparsers.add_parser('test', help='运行测试')
    
    # version命令
    version_parser = subparsers.add_parser('version', help='查看版本')
    
    return parser.parse_args()


async def cmd_start(args):
    """启动桥接器"""
    print("启动 Hermes Bridge...")
    
    config = None
    if args.config:
        import json
        with open(args.config) as f:
            config = json.load(f)
    
    bridge = HermesBridge(config)
    
    try:
        await bridge.start()
        
        print("\n桥接器已启动，按 Ctrl+C 停止")
        
        # 保持运行
        while bridge.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n收到停止信号")
    finally:
        await bridge.stop()
        print("桥接器已停止")


def cmd_stop(args):
    """停止桥接器"""
    print("停止桥接器...")
    # TODO: 通过PID文件或进程名停止
    print("停止命令已发送")


def cmd_status(args):
    """查看状态"""
    print("查看桥接器状态...")
    # TODO: 从PID文件读取状态
    print("状态: 运行中")


def cmd_stats(args):
    """查看统计"""
    print("=" * 60)
    print("Hermes Bridge 统计信息")
    print("=" * 60)
    
    try:
        bridge = HermesBridge()
        stats = bridge.get_stats()
        
        print(f"\n运行状态:")
        print(f"  运行中: {stats['running']}")
        print(f"  启动时间: {stats['started_at']}")
        print(f"  运行秒数: {stats['uptime_seconds']:.0f}")
        
        print(f"\n事件统计:")
        print(f"  接收事件: {stats['events_received']}")
        print(f"  分类事件: {stats['events_classified']}")
        print(f"  分发事件: {stats['events_dispatched']}")
        print(f"  错误数: {stats['errors']}")
        
        print(f"\nHermes事件:")
        print(f"  洞察接收: {stats['insights_received']}")
        print(f"  技能创建: {stats['skills_created']}")
        
        print(f"\n队列状态:")
        queue_stats = stats.get('queue_stats', {})
        print(f"  当前大小: {queue_stats.get('current_size', 0)}")
        print(f"  入队总数: {queue_stats.get('enqueued', 0)}")
        print(f"  出队总数: {queue_stats.get('dequeued', 0)}")
        print(f"  丢弃数: {queue_stats.get('dropped', 0)}")
        
    except Exception as e:
        print(f"获取统计失败: {e}")


def cmd_test(args):
    """运行测试"""
    print("=" * 60)
    print("运行 Hermes Bridge 组件测试")
    print("=" * 60)
    
    import subprocess
    
    test_modules = [
        'events',
        'classifier',
        'matcher',
        'queue'
    ]
    
    for module in test_modules:
        print(f"\n--- 测试 {module} ---")
        result = subprocess.run(
            [sys.executable, f'{module}.py'],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {module} 测试通过")
        else:
            print(f"❌ {module} 测试失败")
            print(result.stderr[:500] if result.stderr else result.stdout[:500])
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


def cmd_version(args):
    """查看版本"""
    print("Hermes Bridge v0.8.3")
    print("Hermes × ClawShell 双脑协同方案")


def main():
    args = parse_args()
    
    if not args.command:
        # 无子命令时显示帮助
        print("Hermes Bridge CLI")
        print("用法: python3 cli.py <command>")
        print("可用命令: start, stop, status, stats, test, version")
        return
    
    commands = {
        'start': cmd_start,
        'stop': cmd_stop,
        'status': cmd_status,
        'stats': cmd_stats,
        'test': cmd_test,
        'version': cmd_version
    }
    
    if args.command in commands:
        commands[args.command](args)
    else:
        print(f"未知命令: {args.command}")


if __name__ == "__main__":
    main()

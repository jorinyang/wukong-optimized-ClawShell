#!/usr/bin/env python3
"""
OpenClaw 消息队列异步处理器
解决主会话执行长任务时消息阻塞问题
架构: 钉钉/微信消息 → OpenClaw接收 → 消息队列(文件系统) → 异步处理器 → 任务分发
"""

import os
import sys
import json
import time
import shutil
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import threading
import signal

# 配置
BASE_DIR = Path(os.path.expanduser("~/.openclaw"))
INBOX_DIR = BASE_DIR / "inbox"
PENDING_DIR = INBOX_DIR / "pending"
PROCESSING_DIR = INBOX_DIR / "processing"
COMPLETED_DIR = INBOX_DIR / "completed"
FAILED_DIR = INBOX_DIR / "failed"
LOGS_DIR = BASE_DIR / "logs"

# 扫描间隔（秒）
SCAN_INTERVAL = 5
# 子任务最大执行时间（秒）
MAX_SUBTASK_DURATION = 30
# 最大重试次数
MAX_RETRIES = 3

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "message_queue.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("MessageQueue")


class Priority(Enum):
    """任务优先级"""
    P0 = 0  # 紧急 - 立即处理
    P1 = 1  # 高优先级 - 优先处理
    P2 = 2  # 普通 - 按顺序处理
    
    def __lt__(self, other):
        return self.value < other.value


@dataclass
class Task:
    """任务数据结构"""
    id: str
    message_id: str
    content: str
    priority: Priority
    source: str  # dingtalk, wechat, etc.
    sender_id: str
    sender_name: str
    timestamp: str
    status: str  # pending, processing, completed, failed
    retry_count: int = 0
    subtasks: List[Dict] = None
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: str = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    def __post_init__(self):
        if self.subtasks is None:
            self.subtasks = []
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['priority'] = self.priority.name
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Task':
        data['priority'] = Priority[data.get('priority', 'P2')]
        return cls(**data)
    
    def save(self, directory: Path):
        """保存任务到文件"""
        file_path = directory / f"{self.id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, file_path: Path) -> 'Task':
        """从文件加载任务"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return cls.from_dict(json.load(f))


class TaskSplitter:
    """任务拆分器 - 将长任务拆分为可中断的子任务"""
    
    @staticmethod
    def is_long_task(content: str) -> bool:
        """判断是否为长任务"""
        # 基于内容长度和关键词判断
        long_keywords = [
            "分析", "报告", "文档", "完整", "详细", "全面", "系统",
            "开发", "搭建", "实现", "迁移", "重构", "优化", "部署"
        ]
        content_lower = content.lower()
        keyword_matches = sum(1 for kw in long_keywords if kw in content_lower)
        
        # 内容较长 或 包含多个长任务关键词
        return len(content) > 100 or keyword_matches >= 2
    
    @staticmethod
    def split_task(task: Task) -> List[Task]:
        """将长任务拆分为子任务"""
        content = task.content
        subtasks = []
        
        # 分析任务类型，生成子任务
        subtask_types = TaskSplitter._analyze_subtasks(content)
        
        for idx, subtask_type in enumerate(subtask_types):
            subtask_id = f"{task.id}_sub_{idx}"
            subtask = Task(
                id=subtask_id,
                message_id=task.message_id,
                content=f"[{subtask_type['phase']}] {subtask_type['description']}",
                priority=task.priority,
                source=task.source,
                sender_id=task.sender_id,
                sender_name=task.sender_name,
                timestamp=task.timestamp,
                status="pending",
                retry_count=0
            )
            subtasks.append(subtask)
        
        # 如果没有识别出子任务类型，按内容分割
        if not subtasks:
            subtasks = TaskSplitter._split_by_content(task)
        
        return subtasks
    
    @staticmethod
    def _analyze_subtasks(content: str) -> List[Dict]:
        """分析任务内容，识别子任务阶段"""
        phases = []
        content_lower = content.lower()
        
        # 分析阶段
        if any(kw in content_lower for kw in ["分析", "调研", "研究", "评估"]):
            phases.append({
                "phase": "分析",
                "description": "需求分析与背景调研",
                "estimated_duration": 20
            })
        
        # 设计阶段
        if any(kw in content_lower for kw in ["设计", "架构", "方案", "规划"]):
            phases.append({
                "phase": "设计",
                "description": "方案设计与架构规划",
                "estimated_duration": 25
            })
        
        # 实现阶段
        if any(kw in content_lower for kw in ["开发", "实现", "搭建", "编写", "创建"]):
            phases.append({
                "phase": "实现",
                "description": "核心功能开发与实现",
                "estimated_duration": 30
            })
        
        # 优化阶段
        if any(kw in content_lower for kw in ["优化", "改进", "完善", "调整"]):
            phases.append({
                "phase": "优化",
                "description": "功能优化与细节完善",
                "estimated_duration": 20
            })
        
        # 验证阶段
        if any(kw in content_lower for kw in ["测试", "验证", "检查", "确认"]):
            phases.append({
                "phase": "验证",
                "description": "测试验证与质量检查",
                "estimated_duration": 15
            })
        
        # 交付阶段
        phases.append({
            "phase": "交付",
            "description": "成果汇总与交付",
            "estimated_duration": 10
        })
        
        return phases
    
    @staticmethod
    def _split_by_content(task: Task) -> List[Task]:
        """按内容长度分割任务"""
        content = task.content
        # 简单的按句子分割策略
        sentences = content.replace('。', '|').replace('？', '|').replace('！', '|').split('|')
        sentences = [s.strip() for s in sentences if s.strip()]
        
        subtasks = []
        chunk_size = max(1, len(sentences) // 3)  # 至少分成3份
        
        for i in range(0, len(sentences), chunk_size):
            chunk = sentences[i:i + chunk_size]
            subtask_id = f"{task.id}_chunk_{i // chunk_size}"
            subtask = Task(
                id=subtask_id,
                message_id=task.message_id,
                content=f"[步骤 {i // chunk_size + 1}] " + "，".join(chunk),
                priority=task.priority,
                source=task.source,
                sender_id=task.sender_id,
                sender_name=task.sender_name,
                timestamp=task.timestamp,
                status="pending",
                retry_count=0
            )
            subtasks.append(subtask)
        
        return subtasks


class MessageQueueProcessor:
    """消息队列处理器"""
    
    def __init__(self):
        self.running = False
        self.current_task: Optional[Task] = None
        self.processed_count = 0
        self.failed_count = 0
        self._setup_directories()
        self._setup_signal_handlers()
    
    def _setup_directories(self):
        """确保目录结构存在"""
        for directory in [INBOX_DIR, PENDING_DIR, PROCESSING_DIR, COMPLETED_DIR, FAILED_DIR, LOGS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"目录已就绪: {directory}")
    
    def _setup_signal_handlers(self):
        """设置信号处理"""
        def signal_handler(signum, frame):
            logger.info(f"接收到信号 {signum}，准备停止处理器...")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def create_task(self, content: str, source: str, sender_id: str, 
                   sender_name: str, message_id: str = "",
                   priority: Priority = Priority.P2) -> Task:
        """创建新任务"""
        task_id = hashlib.md5(
            f"{message_id}:{content}:{time.time()}".encode()
        ).hexdigest()[:16]
        
        task = Task(
            id=task_id,
            message_id=message_id,
            content=content,
            priority=priority,
            source=source,
            sender_id=sender_id,
            sender_name=sender_name,
            timestamp=datetime.now().isoformat(),
            status="pending"
        )
        
        # 判断是否需要拆分
        if TaskSplitter.is_long_task(content):
            logger.info(f"任务 {task_id} 识别为长任务，进行拆分")
            subtasks = TaskSplitter.split_task(task)
            task.subtasks = [s.to_dict() for s in subtasks]
            # 保存子任务
            for subtask in subtasks:
                subtask.save(PENDING_DIR)
                logger.info(f"子任务已创建: {subtask.id}")
        
        task.save(PENDING_DIR)
        logger.info(f"任务已创建: {task_id}, 优先级: {priority.name}")
        return task
    
    def get_pending_tasks(self) -> List[Task]:
        """获取所有待处理任务，按优先级排序"""
        tasks = []
        for task_file in PENDING_DIR.glob("*.json"):
            try:
                task = Task.load(task_file)
                if task.status == "pending":
                    tasks.append(task)
            except Exception as e:
                logger.error(f"加载任务文件失败 {task_file}: {e}")
        
        # 按优先级排序（P0优先）
        tasks.sort(key=lambda t: t.priority)
        return tasks
    
    def move_task(self, task: Task, target_dir: Path):
        """移动任务文件到目标目录"""
        source_file = PENDING_DIR / f"{task.id}.json"
        if not source_file.exists():
            source_file = PROCESSING_DIR / f"{task.id}.json"
        
        target_file = target_dir / f"{task.id}.json"
        
        if source_file.exists():
            shutil.move(str(source_file), str(target_file))
            task.save(target_dir)
    
    def process_task(self, task: Task) -> bool:
        """处理单个任务"""
        logger.info(f"开始处理任务: {task.id}, 内容: {task.content[:50]}...")
        
        task.status = "processing"
        task.started_at = datetime.now().isoformat()
        task.save(PROCESSING_DIR)
        
        try:
            # 根据任务内容决定处理方式
            if task.content.startswith("[步骤") or "[" in task.content:
                # 子任务处理
                result = self._execute_subtask(task)
            else:
                # 普通任务处理 - 调用OpenClaw处理
                result = self._dispatch_to_agent(task)
            
            task.status = "completed"
            task.result = result
            task.completed_at = datetime.now().isoformat()
            task.save(COMPLETED_DIR)
            
            # 移动到completed目录
            self.move_task(task, COMPLETED_DIR)
            
            logger.info(f"任务完成: {task.id}")
            self.processed_count += 1
            return True
            
        except Exception as e:
            logger.error(f"任务处理失败 {task.id}: {e}")
            task.retry_count += 1
            task.error = str(e)
            
            if task.retry_count >= MAX_RETRIES:
                task.status = "failed"
                task.save(FAILED_DIR)
                self.move_task(task, FAILED_DIR)
                self.failed_count += 1
            else:
                task.status = "pending"
                task.save(PENDING_DIR)
            
            return False
    
    def _execute_subtask(self, task: Task) -> str:
        """执行子任务"""
        logger.info(f"执行子任务: {task.content[:50]}...")
        # 子任务执行逻辑 - 实际调用Agent处理
        # 这里模拟处理过程
        time.sleep(0.5)  # 模拟处理时间
        return f"子任务完成: {task.content[:50]}"
    
    def _dispatch_to_agent(self, task: Task) -> str:
        """分发任务给Agent处理"""
        logger.info(f"分发任务给Agent: {task.content[:50]}...")
        
        # 构建调用OpenClaw的命令
        # 这里使用subprocess调用openclaw CLI或API
        # 实际实现需要根据OpenClaw的具体接口调整
        
        # 模拟Agent处理
        # 实际应该调用: openclaw sessions_send 或其他API
        agent_mapping = {
            "dev": ["开发", "代码", "程序", "系统", "API", "脚本", "bug", "修复", "数据库", "接口"],
            "lab": ["架构", "方案", "分析", "设计", "规划", "咨询", "策略", "研究", "调研"],
            "doc": ["写作", "文章", "文案", "文档", "手册", "指南", "教程"],
            "pub": ["发布", "推送", "同步", "排版", "小红书", "公众号", "知乎"],
            "lib": ["归档", "检索", "查询", "资料", "笔记", "整理", "分类"]
        }
        
        # 简单的路由逻辑
        content_lower = task.content.lower()
        target_agent = "ceo"  # 默认路由给CEO
        
        for agent, keywords in agent_mapping.items():
            if any(kw in content_lower for kw in keywords):
                target_agent = agent
                break
        
        logger.info(f"任务路由到Agent: {target_agent}")
        
        # 记录路由结果
        return f"任务已路由至 {target_agent} Agent处理"
    
    def run(self):
        """主运行循环"""
        logger.info("=" * 60)
        logger.info("OpenClaw 消息队列处理器启动")
        logger.info("=" * 60)
        logger.info(f"扫描间隔: {SCAN_INTERVAL}秒")
        logger.info(f"最大子任务时长: {MAX_SUBTASK_DURATION}秒")
        logger.info(f"待处理目录: {PENDING_DIR}")
        logger.info(f"处理中目录: {PROCESSING_DIR}")
        logger.info(f"已完成目录: {COMPLETED_DIR}")
        logger.info("=" * 60)
        
        self.running = True
        
        while self.running:
            try:
                # 扫描待处理任务
                pending_tasks = self.get_pending_tasks()
                
                if pending_tasks:
                    logger.info(f"发现 {len(pending_tasks)} 个待处理任务")
                    
                    # 按优先级处理
                    for task in pending_tasks:
                        if not self.running:
                            break
                        
                        self.current_task = task
                        self.process_task(task)
                        self.current_task = None
                        
                        # 每个任务处理后短暂休息，避免CPU占用过高
                        time.sleep(0.1)
                
                # 等待下一次扫描
                time.sleep(SCAN_INTERVAL)
                
            except Exception as e:
                logger.error(f"处理器主循环异常: {e}")
                time.sleep(SCAN_INTERVAL)
        
        logger.info("处理器已停止")
        logger.info(f"统计: 成功处理 {self.processed_count} 个任务, 失败 {self.failed_count} 个任务")
    
    def stop(self):
        """停止处理器"""
        self.running = False


class QueueStats:
    """队列统计信息"""
    
    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """获取队列统计"""
        stats = {
            "pending": len(list(PENDING_DIR.glob("*.json"))),
            "processing": len(list(PROCESSING_DIR.glob("*.json"))),
            "completed": len(list(COMPLETED_DIR.glob("*.json"))),
            "failed": len(list(FAILED_DIR.glob("*.json"))),
            "timestamp": datetime.now().isoformat()
        }
        return stats
    
    @staticmethod
    def print_stats():
        """打印统计信息"""
        stats = QueueStats.get_stats()
        print("\n" + "=" * 40)
        print("消息队列统计")
        print("=" * 40)
        print(f"待处理: {stats['pending']}")
        print(f"处理中: {stats['processing']}")
        print(f"已完成: {stats['completed']}")
        print(f"失败:   {stats['failed']}")
        print(f"时间:   {stats['timestamp']}")
        print("=" * 40 + "\n")


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenClaw 消息队列处理器")
    parser.add_argument("--daemon", "-d", action="store_true", help="后台模式运行")
    parser.add_argument("--stats", "-s", action="store_true", help="显示统计信息")
    parser.add_argument("--add", "-a", type=str, help="添加测试任务")
    parser.add_argument("--priority", "-p", choices=["P0", "P1", "P2"], default="P2",
                       help="任务优先级")
    
    args = parser.parse_args()
    
    processor = MessageQueueProcessor()
    
    if args.stats:
        QueueStats.print_stats()
    elif args.add:
        # 添加测试任务
        task = processor.create_task(
            content=args.add,
            source="test",
            sender_id="test_user",
            sender_name="测试用户",
            priority=Priority[args.priority]
        )
        print(f"测试任务已添加: {task.id}")
        QueueStats.print_stats()
    else:
        # 运行处理器
        processor.run()


if __name__ == "__main__":
    main()

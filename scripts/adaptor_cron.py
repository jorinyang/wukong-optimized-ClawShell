#!/usr/bin/env python3
"""
Adaptor Cron脚本 - ClawShell v0.1
=================================

自适应机制的Cron任务脚本。
定期采集状态、分析并执行响应。

执行频率：每5分钟
"""

import sys
import os
import logging
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from adaptor import StateCollector, StrategyAnalyzer, AutoResponder
from strategies import get_switcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_adaptor_cycle():
    """
    执行一次自适应循环
    
    1. 采集状态
    2. 分析状态
    3. 执行响应
    """
    logger.info("=== Adaptor Cron Cycle Started ===")
    
    try:
        # 1. 采集状态
        collector = StateCollector()
        metrics = collector.collect_all()
        logger.info(f"Collected {len(metrics)} metrics")
        
        # 2. 分析状态
        analyzer = StrategyAnalyzer()
        result = analyzer.analyze(metrics)
        logger.info(f"Analysis: should_switch={result.should_switch}, target={result.target_strategy}")
        
        if result.issues:
            for issue in result.issues:
                logger.warning(f"  Issue: {issue}")
        
        # 3. 执行响应
        responder = AutoResponder()
        
        if result.should_switch:
            actions = responder.respond(result)
            logger.info(f"Executed {len(actions)} actions")
            
            # 发布事件
            from eventbus import Publisher
            pub = Publisher(source="adaptor_cron")
            pub.publish(
                event_type=None,
                payload={
                    "event_name": "adaptor_cycle_completed",
                    "switched": True,
                    "target_strategy": result.target_strategy,
                    "metrics": metrics,
                },
                tags=["adaptor", "cron", "strategy_switched"],
            )
        else:
            logger.info("No action needed, system is healthy")
        
        # 获取动作历史
        history = responder.get_action_history(limit=5)
        if history:
            logger.info("Recent actions:")
            for action in history:
                logger.info(f"  {action['action_type']}: {action['target']} - executed={action['executed']}")
        
        logger.info("=== Adaptor Cron Cycle Completed ===")
        return True
        
    except Exception as e:
        logger.error(f"Adaptor cycle failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主入口"""
    success = run_adaptor_cycle()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

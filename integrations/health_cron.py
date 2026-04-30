"""
悟空定时健康检查 - WuKongHealthMonitor 集成
自动执行健康检查并记录结果
"""

import sys
sys.path.insert(0, r'C:\Users\Aorus\.ClawShell')

from integrations.health_monitor_integration import WuKongHealthMonitor
from datetime import datetime
import json
from pathlib import Path

class WuKongHealthCron:
    """悟空定时健康检查任务"""
    
    def __init__(self):
        self.health_monitor = WuKongHealthMonitor()
        self.log_dir = Path(r'C:\Users\Aorus\.real\users\user-bd1b229d4eff8f6a45c456149072cb3b\workspace\health_logs')
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def run(self):
        """执行健康检查并记录"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"[健康检查] 开始执行: {timestamp}")
        
        result = self.health_monitor.run_health_check()
        
        # 保存结果
        log_file = self.log_dir / f"health_{timestamp}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        
        # 输出摘要
        print(f"[健康检查] 完成: {result['overall_status']}")
        print(f"[健康检查] 评分: {result['overall_score']:.1f}/100")
        print(f"[健康检查] 问题数: {len(result['issues'])}")
        print(f"[健康检查] 日志: {log_file}")
        
        return result

if __name__ == "__main__":
    cron = WuKongHealthCron()
    cron.run()

"""
ClawShell 健康检查集成 - 悟空定期自检
集成 Layer1 健康监控系统到悟空的自检流程
"""

import sys
sys.path.insert(0, r'C:\Users\Aorus\.ClawShell')

from lib.layer1.health_check import HealthMonitor, HealthStatus

class WuKongHealthMonitor:
    """悟空健康监控集成类"""
    
    def __init__(self):
        self.monitor = HealthMonitor()
        self.last_report = None
        
    def run_health_check(self):
        """执行完整健康检查"""
        report = self.monitor.scan()
        self.last_report = report
        
        # 分析健康状态
        critical_issues = []
        warnings = []
        
        for component, status in report:
            if isinstance(status, dict):
                health = status if hasattr(status, "name") else status
            else:
                health = status
                
            if health == HealthStatus.CRITICAL:
                critical_issues.append(component)
            elif health == HealthStatus.WARNING:
                warnings.append(component)
        
        return {
            'critical': critical_issues,
            'warnings': warnings,
            'healthy': len(report) - len(critical_issues) - len(warnings),
            'total': len(report)
        }
    
    def get_status_summary(self):
        """获取状态摘要"""
        if not self.last_report:
            self.run_health_check()
        
        summary = {}
        for component, status in self.last_report.items():
            if isinstance(status, dict):
                summary[component] = {
                    'status': status.get('health', HealthStatus.UNKNOWN).name,
                    'details': status.get('details', {})
                }
            else:
                summary[component] = {'status': status.name if hasattr(status, 'name') else str(status)}
        
        return summary


# 集成示例
if __name__ == '__main__':
    monitor = WuKongHealthMonitor()
    result = monitor.run_health_check()
    
    print("=== 悟空健康检查报告 ===")
    print(f"总组件数: {result['total']}")
    print(f"健康: {result['healthy']}")
    print(f"警告: {len(result['warnings'])}")
    print(f"严重: {len(result['critical'])}")
    
    if result['warnings']:
        print(f"\n警告组件: {', '.join(result['warnings'])}")
    if result['critical']:
        print(f"\n严重问题: {', '.join(result['critical'])}")

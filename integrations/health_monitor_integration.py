"""
ClawShell 健康检查集成 - 替换悟空手动健康检查
集成 Layer1 HealthMonitor 到悟空的系统监控
"""

import sys
sys.path.insert(0, r'C:\Users\Aorus\.ClawShell')

from lib.layer1.health_check import HealthMonitor, HealthStatus


class WuKongHealthMonitor:
    """悟空健康监控系统 - 基于ClawShell Layer1"""
    
    def __init__(self):
        self.monitor = HealthMonitor()
        self.last_report = None
        
    def run_health_check(self):
        """执行全面健康检查，返回格式化报告"""
        report = self.monitor.scan()
        self.last_report = report
        
        # 格式化报告
        result = {
            'timestamp': report.timestamp,
            'overall_status': report.status.name if hasattr(report.status, 'name') else str(report.status),
            'overall_score': round(report.overall_score, 1),
            'scores': report.scores,
            'issues': [],
            'recommendations': report.recommendations,
            'stats': report.stats
        }
        
        # 格式化问题列表
        for issue in report.issues:
            result['issues'].append({
                'id': issue.id,
                'name': issue.name,
                'severity': issue.severity.name if hasattr(issue.severity, 'name') else str(issue.severity),
                'description': issue.description,
                'auto_repairable': issue.auto_repairable,
                'repair_action': issue.repair_action
            })
        
        return result
    
    def get_status_summary(self):
        """获取状态摘要"""
        if not self.last_report:
            self.run_health_check()
        
        report = self.last_report
        return {
            'status': report.status.name if hasattr(report.status, 'name') else str(report.status),
            'score': round(report.overall_score, 1),
            'p0_count': report.stats.get('p0_count', 0),
            'p1_count': report.stats.get('p1_count', 0),
            'active_issues': report.stats.get('active_issues', 0)
        }
    
    def get_critical_issues(self):
        """获取关键问题（P0和P1）"""
        if not self.last_report:
            self.run_health_check()
        
        critical = []
        for issue in self.last_report.issues:
            severity_name = issue.severity.name if hasattr(issue.severity, 'name') else str(issue.severity)
            if severity_name in ['P0', 'P1']:
                critical.append({
                    'name': issue.name,
                    'severity': severity_name,
                    'description': issue.description
                })
        
        return critical
    
    def is_healthy(self):
        """快速检查是否健康"""
        if not self.last_report:
            self.run_health_check()
        
        return self.last_report.status == HealthStatus.HEALTHY


# 导出
__all__ = ['WuKongHealthMonitor']

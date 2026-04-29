#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钉钉待办任务完整查询工具
基于钉钉开放平台 API v2
解决 MCP 服务查询不完整的问题
"""

import requests
import json
import os
from datetime import datetime

class DingTalkTodoAPI:
    """钉钉待办 API 客户端"""
    
    def __init__(self, app_key=None, app_secret=None):
        """
        初始化钉钉 API 客户端
        
        Args:
            app_key: 钉钉应用 AppKey
            app_secret: 钉钉应用 AppSecret
        """
        self.app_key = app_key or os.getenv('DINGTALK_APP_KEY')
        self.app_secret = app_secret or os.getenv('DINGTALK_APP_SECRET')
        self.access_token = None
        self.base_url = "https://oapi.dingtalk.com"
        
    def get_access_token(self):
        """获取钉钉 Access Token"""
        url = f"{self.base_url}/gettoken"
        params = {
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('errcode') == 0:
                self.access_token = data.get('access_token')
                return self.access_token
            else:
                print(f"获取 Token 失败: {data.get('errmsg')}")
                return None
        except Exception as e:
            print(f"请求异常: {e}")
            return None
    
    def get_user_todos(self, userid, status=None, page_size=50, page_number=1):
        """
        获取用户待办任务列表
        
        Args:
            userid: 用户 ID
            status: 状态筛选 (0:未完成, 1:已完成, None:全部)
            page_size: 每页数量
            page_number: 页码
            
        Returns:
            待办任务列表
        """
        if not self.access_token:
            self.get_access_token()
            
        # 钉钉待办 API v2
        url = f"{self.base_url}/topapi/workrecord/task/getusertasklist"
        
        params = {
            "access_token": self.access_token
        }
        
        data = {
            "userid": userid,
            "page_size": page_size,
            "page_number": page_number
        }
        
        # 添加状态筛选
        if status is not None:
            data["status"] = status
        
        try:
            response = requests.post(url, params=params, json=data, timeout=10)
            result = response.json()
            
            if result.get('errcode') == 0:
                return result.get('result', {})
            else:
                print(f"查询失败: {result.get('errmsg')}")
                return None
        except Exception as e:
            print(f"请求异常: {e}")
            return None
    
    def get_all_todos(self, userid):
        """
        获取用户所有待办（包括未完成和已完成）
        
        Args:
            userid: 用户 ID
            
        Returns:
            完整的待办任务列表
        """
        all_todos = []
        
        # 获取未完成待办
        print("📥 正在查询未完成待办...")
        incomplete = self.get_user_todos(userid, status=0)
        if incomplete and 'items' in incomplete:
            all_todos.extend([{**item, 'status': '未完成'} for item in incomplete['items']])
            print(f"  ✅ 找到 {len(incomplete['items'])} 项未完成待办")
        
        # 获取已完成待办
        print("📥 正在查询已完成待办...")
        complete = self.get_user_todos(userid, status=1)
        if complete and 'items' in complete:
            all_todos.extend([{**item, 'status': '已完成'} for item in complete['items']])
            print(f"  ✅ 找到 {len(complete['items'])} 项已完成待办")
        
        return all_todos
    
    def print_todos(self, todos):
        """格式化打印待办列表"""
        if not todos:
            print("\n📭 暂无待办任务")
            return
        
        print(f"\n📋 待办任务清单 (共 {len(todos)} 项)\n")
        print("-" * 80)
        
        for idx, todo in enumerate(todos, 1):
            subject = todo.get('subject', '无标题')
            status = todo.get('status', '未知')
            created_time = todo.get('created_time', 0)
            due_time = todo.get('due_time', 0)
            priority = todo.get('priority', 20)
            task_id = todo.get('task_id', 'N/A')
            
            # 格式化时间
            created_str = datetime.fromtimestamp(created_time/1000).strftime('%Y-%m-%d %H:%M') if created_time else '无'
            due_str = datetime.fromtimestamp(due_time/1000).strftime('%Y-%m-%d %H:%M') if due_time else '无截止日期'
            
            # 优先级图标
            priority_icon = {10: '🔵 低', 20: '🟢 普通', 30: '🟡 较高', 40: '🔴 紧急'}.get(priority, '⚪ 未知')
            status_icon = '⏳' if status == '未完成' else '✅'
            
            print(f"{idx}. {status_icon} {subject}")
            print(f"   状态: {status} | 优先级: {priority_icon}")
            print(f"   创建: {created_str} | 截止: {due_str}")
            print(f"   ID: {task_id}")
            print("-" * 80)


def main():
    """主函数"""
    # 从环境变量获取凭证
    app_key = os.getenv('DINGTALK_APP_KEY')
    app_secret = os.getenv('DINGTALK_APP_SECRET')
    userid = os.getenv('DINGTALK_USER_ID')  # 您的钉钉用户ID
    
    if not app_key or not app_secret:
        print("❌ 请设置环境变量 DINGTALK_APP_KEY 和 DINGTALK_APP_SECRET")
        print("\n设置方法:")
        print("  export DINGTALK_APP_KEY='your_app_key'")
        print("  export DINGTALK_APP_SECRET='your_app_secret'")
        print("  export DINGTALK_USER_ID='your_userid'")
        return
    
    if not userid:
        # 尝试使用默认值
        userid = "1062695814-580275369"
        print(f"⚠️ 未设置 DINGTALK_USER_ID，使用默认值: {userid}")
    
    # 创建客户端
    client = DingTalkTodoAPI(app_key, app_secret)
    
    # 获取 Token
    print("🔑 正在获取 Access Token...")
    token = client.get_access_token()
    if not token:
        print("❌ 获取 Token 失败，请检查 AppKey 和 AppSecret")
        return
    print("✅ Token 获取成功\n")
    
    # 获取所有待办
    todos = client.get_all_todos(userid)
    
    # 打印结果
    client.print_todos(todos)


if __name__ == "__main__":
    main()

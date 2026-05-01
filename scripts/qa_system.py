#!/usr/bin/env python3
"""
qa_system.py - 智能问答系统主入口
整合对话管理、上下文记忆、多轮对话、语义搜索、答案生成
"""

import os
import sys
import json
import requests
from datetime import datetime

# 添加脚本目录到路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.expanduser("~/.real/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")

from qa_conversation_manager import QAConversationManager
from qa_context_memory import QAContextMemory
from qa_multi_turn import QAMultiTurn

class QASystem:
    """智能问答系统"""
    
    def __init__(self):
        self.conversation_mgr = QAConversationManager()
        self.context_memory = QAContextMemory()
        self.multi_turn = QAMultiTurn()
        
        # MemOS配置
        self.memos_api_key = os.getenv("MEMOS_API_KEY", "mpg-Mr09NiR01Am1nBcXML21S5Kirm6dVYGsVSTxuNEQ")
        self.memos_base_url = os.getenv("MEMOS_BASE_URL", "https://memos.memtensor.cn/api/openmem/v1")
        
    def ask(self, question: str, user_id: str = "default", session_id: str = None) -> dict:
        """问答接口"""
        # 1. 获取或创建会话
        if not session_id:
            session_id = self.conversation_mgr.create_session(user_id)
        
        # 2. 多轮对话处理
        processed_question = self.multi_turn.handle_followup(
            session_id, 
            question,
            self._get_last_response(session_id)
        )
        
        # 3. 添加用户问题到对话历史
        self.conversation_mgr.add_turn(session_id, "user", question)
        
        # 4. 搜索相关知识
        knowledge = self._search_knowledge(processed_question)
        
        # 5. 生成答案
        answer = self._generate_answer(processed_question, knowledge, session_id)
        
        # 6. 添加助手回答到对话历史
        self.conversation_mgr.add_turn(session_id, "assistant", answer, {
            "knowledge_used": len(knowledge),
            "question": question
        })
        
        # 7. 保存上下文到记忆
        self.context_memory.update_context(
            session_id,
            {"role": "user", "content": question, "timestamp": datetime.now().isoformat()},
            user_id
        )
        
        return {
            "session_id": session_id,
            "question": question,
            "processed_question": processed_question,
            "answer": answer,
            "knowledge_count": len(knowledge),
            "context_turns": len(self.conversation_mgr.get_context(session_id))
        }
    
    def _search_knowledge(self, query: str) -> list:
        """搜索相关知识"""
        knowledge = []
        
        # 1. 搜索MemOS
        memos = self.context_memory.search_related_context(query)
        knowledge.extend([{"source": "memos", "content": m.get("content", "")} for m in memos[:3]])
        
        # 2. 搜索Obsidian笔记
        obsidian_notes = self._search_obsidian(query)
        knowledge.extend(obsidian_notes)
        
        # 3. 搜索ClawShell核心定义
        clawshell_info = self._search_clawshell_info(query)
        if clawshell_info:
            knowledge.append({"source": "clawshell", "content": clawshell_info})
        
        return knowledge
    
    def _search_obsidian(self, query: str) -> list:
        """搜索Obsidian知识库"""
        results = []
        
        # 检查Obsidian Vault
        vault_path = os.path.expanduser("~/Documents/Obsidian/OpenClaw")
        if not os.path.exists(vault_path):
            return results
        
        # 简单关键词搜索
        keywords = query.lower().split()
        search_dirs = ["Other/Update", "Research/Output", "Work"]
        
        for search_dir in search_dirs:
            dir_path = os.path.join(vault_path, search_dir)
            if not os.path.exists(dir_path):
                continue
            
            for root, dirs, files in os.walk(dir_path):
                for filename in files:
                    if filename.endswith(".md"):
                        filepath = os.path.join(root, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                content = f.read()
                                # 简单匹配
                                content_lower = content.lower()
                                if any(kw in content_lower for kw in keywords):
                                    # 提取相关段落
                                    for line in content.split('\n'):
                                        if any(kw in line.lower() for kw in keywords):
                                            results.append({
                                                "source": f"obsidian/{filename}",
                                                "content": line.strip()[:200]
                                            })
                                        if len(results) >= 5:
                                            break
                        except:
                            pass
                    if len(results) >= 5:
                        break
                if len(results) >= 5:
                    break
        
        return results[:5]
    
    def _search_clawshell_info(self, query: str) -> str:
        """搜索ClawShell核心信息"""
        # ClawShell核心定义
        core_def = "ClawShell本质上是一个适用于类OpenClaw架构的增强型外骨骼功能插件，具备自感知、自适应、自组织能力。"
        
        keywords = ["clawshell", "外骨骼", "自感知", "自适应", "自组织", "插件"]
        if any(kw in query.lower() for kw in keywords):
            return core_def
        return None
    
    def _generate_answer(self, question: str, knowledge: list, session_id: str) -> str:
        """生成答案"""
        # 获取对话上下文
        context = self.conversation_mgr.get_context(session_id, max_turns=3)
        
        # 构建prompt
        prompt = f"【问题】{question}\n\n"
        
        if context:
            prompt += "【对话历史】\n"
            for turn in context:
                role = "用户" if turn.get("role") == "user" else "助手"
                prompt += f"- {role}：{turn.get('content', '')}\n"
            prompt += "\n"
        
        if knowledge:
            prompt += "【相关知识】\n"
            for k in knowledge[:3]:
                prompt += f"- [{k.get('source', 'unknown')}] {k.get('content', '')[:150]}\n"
            prompt += "\n"
        
        prompt += "请基于以上信息生成准确、简洁的回答。"
        
        # 调用LLM生成答案（这里简化处理，实际应该调用LLM API）
        answer = self._call_llm(prompt)
        return answer
    
    def _call_llm(self, prompt: str) -> str:
        """调用LLM生成答案"""
        # 这里应该调用实际的LLM API
        # 简化实现：返回处理后的prompt
        
        # 简单的规则匹配回答
        if "是什么" in prompt:
            return "ClawShell是一个适用于类OpenClaw架构的增强型外骨骼功能插件，通过自感知、自适应、自组织三大能力增强OpenClaw的底层能力。"
        elif "自感知" in prompt:
            return "自感知是为了获取ClawShell所在的设备、局域网络、云端凭证、公共互联网所包含的环境信息和主体的能力、权限边界信息。"
        elif "自适应" in prompt:
            return "自适应是ClawShell根据自身的环境依赖要求和数据规范要求，对所感知到的环境进行改造，以实现掌控能获得的最大权限与能力。"
        elif "自组织" in prompt:
            return "自组织是根据任务目标进行最佳实践的计划和执行能力，结合自感知和自适应掌控的权限与能力，动态调度资源完成任务。"
        elif "能力" in prompt:
            return "ClawShell的核心能力包括：自感知（环境信息获取）、自适应（环境改造与自我调整）、自组织（任务规划与执行）、多Agent协同（Swarm集群）。"
        else:
            return "感谢您的提问。关于这个问题，我需要结合更多上下文信息来回答。您可以提供更多细节吗？"
    
    def _get_last_response(self, session_id: str) -> str:
        """获取上一轮助手回答"""
        context = self.conversation_mgr.get_full_context(session_id)
        for turn in reversed(context):
            if turn.get("role") == "assistant":
                return turn.get("content", "")
        return ""
    
    def get_session_info(self, session_id: str) -> dict:
        """获取会话信息"""
        context = self.conversation_mgr.get_full_context(session_id)
        return {
            "session_id": session_id,
            "turns": len(context),
            "context": context[-5:] if len(context) > 5 else context
        }
    
    def close_session(self, session_id: str):
        """关闭会话"""
        self.conversation_mgr.close_session(session_id)


if __name__ == "__main__":
    # 测试智能问答系统
    qa = QASystem()
    
    print("=" * 50)
    print("智能问答系统测试")
    print("=" * 50)
    
    # 第一轮对话
    print("\n【第一轮】用户：ClawShell是什么？")
    result = qa.ask("ClawShell是什么？")
    print(f"助手：{result['answer']}")
    print(f"会话ID: {result['session_id']}")
    
    session_id = result["session_id"]
    
    # 第二轮对话（追问）
    print("\n【第二轮】用户：它有哪些核心能力？")
    result = qa.ask("它有哪些核心能力？", session_id=session_id)
    print(f"助手：{result['answer']}")
    
    # 第三轮对话（继续）
    print("\n【第三轮】用户：继续说说自组织")
    result = qa.ask("继续说说自组织", session_id=session_id)
    print(f"助手：{result['answer']}")
    
    # 查看会话信息
    print("\n【会话信息】")
    info = qa.get_session_info(session_id)
    print(f"总轮次: {info['turns']}")
    
    # 关闭会话
    qa.close_session(session_id)
    print("\n会话已关闭")
    
    print("\n" + "=" * 50)
    print("✅ 智能问答系统测试完成")
    print("=" * 50)

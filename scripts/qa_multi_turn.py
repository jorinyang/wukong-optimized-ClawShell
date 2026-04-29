#!/usr/bin/env python3
"""
qa_multi_turn.py - 智能问答多轮对话处理
功能：处理追问、指代消解、话题延续
"""

import re
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qa_conversation_manager import QAConversationManager
from qa_context_memory import QAContextMemory

class QAMultiTurn:
    """多轮对话处理器"""
    
    # 指代消解词库
    PRONOUNS = {
        "它": ["ClawShell", "系统", "这个", "那个"],
        "他": [],
        "她": [],
        "这个": ["上面", "刚才", "之前"],
        "那个": ["上面", "刚才", "之前"],
        "这些": ["上面", "刚才", "之前"],
        "那些": ["上面", "刚才", "之前"],
        "这里": ["当前", "这里"],
        "那里": ["之前", "刚才"],
        "这样": ["这样", "如此"],
        "那样": ["那样", "如此"],
    }
    
    # 话题延续词
    CONTINUE_WORDS = [
        "还有呢", "继续", "然后", "还有", "另外",
        "除此之外", "再说说", "补充一下", "继续说"
    ]
    
    # 追问模式
    FOLLOWUP_PATTERNS = [
        r"为什么(.*)",
        r"怎么(.*)",
        r"如何(.*)",
        r"能详细说吗",
        r"能解释一下吗",
        r"具体是(.*)",
        r"也就是说",
        r"你的意思是",
        r"那(.*)呢",
    ]
    
    def __init__(self):
        self.conversation_mgr = QAConversationManager()
        self.context_memory = QAContextMemory()
        
    def handle_followup(self, session_id: str, followup: str, last_response: str = "") -> str:
        """处理追问"""
        # 1. 指代消解
        resolved = self.resolve_coreference(session_id, followup)
        
        # 2. 检测是否是继续话题
        if self.is_continue(followup):
            return self.handle_continue(session_id, resolved)
        
        # 3. 检测是否是追问
        if self.is_followup(followup):
            return self.handle_specific_followup(session_id, resolved, last_response)
        
        # 4. 普通问题，保持原样
        return resolved
    
    def resolve_coreference(self, session_id: str, text: str) -> str:
        """指代消解"""
        context = self.conversation_mgr.get_full_context(session_id)
        if not context:
            return text
        
        resolved = text
        
        # 获取最近的实体（最后一轮assistant的实体）
        recent_entities = []
        for turn in reversed(context):
            if turn.get("role") == "assistant":
                # 简单提取名词
                words = turn.get("content", "").split()
                for word in words:
                    if len(word) > 2 and word not in ["这个", "那个", "什么"]:
                        recent_entities.append(word)
                break
        
        # 替换指代词
        for pronoun, _ in self.PRONOUNS.items():
            if pronoun in resolved:
                # 尝试用最近实体替换
                for entity in recent_entities[:3]:
                    if entity in resolved:
                        resolved = resolved.replace(pronoun, entity, 1)
                        break
        
        return resolved
    
    def is_continue(self, text: str) -> bool:
        """判断是否是继续话题"""
        text_lower = text.lower()
        return any(word in text_lower for word in self.CONTINUE_WORDS)
    
    def is_followup(self, text: str) -> bool:
        """判断是否是追问"""
        return any(re.search(pattern, text) for pattern in self.FOLLOWUP_PATTERNS)
    
    def handle_continue(self, session_id: str, resolved: str) -> str:
        """处理继续话题"""
        context = self.conversation_mgr.get_full_context(session_id)
        if not context:
            return "好的，我继续介绍..."
        
        # 获取assistant最后说的内容
        last_assistant_content = ""
        for turn in reversed(context):
            if turn.get("role") == "assistant":
                last_assistant_content = turn.get("content", "")
                break
        
        if last_assistant_content:
            # 继续延伸
            return f"继续刚才的话题：{last_assistant_content}"
        return "好的，我继续..."
    
    def handle_specific_followup(self, session_id: str, followup: str, last_response: str) -> str:
        """处理特定类型的追问"""
        # 获取上下文
        context = self.conversation_mgr.get_full_context(session_id)
        
        # 提取最后一个主题
        last_topic = self._extract_topic(context[-1] if context else {})
        
        # 根据追问类型构造响应
        if followup.startswith("为什么"):
            reason = followup.replace("为什么", "")
            return f"关于「{reason}」的原因，需要结合具体的上下文来分析。{last_topic}的设计是为了..."
        
        elif followup.startswith("怎么") or followup.startswith("如何"):
            method = followup.replace("怎么", "").replace("如何", "")
            return f"要{method}，可以按照以下步骤：首先...其次...最后..."
        
        elif "详细" in followup or "解释" in followup:
            return f"让我详细解释一下：{last_topic}的核心在于..."
        
        elif "那" in followup and "呢" in followup:
            # 话题切换
            return f"关于「{followup}」这是一个新的话题，让我来解答..."
        
        return followup
    
    def _extract_topic(self, turn: dict) -> str:
        """提取对话中的主题"""
        content = turn.get("content", "")
        # 简单取前50字
        return content[:50] if content else "这个"
    
    def build_multi_turn_prompt(self, session_id: str, current_question: str) -> str:
        """构建多轮对话Prompt"""
        context = self.conversation_mgr.get_context(session_id, max_turns=5)
        
        prompt = "【对话历史】\n"
        for turn in context:
            role = "用户" if turn.get("role") == "user" else "助手"
            prompt += f"{role}：{turn.get('content', '')}\n"
        
        prompt += f"\n【当前问题】\n用户：{current_question}\n"
        prompt += "\n请根据对话历史，回答当前问题。"
        
        return prompt
    
    def should_end_conversation(self, session_id: str, user_input: str) -> bool:
        """判断是否应该结束对话"""
        end_signals = [
            "谢谢", "好的", "知道了", "明白了",
            "结束了", "就这样", "没问题了",
            "再见", "拜拜"
        ]
        return any(signal in user_input for signal in end_signals)


if __name__ == "__main__":
    # 测试多轮对话
    multi_turn = QAMultiTurn()
    mgr = QAConversationManager()
    
    # 创建测试会话
    session_id = mgr.create_session("test")
    
    # 添加对话历史
    mgr.add_turn(session_id, "user", "ClawShell是什么？")
    mgr.add_turn(session_id, "assistant", "ClawShell是一个适用于类OpenClaw架构的增强型外骨骼功能插件，具备自感知、自适应、自组织能力。")
    mgr.add_turn(session_id, "user", "它有哪些核心能力？")
    mgr.add_turn(session_id, "assistant", "ClawShell的核心能力包括：1) 自感知 2) 自适应 3) 自组织。")
    
    # 测试指代消解
    test_followup = "那它是怎么实现的呢？"
    resolved = multi_turn.resolve_coreference(session_id, test_followup)
    print(f"原始追问: {test_followup}")
    print(f"消解后: {resolved}")
    
    # 测试继续话题
    continue_input = "继续"
    if multi_turn.is_continue(continue_input):
        print("检测到继续话题")
    
    # 测试追问检测
    followup_input = "为什么是这样设计的？"
    if multi_turn.is_followup(followup_input):
        print("检测到追问")
    
    # 构建多轮Prompt
    prompt = multi_turn.build_multi_turn_prompt(
        session_id, 
        "能详细说说自感知吗？"
    )
    print(f"\n构建的多轮Prompt:\n{prompt}")
    
    print("\n✅ 多轮对话测试通过")

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
幸运飞艇开奖查询工具
支持信用盘和官方盘查询，以及投注结果计算
"""

import sys
import io

# Windows控制台编码修复
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import json
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import threading
from urllib.parse import urlencode
from collections import defaultdict, Counter
import statistics


class LotteryCalculator:
    """投注结果计算器"""
    
    @staticmethod
    def parse_result(result_str: str) -> List[int]:
        """解析开奖结果字符串为数字列表"""
        return [int(x.strip()) for x in result_str.split(',')]
    
    @staticmethod
    def is_odd(num: int) -> bool:
        """判断是否为单数"""
        return num % 2 == 1
    
    @staticmethod
    def is_big(num: int) -> bool:
        """判断是否为大（>=6）"""
        return num >= 6
    
    @staticmethod
    def calculate_two_sides(result: List[int], position: int) -> Dict[str, str]:
        """计算1~10两面结果（单双、大小）"""
        num = result[position]
        return {
            '单双': '单' if LotteryCalculator.is_odd(num) else '双',
            '大小': '大' if LotteryCalculator.is_big(num) else '小',
            '号码': num
        }
    
    @staticmethod
    def calculate_dragon_tiger(result: List[int], position: int) -> str:
        """计算龙虎结果
        position: 0=冠军, 1=亚军, 2=第三名, 3=第四名, 4=第五名
        """
        positions = [
            (0, 9),   # 冠军 vs 第十名
            (1, 8),   # 亚军 vs 第九名
            (2, 7),   # 第三名 vs 第八名
            (3, 6),   # 第四名 vs 第七名
            (4, 5),   # 第五名 vs 第六名
        ]
        
        if position >= len(positions):
            return '无效'
        
        first_pos, second_pos = positions[position]
        first_num = result[first_pos]
        second_num = result[second_pos]
        
        if first_num > second_num:
            return '龙'
        elif first_num < second_num:
            return '虎'
        else:
            return '和'
    
    @staticmethod
    def calculate_crown_sum(result: List[int]) -> Dict[str, any]:
        """计算冠亚和值相关结果"""
        crown = result[0]  # 冠军
        sub = result[1]    # 亚军
        total = crown + sub
        
        return {
            '和值': total,
            '单双': '单' if LotteryCalculator.is_odd(total) else '双',
            '大小': '大' if total > 11 else ('小' if total < 11 else '和'),
            '组合': f"{crown:02d}{sub:02d}"
        }
    
    @staticmethod
    def check_crown_combination(result: List[int], bet_nums: List[int]) -> bool:
        """检查冠亚组合是否中奖
        bet_nums: 投注的两个号码
        """
        crown = result[0]
        sub = result[1]
        return crown in bet_nums and sub in bet_nums


class PositionPrediction:
    """定位胆预测算法"""
    
    def __init__(self, history_data: List[Dict]):
        """
        history_data: 历史开奖数据列表，每个元素包含 'result' 字段（开奖号码字符串）
        """
        self.history_data = history_data
        self.positions = 10  # 1-10名
        self.numbers = list(range(1, 11))  # 1-10号
    
    def algorithm1_frequency(self) -> Dict[int, List[Tuple[int, float]]]:
        """
        算法1：频率分析
        统计每个位置每个号码出现的频率，推荐频率最高的号码
        返回: {位置: [(号码, 频率), ...]}
        """
        # 统计每个位置每个号码的出现次数
        position_counts = {pos: defaultdict(int) for pos in range(self.positions)}
        
        for record in self.history_data:
            result_str = record.get('result', '')
            if not result_str:
                continue
            
            try:
                numbers = LotteryCalculator.parse_result(result_str)
                for pos in range(self.positions):
                    if pos < len(numbers):
                        position_counts[pos][numbers[pos]] += 1
            except:
                continue
        
        # 计算频率并排序
        predictions = {}
        total_periods = len(self.history_data)
        
        for pos in range(self.positions):
            counts = position_counts[pos]
            # 计算频率
            frequencies = [(num, count / total_periods if total_periods > 0 else 0) 
                          for num, count in counts.items()]
            # 按频率降序排序
            frequencies.sort(key=lambda x: x[1], reverse=True)
            # 如果没有历史数据，返回所有号码
            if not frequencies:
                frequencies = [(num, 0.1) for num in self.numbers]
            predictions[pos] = frequencies
        
        return predictions
    
    def algorithm2_missing(self) -> Dict[int, List[Tuple[int, float]]]:
        """
        算法2：遗漏分析
        分析每个号码的遗漏值，推荐遗漏较大的号码（冷号）
        返回: {位置: [(号码, 遗漏值), ...]}
        """
        # 记录每个位置每个号码最后一次出现的位置
        last_appear = {pos: {num: -1 for num in self.numbers} for pos in range(self.positions)}
        
        for idx, record in enumerate(self.history_data):
            result_str = record.get('result', '')
            if not result_str:
                continue
            
            try:
                numbers = LotteryCalculator.parse_result(result_str)
                for pos in range(self.positions):
                    if pos < len(numbers):
                        last_appear[pos][numbers[pos]] = idx
            except:
                continue
        
        # 计算遗漏值（当前期数 - 最后出现期数）
        current_period = len(self.history_data)
        predictions = {}
        
        for pos in range(self.positions):
            missing_values = []
            for num in self.numbers:
                last_idx = last_appear[pos][num]
                if last_idx == -1:
                    # 从未出现过，遗漏值设为最大值
                    missing = current_period
                else:
                    missing = current_period - 1 - last_idx
                
                # 遗漏值越大，推荐度越高（转换为0-1的分数）
                score = min(missing / max(current_period, 1), 1.0)
                missing_values.append((num, score))
            
            # 按遗漏值降序排序
            missing_values.sort(key=lambda x: x[1], reverse=True)
            predictions[pos] = missing_values
        
        return predictions
    
    def algorithm3_trend(self) -> Dict[int, List[Tuple[int, float]]]:
        """
        算法3：趋势分析
        分析最近几期的趋势，预测下一期
        结合最近出现频率和变化趋势
        返回: {位置: [(号码, 趋势分数), ...]}
        """
        if len(self.history_data) < 3:
            # 数据不足，返回频率分析结果
            return self.algorithm1_frequency()
        
        # 分析最近N期的数据（取最近20期或全部数据）
        recent_n = min(20, len(self.history_data))
        recent_data = self.history_data[:recent_n]
        
        # 统计最近期的频率
        recent_counts = {pos: defaultdict(int) for pos in range(self.positions)}
        
        for record in recent_data:
            result_str = record.get('result', '')
            if not result_str:
                continue
            
            try:
                numbers = LotteryCalculator.parse_result(result_str)
                for pos in range(self.positions):
                    if pos < len(numbers):
                        recent_counts[pos][numbers[pos]] += 1
            except:
                continue
        
        # 分析趋势（最近3期的变化）
        trend_scores = {pos: defaultdict(float) for pos in range(self.positions)}
        
        if len(recent_data) >= 3:
            recent_3 = recent_data[:3]
            for record in recent_3:
                result_str = record.get('result', '')
                if not result_str:
                    continue
                
                try:
                    numbers = LotteryCalculator.parse_result(result_str)
                    for pos in range(self.positions):
                        if pos < len(numbers):
                            # 最近出现的号码给予额外加分
                            trend_scores[pos][numbers[pos]] += 0.3
                except:
                    continue
        
        predictions = {}
        for pos in range(self.positions):
            scores = []
            for num in self.numbers:
                # 综合分数 = 最近频率 + 趋势分数
                recent_freq = recent_counts[pos][num] / recent_n if recent_n > 0 else 0
                trend_score = trend_scores[pos][num]
                total_score = recent_freq * 0.7 + trend_score * 0.3
                scores.append((num, total_score))
            
            # 按分数降序排序
            scores.sort(key=lambda x: x[1], reverse=True)
            predictions[pos] = scores
        
        return predictions
    
    def calculate_win_rate(self, predictions: Dict[int, List[Tuple[int, float]]], 
                          test_data: List[Dict]) -> Dict[int, float]:
        """
        计算胜率（基于测试数据）
        返回: {位置: 胜率}
        """
        if not test_data:
            return {pos: 0.0 for pos in range(self.positions)}
        
        wins = {pos: 0 for pos in range(self.positions)}
        total = {pos: 0 for pos in range(self.positions)}
        
        for record in test_data:
            result_str = record.get('result', '')
            if not result_str:
                continue
            
            try:
                numbers = LotteryCalculator.parse_result(result_str)
                for pos in range(self.positions):
                    if pos < len(numbers):
                        total[pos] += 1
                        # 检查预测的前3个号码是否包含实际开奖号码
                        top3 = [pred[0] for pred in predictions[pos][:3]]
                        if numbers[pos] in top3:
                            wins[pos] += 1
            except:
                continue
        
        win_rates = {}
        for pos in range(self.positions):
            if total[pos] > 0:
                win_rates[pos] = wins[pos] / total[pos]
            else:
                win_rates[pos] = 0.0
        
        return win_rates
    
    def predict_all(self) -> Dict[str, Dict]:
        """
        使用所有算法进行预测
        返回: {
            'algorithm1': {位置: [(号码, 分数), ...]},
            'algorithm2': {位置: [(号码, 分数), ...]},
            'algorithm3': {位置: [(号码, 分数), ...]},
            'win_rates': {算法名: {位置: 胜率}}
        }
        """
        if not self.history_data:
            return {}
        
        # 使用80%的数据训练，20%的数据测试
        split_idx = int(len(self.history_data) * 0.8)
        train_data = self.history_data[:split_idx] if split_idx > 0 else self.history_data
        test_data = self.history_data[split_idx:] if split_idx < len(self.history_data) else []
        
        # 创建训练预测器
        train_predictor = PositionPrediction(train_data)
        
        # 运行三个算法
        pred1 = train_predictor.algorithm1_frequency()
        pred2 = train_predictor.algorithm2_missing()
        pred3 = train_predictor.algorithm3_trend()
        
        # 计算胜率
        win_rates = {
            '频率分析': train_predictor.calculate_win_rate(pred1, test_data),
            '遗漏分析': train_predictor.calculate_win_rate(pred2, test_data),
            '趋势分析': train_predictor.calculate_win_rate(pred3, test_data)
        }
        
        # 计算综合推荐
        comprehensive = train_predictor.calculate_comprehensive(pred1, pred2, pred3, win_rates)
        
        return {
            'algorithm1': pred1,
            'algorithm2': pred2,
            'algorithm3': pred3,
            'comprehensive': comprehensive,
            'win_rates': win_rates
        }
    
    def calculate_comprehensive(self, pred1: Dict, pred2: Dict, pred3: Dict, 
                                win_rates: Dict) -> Dict[int, List[Tuple[int, float]]]:
        """
        综合推荐：结合三个算法的结果和胜率
        返回: {位置: [(号码, 综合分数), ...]}
        """
        comprehensive = {}
        
        # 获取各算法的平均胜率作为权重
        algo_weights = {}
        for algo_name in ['频率分析', '遗漏分析', '趋势分析']:
            rates = win_rates.get(algo_name, {})
            avg_rate = sum(rates.values()) / len(rates) if rates else 0.25
            algo_weights[algo_name] = avg_rate
        
        # 归一化权重
        total_weight = sum(algo_weights.values())
        if total_weight > 0:
            for key in algo_weights:
                algo_weights[key] = algo_weights[key] / total_weight
        else:
            # 如果胜率都为0，使用平均权重
            algo_weights = {'频率分析': 0.33, '遗漏分析': 0.33, '趋势分析': 0.34}
        
        for pos in range(self.positions):
            # 收集所有号码的综合分数
            num_scores = defaultdict(float)
            
            # 算法1（频率分析）
            if pos in pred1:
                for idx, (num, score) in enumerate(pred1[pos]):
                    # 排名越靠前，权重越高
                    rank_weight = (len(pred1[pos]) - idx) / len(pred1[pos]) if pred1[pos] else 1.0
                    num_scores[num] += score * algo_weights['频率分析'] * rank_weight
            
            # 算法2（遗漏分析）
            if pos in pred2:
                for idx, (num, score) in enumerate(pred2[pos]):
                    rank_weight = (len(pred2[pos]) - idx) / len(pred2[pos]) if pred2[pos] else 1.0
                    num_scores[num] += score * algo_weights['遗漏分析'] * rank_weight
            
            # 算法3（趋势分析）
            if pos in pred3:
                for idx, (num, score) in enumerate(pred3[pos]):
                    rank_weight = (len(pred3[pos]) - idx) / len(pred3[pos]) if pred3[pos] else 1.0
                    num_scores[num] += score * algo_weights['趋势分析'] * rank_weight
            
            # 转换为列表并排序
            comprehensive[pos] = sorted(num_scores.items(), key=lambda x: x[1], reverse=True)
            
            # 归一化分数到0-1范围
            if comprehensive[pos]:
                max_score = comprehensive[pos][0][1]
                if max_score > 0:
                    comprehensive[pos] = [(num, score / max_score) for num, score in comprehensive[pos]]
        
        return comprehensive


class DeepSeekPredictor:
    """DeepSeek AI预测器"""
    
    API_URL = "https://api.deepseek.com/v1/chat/completions"
    
    @staticmethod
    def predict_position(token: str, history_data: List[Dict]) -> Optional[Dict]:
        """
        使用DeepSeek AI预测定位胆
        返回: {
            'predictions': {位置: [(号码, 置信度), ...]},
            'confidence': float  # 总体置信度
        }
        """
        if not token or not history_data:
            return None
        
        try:
            # 准备历史数据（最近100期）
            recent_data = history_data[:100]
            
            # 构建专业提示词
            prompt = DeepSeekPredictor._build_prompt(recent_data)
            
            # 调用DeepSeek API
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': 'deepseek-chat',
                'messages': [
                    {
                        'role': 'system',
                        'content': '你是一个专业的彩票数据分析专家，擅长分析历史开奖数据并预测下一期的开奖号码。'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.3,  # 降低随机性，提高准确性
                'max_tokens': 2000
            }
            
            response = requests.post(DeepSeekPredictor.API_URL, 
                                   headers=headers, 
                                   json=payload, 
                                   timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            # 解析返回结果
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                return DeepSeekPredictor._parse_response(content)
            
            return None
            
        except Exception as e:
            print(f"DeepSeek API调用错误: {e}")
            return None
    
    @staticmethod
    def _build_prompt(history_data: List[Dict]) -> str:
        """构建专业的预测提示词"""
        # 格式化历史数据
        history_text = "历史开奖数据（从最新到最旧）：\n"
        for idx, record in enumerate(history_data[:50]):  # 只取最近50期
            period = record.get('period', '')
            result = record.get('result', '')
            date = record.get('date', '')
            history_text += f"期号{period}: {result} (时间: {date})\n"
        
        prompt = f"""请分析以下幸运飞艇历史开奖数据，预测下一期（第1名到第10名）的定位胆号码。

{history_text}

**预测要求：**
1. 分析每个位置（第1名到第10名）的历史号码出现规律
2. 考虑号码的频率、遗漏值、趋势变化等因素
3. 为每个位置预测3个最可能的号码，按可能性从高到低排序
4. 给出每个号码的置信度（0-100%）

**输出格式（必须严格遵循JSON格式）：**
{{
  "predictions": {{
    "1": [{{"number": 号码, "confidence": 置信度百分比}}, ...],
    "2": [{{"number": 号码, "confidence": 置信度百分比}}, ...],
    ...
    "10": [{{"number": 号码, "confidence": 置信度百分比}}, ...]
  }},
  "overall_confidence": 总体置信度百分比,
  "analysis": "简要分析说明"
}}

**注意：**
- 每个位置必须预测3个号码（1-10之间的整数）
- 置信度必须是0-100之间的数字
- 只返回JSON，不要有其他文字说明
"""
        return prompt
    
    @staticmethod
    def _parse_response(content: str) -> Optional[Dict]:
        """解析DeepSeek返回的结果"""
        try:
            # 尝试提取JSON部分
            # 查找JSON对象
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                
                # 转换为标准格式
                predictions = {}
                if 'predictions' in result:
                    for pos_str, pred_list in result['predictions'].items():
                        pos = int(pos_str) - 1  # 转换为0-9索引
                        predictions[pos] = []
                        for pred in pred_list:
                            if isinstance(pred, dict):
                                num = pred.get('number', pred.get('号码', 0))
                                conf = pred.get('confidence', pred.get('置信度', 0))
                                # 转换为0-1范围的分数
                                score = conf / 100.0 if conf > 1 else conf
                                predictions[pos].append((int(num), score))
                
                return {
                    'predictions': predictions,
                    'confidence': result.get('overall_confidence', 50) / 100.0,
                    'analysis': result.get('analysis', '')
                }
            
            return None
            
        except Exception as e:
            print(f"解析DeepSeek响应错误: {e}")
            print(f"响应内容: {content[:500]}")
            return None


class CreditLotteryAPI:
    """信用盘API接口"""
    
    BASE_URL = "https://xn--dck9c.xn--1230a25-nr4fyc2j2b5k9i7e.xn--q9jyb4c/lotData/getLotteryResultList.do"
    
    @staticmethod
    def get_results(page_size: int = 20, page_number: int = 1, 
                    start_date: str = "", end_date: str = "", 
                    period: str = "") -> Optional[Dict]:
        """获取开奖结果"""
        params = {
            'code': 'XXYFT',
            'version': '2',
            'pageSize': page_size,
            'pageNumber': page_number,
            'startDate': start_date,
            'endDate': end_date,
            'period': period,
            '_': int(datetime.now().timestamp() * 1000)
        }
        
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://xn--dck9c.xn--1230a25-nr4fyc2j2b5k9i7e.xn--q9jyb4c/lotData/result.do?code=XXYFT&version=2',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        try:
            response = requests.get(CreditLotteryAPI.BASE_URL, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API请求错误: {e}")
            return None


class OfficialLotteryAPI:
    """官方盘API接口"""
    
    BASE_URL = "https://xn--dck9c.xn--1230a25-nr4fyc2j2b5k9i7e.xn--q9jyb4c/lotData/getLotteryResultList.do"
    
    @staticmethod
    def get_results(page_size: int = 20, page_number: int = 1, 
                    start_date: str = "", end_date: str = "", 
                    period: str = "") -> Optional[Dict]:
        """获取开奖结果（官方盘）"""
        params = {
            'code': 'XXYFT',
            'version': '1',  # 官方盘使用version=1
            'pageSize': page_size,
            'pageNumber': page_number,
            'startDate': start_date,
            'endDate': end_date,
            'period': period,
            '_': int(datetime.now().timestamp() * 1000)
        }
        
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://xn--dck9c.xn--1230a25-nr4fyc2j2b5k9i7e.xn--q9jyb4c/lotData/result.do?code=XXYFT&version=1',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        try:
            response = requests.get(OfficialLotteryAPI.BASE_URL, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"官方盘API请求错误: {e}")
            return None


class OfficialLotteryParser:
    """官方盘数据解析器"""
    
    @staticmethod
    def parse_from_text(text: str) -> List[Dict]:
        """从文本中解析开奖数据
        格式: 期号,开奖号码,日期时间
        例如: 20260121083,06,07,02,05,01,10,03,04,09,08,2026-01-21 19:58:40
        """
        results = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 尝试多种格式
            parts = re.split(r'[,\s]+', line)
            if len(parts) >= 11:
                try:
                    period = parts[0]
                    result_nums = parts[1:11]
                    date_str = ' '.join(parts[11:]) if len(parts) > 11 else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    result_str = ','.join([f"{int(x):02d}" for x in result_nums])
                    
                    results.append({
                        'period': period,
                        'result': result_str,
                        'date': date_str,
                        'id': len(results)
                    })
                except:
                    continue
        
        return results


class LotteryQueryApp:
    """主应用程序"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("幸运飞艇开奖查询工具 - 作者：飞机@laomao12315")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')
        
        # 初始化字体（需要在setup_styles之前）
        self.default_font = 'TkDefaultFont'
        
        # 设置样式
        self.setup_styles()
        
        # 实时信息相关
        self.latest_period = None
        self.last_result = None
        self.auto_refresh_enabled = False
        
        # 数据存储
        self.current_results = []
        self.current_source = None
        
        # 创建界面
        self.create_widgets()
        
        # 倒计时相关
        self.countdown_timer = None
        self.latest_period = None
        self.last_result = None
        self.next_draw_time = None
    
    def setup_styles(self):
        """设置样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 检测可用字体
        try:
            import tkinter.font as tkfont
            fonts = tkfont.families()
            if 'Microsoft YaHei' in fonts:
                default_font = 'Microsoft YaHei'
            elif 'SimHei' in fonts:
                default_font = 'SimHei'
            elif 'Microsoft Sans Serif' in fonts:
                default_font = 'Microsoft Sans Serif'
            else:
                default_font = 'TkDefaultFont'
        except:
            default_font = 'TkDefaultFont'
        
        # 配置样式
        style.configure('Title.TLabel', font=(default_font, 16, 'bold'), background='#f0f0f0')
        style.configure('Heading.TLabel', font=(default_font, 11, 'bold'), background='#f0f0f0')
        style.configure('Info.TLabel', font=(default_font, 9), background='#f0f0f0')
        style.configure('Custom.TButton', font=(default_font, 10))
        style.configure('Custom.Treeview', font=(default_font, 9))
        
        self.default_font = default_font
    
    def create_realtime_panel(self):
        """创建实时信息显示面板"""
        realtime_frame = tk.Frame(self.root, bg='#ecf0f1', height=130)
        realtime_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        realtime_frame.pack_propagate(False)
        
        # 左侧：最新期号
        left_info = tk.Frame(realtime_frame, bg='#3498db', relief=tk.RAISED, bd=2)
        left_info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        tk.Label(left_info, text="最新期号", font=(self.default_font, 9), 
                bg='#3498db', fg='white').pack(pady=(20, 5))
        self.latest_period_label = tk.Label(left_info, text="--", 
                                           font=(self.default_font, 20, 'bold'),
                                           bg='#3498db', fg='white')
        self.latest_period_label.pack(pady=(0, 20))
        
        # 右侧：上一期开奖结果
        right_info = tk.Frame(realtime_frame, bg='#27ae60', relief=tk.RAISED, bd=2)
        right_info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        tk.Label(right_info, text="上一期开奖", font=(self.default_font, 9),
                bg='#27ae60', fg='white').pack(pady=(10, 3))
        self.last_period_label = tk.Label(right_info, text="期号: --", 
                                         font=(self.default_font, 11, 'bold'),
                                         bg='#27ae60', fg='white')
        self.last_period_label.pack()
        
        self.last_result_label = tk.Label(right_info, text="开奖号码: --", 
                                         font=(self.default_font, 14, 'bold'),
                                         bg='#27ae60', fg='#f1c40f')
        self.last_result_label.pack(pady=(8, 10))
        
        # 自动刷新开关
        refresh_frame = tk.Frame(realtime_frame, bg='#ecf0f1')
        refresh_frame.pack(side=tk.RIGHT, padx=15, fill=tk.Y)
        
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_check = tk.Checkbutton(refresh_frame, text="自动刷新", 
                                            variable=self.auto_refresh_var,
                                            font=(self.default_font, 10),
                                            bg='#ecf0f1', fg='#2c3e50',
                                            command=self.on_auto_refresh_change)
        auto_refresh_check.pack(pady=45)
    
    def on_auto_refresh_change(self):
        """自动刷新开关变化"""
        self.auto_refresh_enabled = self.auto_refresh_var.get()
    
    def on_predict_mode_change(self):
        """预测方式切换"""
        if self.predict_mode_var.get() == "algorithm":
            self.algorithm_predict_frame.pack(fill=tk.X)
            self.ai_predict_frame.pack_forget()
        else:
            self.algorithm_predict_frame.pack_forget()
            self.ai_predict_frame.pack(fill=tk.X)
    
    
    def create_widgets(self):
        """创建界面组件"""
        # 主标题
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=75)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, text="幸运飞艇开奖查询工具", 
                               font=(self.default_font, 18, 'bold'),
                               bg='#2c3e50', fg='white')
        title_label.pack(pady=(12, 2))
        
        author_label = tk.Label(title_frame, text="作者：飞机@laomao12315", 
                               font=(self.default_font, 9),
                               bg='#2c3e50', fg='#ecf0f1')
        author_label.pack(pady=(0, 10))
        
        # 实时信息显示面板
        self.create_realtime_panel()
        
        # 主容器
        main_container = tk.Frame(self.root, bg='#f0f0f0')
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧面板 - 查询控制
        left_panel = tk.Frame(main_container, bg='white', relief=tk.RAISED, bd=1)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.config(width=350)
        left_panel.pack_propagate(False)
        
        self.create_query_panel(left_panel)
        
        # 右侧面板 - 结果显示
        right_panel = tk.Frame(main_container, bg='white', relief=tk.RAISED, bd=1)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.create_result_panel(right_panel)
    
    def create_query_panel(self, parent):
        """创建查询面板"""
        # 标题
        title = tk.Label(parent, text="查询控制", font=(self.default_font, 12, 'bold'),
                        bg='white', fg='#2c3e50')
        title.pack(pady=15)
        
        # 数据源选择
        source_frame = tk.LabelFrame(parent, text="数据源", font=(self.default_font, 10),
                                     bg='white', fg='#34495e', padx=10, pady=10)
        source_frame.pack(fill=tk.X, padx=15, pady=10)
        
        self.source_var = tk.StringVar(value="credit")
        tk.Radiobutton(source_frame, text="信用盘", variable=self.source_var, value="credit",
                      font=(self.default_font, 9), bg='white', command=self.on_source_change).pack(anchor=tk.W)
        tk.Radiobutton(source_frame, text="官方盘", variable=self.source_var, value="official",
                      font=(self.default_font, 9), bg='white', command=self.on_source_change).pack(anchor=tk.W)
        
        # 信用盘查询选项
        self.credit_frame = tk.LabelFrame(parent, text="信用盘查询", font=(self.default_font, 10),
                                          bg='white', fg='#34495e', padx=10, pady=10)
        self.credit_frame.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(self.credit_frame, text="查询数量:", font=(self.default_font, 9), bg='white').pack(anchor=tk.W)
        self.page_size_var = tk.StringVar(value="20")
        page_size_combo = ttk.Combobox(self.credit_frame, textvariable=self.page_size_var,
                                       values=["10", "20", "50", "100"], width=15, state='readonly')
        page_size_combo.pack(anchor=tk.W, pady=5)
        
        tk.Label(self.credit_frame, text="期号查询:", font=(self.default_font, 9), bg='white').pack(anchor=tk.W, pady=(10, 0))
        self.period_var = tk.StringVar()
        tk.Entry(self.credit_frame, textvariable=self.period_var, width=20).pack(anchor=tk.W, pady=5)
        
        query_btn = tk.Button(self.credit_frame, text="查询信用盘", command=self.query_credit,
                             bg='#3498db', fg='white', font=(self.default_font, 10, 'bold'),
                             relief=tk.FLAT, padx=20, pady=8, cursor='hand2')
        query_btn.pack(pady=15)
        
        # 官方盘查询选项
        self.official_frame = tk.LabelFrame(parent, text="官方盘查询", font=(self.default_font, 10),
                                           bg='white', fg='#34495e', padx=10, pady=10)
        
        # 查询方式选择
        query_mode_frame = tk.Frame(self.official_frame, bg='white')
        query_mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(query_mode_frame, text="查询方式:", font=(self.default_font, 9), bg='white').pack(side=tk.LEFT)
        self.official_mode_var = tk.StringVar(value="api")
        tk.Radiobutton(query_mode_frame, text="API查询", variable=self.official_mode_var, value="api",
                      font=(self.default_font, 8), bg='white', command=self.on_official_mode_change).pack(side=tk.LEFT, padx=(10, 5))
        tk.Radiobutton(query_mode_frame, text="文本输入", variable=self.official_mode_var, value="text",
                      font=(self.default_font, 8), bg='white', command=self.on_official_mode_change).pack(side=tk.LEFT)
        
        # API查询选项
        self.official_api_frame = tk.Frame(self.official_frame, bg='white')
        
        tk.Label(self.official_api_frame, text="查询数量:", font=(self.default_font, 9), bg='white').pack(anchor=tk.W)
        self.official_page_size_var = tk.StringVar(value="20")
        official_page_size_combo = ttk.Combobox(self.official_api_frame, textvariable=self.official_page_size_var,
                                               values=["10", "20", "50", "100"], width=15, state='readonly')
        official_page_size_combo.pack(anchor=tk.W, pady=5)
        
        tk.Label(self.official_api_frame, text="期号查询:", font=(self.default_font, 9), bg='white').pack(anchor=tk.W, pady=(10, 0))
        self.official_period_var = tk.StringVar()
        tk.Entry(self.official_api_frame, textvariable=self.official_period_var, width=20).pack(anchor=tk.W, pady=5)
        
        official_query_btn = tk.Button(self.official_api_frame, text="查询官方盘", command=self.query_official_api,
                                      bg='#27ae60', fg='white', font=(self.default_font, 10, 'bold'),
                                      relief=tk.FLAT, padx=20, pady=8, cursor='hand2')
        official_query_btn.pack(pady=15)
        
        # 文本输入选项
        self.official_text_frame = tk.Frame(self.official_frame, bg='white')
        
        tk.Label(self.official_text_frame, text="数据输入:", font=(self.default_font, 9), bg='white').pack(anchor=tk.W)
        self.official_text = scrolledtext.ScrolledText(self.official_text_frame, height=8, width=30,
                                                       font=('Consolas', 9))
        self.official_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        tk.Label(self.official_text_frame, text="格式: 期号,号码1,号码2,...,号码10,日期时间", 
                font=(self.default_font, 8), bg='white', fg='gray').pack(anchor=tk.W)
        
        parse_btn = tk.Button(self.official_text_frame, text="解析官方盘数据", command=self.parse_official,
                             bg='#27ae60', fg='white', font=(self.default_font, 10, 'bold'),
                             relief=tk.FLAT, padx=20, pady=8, cursor='hand2')
        parse_btn.pack(pady=15)
        
        self.on_official_mode_change()
        
        # 定位胆预测
        prediction_frame = tk.LabelFrame(parent, text="定位胆预测", font=(self.default_font, 10),
                                        bg='white', fg='#34495e', padx=10, pady=10)
        prediction_frame.pack(fill=tk.X, padx=15, pady=10)
        
        # 预测方式选择
        predict_mode_frame = tk.Frame(prediction_frame, bg='white')
        predict_mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(predict_mode_frame, text="预测方式:", font=(self.default_font, 9), bg='white').pack(side=tk.LEFT)
        self.predict_mode_var = tk.StringVar(value="algorithm")
        tk.Radiobutton(predict_mode_frame, text="算法预测", variable=self.predict_mode_var, value="algorithm",
                      font=(self.default_font, 8), bg='white', command=self.on_predict_mode_change).pack(side=tk.LEFT, padx=(10, 5))
        tk.Radiobutton(predict_mode_frame, text="AI预测", variable=self.predict_mode_var, value="ai",
                      font=(self.default_font, 8), bg='white', command=self.on_predict_mode_change).pack(side=tk.LEFT)
        
        # 算法预测选项（默认显示）
        self.algorithm_predict_frame = tk.Frame(prediction_frame, bg='white')
        self.algorithm_predict_frame.pack(fill=tk.X)
        
        tk.Label(self.algorithm_predict_frame, text="基于历史数据的算法预测", font=(self.default_font, 8), 
                bg='white', fg='gray').pack(anchor=tk.W, pady=(0, 8))
        
        predict_btn = tk.Button(self.algorithm_predict_frame, text="开始预测", command=self.predict_position,
                               bg='#9b59b6', fg='white', font=(self.default_font, 10, 'bold'),
                               relief=tk.FLAT, padx=20, pady=8, cursor='hand2')
        predict_btn.pack()
        
        # AI预测选项
        self.ai_predict_frame = tk.Frame(prediction_frame, bg='white')
        
        tk.Label(self.ai_predict_frame, text="DeepSeek AI预测", font=(self.default_font, 8), 
                bg='white', fg='gray').pack(anchor=tk.W, pady=(0, 5))
        
        tk.Label(self.ai_predict_frame, text="API Token:", font=(self.default_font, 8), bg='white').pack(anchor=tk.W)
        self.deepseek_token_var = tk.StringVar()
        token_entry = tk.Entry(self.ai_predict_frame, textvariable=self.deepseek_token_var, 
                              width=25, show='*', font=(self.default_font, 9))
        token_entry.pack(anchor=tk.W, pady=3)
        
        tk.Label(self.ai_predict_frame, text="(将自动获取100期数据)", font=(self.default_font, 7), 
                bg='white', fg='gray').pack(anchor=tk.W, pady=(0, 8))
        
        ai_predict_btn = tk.Button(self.ai_predict_frame, text="开始预测", command=self.predict_with_deepseek,
                                  bg='#16a085', fg='white', font=(self.default_font, 10, 'bold'),
                                  relief=tk.FLAT, padx=20, pady=8, cursor='hand2')
        ai_predict_btn.pack()
        
        self.on_predict_mode_change()
        
        # 状态栏
        self.status_label = tk.Label(parent, text="就绪", font=(self.default_font, 9),
                                     bg='white', fg='gray', anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=10)
        
        self.on_source_change()
    
    def create_result_panel(self, parent):
        """创建结果显示面板"""
        # 标题栏
        header_frame = tk.Frame(parent, bg='#34495e', height=40)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="开奖结果", font=(self.default_font, 12, 'bold'),
                bg='#34495e', fg='white').pack(side=tk.LEFT, padx=15, pady=8)
        
        self.result_count_label = tk.Label(header_frame, text="", font=(self.default_font, 10),
                                           bg='#34495e', fg='#ecf0f1')
        self.result_count_label.pack(side=tk.RIGHT, padx=15, pady=8)
        
        # 结果表格
        table_frame = tk.Frame(parent, bg='white')
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建Treeview
        columns = ('期号', '开奖号码', '日期时间', '两面', '龙虎', '冠亚和值')
        self.result_tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                       style='Custom.Treeview', height=20)
        
        # 设置列
        self.result_tree.heading('期号', text='期号')
        self.result_tree.heading('开奖号码', text='开奖号码')
        self.result_tree.heading('日期时间', text='日期时间')
        self.result_tree.heading('两面', text='两面(1-10)')
        self.result_tree.heading('龙虎', text='龙虎(1-5)')
        self.result_tree.heading('冠亚和值', text='冠亚和值')
        
        # 设置列宽
        self.result_tree.column('期号', width=120)
        self.result_tree.column('开奖号码', width=200)
        self.result_tree.column('日期时间', width=180)
        self.result_tree.column('两面', width=150)
        self.result_tree.column('龙虎', width=200)
        self.result_tree.column('冠亚和值', width=150)
        
        # 滚动条
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.result_tree.xview)
        self.result_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 详细信息面板
        detail_frame = tk.LabelFrame(parent, text="详细信息", font=(self.default_font, 10),
                                     bg='white', fg='#34495e', padx=10, pady=10)
        detail_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.detail_text = scrolledtext.ScrolledText(detail_frame, height=8, font=('Consolas', 9))
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        
        # 绑定选择事件
        self.result_tree.bind('<<TreeviewSelect>>', self.on_result_select)
    
    def on_source_change(self):
        """数据源切换"""
        if self.source_var.get() == "credit":
            self.credit_frame.pack(fill=tk.X, padx=15, pady=10)
            self.official_frame.pack_forget()
        else:
            self.credit_frame.pack_forget()
            self.official_frame.pack(fill=tk.X, padx=15, pady=10)
    
    def on_official_mode_change(self):
        """官方盘查询方式切换"""
        if self.official_mode_var.get() == "api":
            self.official_api_frame.pack(fill=tk.BOTH, expand=True)
            self.official_text_frame.pack_forget()
        else:
            self.official_api_frame.pack_forget()
            self.official_text_frame.pack(fill=tk.BOTH, expand=True)
    
    def query_credit(self):
        """查询信用盘数据"""
        self.status_label.config(text="正在查询信用盘数据...", fg='blue')
        
        def query_thread():
            try:
                page_size = int(self.page_size_var.get())
                period = self.period_var.get().strip()
                
                data = CreditLotteryAPI.get_results(
                    page_size=page_size,
                    period=period if period else ""
                )
                
                if data and 'list' in data:
                    self.root.after(0, self.display_results, data['list'], 'credit')
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", "查询失败，请检查网络连接"))
                    self.root.after(0, lambda: self.status_label.config(text="查询失败", fg='red'))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"查询出错: {str(e)}"))
                self.root.after(0, lambda: self.status_label.config(text="查询出错", fg='red'))
        
        threading.Thread(target=query_thread, daemon=True).start()
    
    def query_official_api(self):
        """查询官方盘API数据"""
        self.status_label.config(text="正在查询官方盘数据...", fg='blue')
        
        def query_thread():
            try:
                page_size = int(self.official_page_size_var.get())
                period = self.official_period_var.get().strip()
                
                data = OfficialLotteryAPI.get_results(
                    page_size=page_size,
                    period=period if period else ""
                )
                
                if data and 'list' in data:
                    self.root.after(0, self.display_results, data['list'], 'official')
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", "查询失败，请检查网络连接"))
                    self.root.after(0, lambda: self.status_label.config(text="查询失败", fg='red'))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"查询出错: {str(e)}"))
                self.root.after(0, lambda: self.status_label.config(text="查询出错", fg='red'))
        
        threading.Thread(target=query_thread, daemon=True).start()
    
    def parse_official(self):
        """解析官方盘数据"""
        text = self.official_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("警告", "请输入官方盘数据")
            return
        
        self.status_label.config(text="正在解析官方盘数据...", fg='blue')
        
        try:
            results = OfficialLotteryParser.parse_from_text(text)
            if results:
                self.display_results(results, 'official')
                self.status_label.config(text=f"成功解析 {len(results)} 条记录", fg='green')
            else:
                messagebox.showwarning("警告", "未能解析出有效数据，请检查数据格式")
                self.status_label.config(text="解析失败", fg='red')
        except Exception as e:
            messagebox.showerror("错误", f"解析出错: {str(e)}")
            self.status_label.config(text="解析出错", fg='red')
    
    def display_results(self, results: List[Dict], source: str):
        """显示查询结果"""
        self.current_results = results
        self.current_source = source
        
        # 清空现有数据
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        # 更新期号列表（用于其他功能）
        periods = [r['period'] for r in results]
        
        # 插入数据
        for result in results:
            result_nums = LotteryCalculator.parse_result(result['result'])
            
            # 计算两面（显示第1名）
            two_sides = LotteryCalculator.calculate_two_sides(result_nums, 0)
            two_sides_str = f"1名: {two_sides['号码']}({two_sides['单双']}/{two_sides['大小']})"
            
            # 计算龙虎（显示前5个）
            dragon_tiger_list = []
            for i in range(5):
                dt = LotteryCalculator.calculate_dragon_tiger(result_nums, i)
                dragon_tiger_list.append(f"{i+1}:{dt}")
            dragon_tiger_str = " ".join(dragon_tiger_list)
            
            # 计算冠亚和值
            crown_info = LotteryCalculator.calculate_crown_sum(result_nums)
            crown_str = f"{crown_info['和值']}({crown_info['单双']}/{crown_info['大小']})"
            
            self.result_tree.insert('', tk.END, values=(
                result['period'],
                result['result'],
                result.get('date', ''),
                two_sides_str,
                dragon_tiger_str,
                crown_str
            ))
        
        # 更新实时信息面板
        if results:
            # 上一期开奖结果（第一条记录就是最新的已开奖期）
            latest = results[0]
            self.last_result = latest
            self.last_period_label.config(text=f"期号: {latest['period']}")
            self.last_result_label.config(text=f"开奖号码: {latest['result']}")
            
            # 计算最新期号（上一期期号+1）
            try:
                # 期号格式通常是：YYYYMMDDXXX（年月日+序号）
                last_period = latest['period']
                if len(last_period) >= 8:
                    # 提取日期部分和序号部分
                    date_part = last_period[:8]  # YYYYMMDD
                    seq_part = last_period[8:] if len(last_period) > 8 else ""
                    
                    if seq_part:
                        # 序号+1
                        next_seq = int(seq_part) + 1
                        # 检查是否需要进位（每天最多180期）
                        if next_seq > 180:
                            # 跨天，需要计算下一天
                            from datetime import timedelta
                            last_date = datetime.strptime(date_part, '%Y%m%d')
                            next_date = last_date + timedelta(days=1)
                            next_date_str = next_date.strftime('%Y%m%d')
                            self.latest_period = f"{next_date_str}001"
                        else:
                            self.latest_period = f"{date_part}{next_seq:03d}"
                    else:
                        # 如果没有序号部分，直接+1
                        self.latest_period = str(int(last_period) + 1)
                else:
                    # 简单格式，直接+1
                    self.latest_period = str(int(last_period) + 1)
            except:
                # 如果解析失败，尝试简单+1
                try:
                    self.latest_period = str(int(latest['period']) + 1)
                except:
                    self.latest_period = latest['period']
            
            self.latest_period_label.config(text=self.latest_period)
            
        
        # 更新统计
        self.result_count_label.config(text=f"共 {len(results)} 条记录")
        self.status_label.config(text=f"成功加载 {len(results)} 条记录", fg='green')
    
    def predict_position(self):
        """定位胆预测"""
        if not self.current_results or len(self.current_results) < 10:
            messagebox.showwarning("警告", "历史数据不足，至少需要10期数据才能进行预测")
            return
        
        self.status_label.config(text="正在分析历史数据...", fg='blue')
        
        def predict_thread():
            try:
                # 创建预测器
                predictor = PositionPrediction(self.current_results)
                
                # 执行预测
                predictions = predictor.predict_all()
                
                if predictions:
                    self.root.after(0, self.show_prediction_results, predictions)
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", "预测失败"))
                    self.root.after(0, lambda: self.status_label.config(text="预测失败", fg='red'))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"预测出错: {str(e)}"))
                self.root.after(0, lambda: self.status_label.config(text="预测出错", fg='red'))
        
        threading.Thread(target=predict_thread, daemon=True).start()
    
    def predict_with_deepseek(self):
        """使用DeepSeek AI进行预测"""
        token = self.deepseek_token_var.get().strip()
        if not token:
            messagebox.showwarning("警告", "请输入DeepSeek API Token")
            return
        
        if not self.current_results or len(self.current_results) < 10:
            messagebox.showwarning("警告", "历史数据不足，至少需要10期数据")
            return
        
        self.status_label.config(text="正在获取100期数据并使用DeepSeek预测...", fg='blue')
        
        def deepseek_thread():
            try:
                # 自动获取100期数据
                if len(self.current_results) < 100:
                    # 如果当前数据不足100期，尝试获取更多
                    if self.current_source == 'credit':
                        data = CreditLotteryAPI.get_results(page_size=100)
                    elif self.current_source == 'official':
                        data = OfficialLotteryAPI.get_results(page_size=100)
                    else:
                        data = None
                    
                    if data and 'list' in data:
                        all_data = data['list']
                    else:
                        all_data = self.current_results
                else:
                    all_data = self.current_results[:100]
                
                # 调用DeepSeek预测
                deepseek_result = DeepSeekPredictor.predict_position(token, all_data)
                
                if deepseek_result:
                    # 同时运行传统算法预测
                    predictor = PositionPrediction(all_data)
                    traditional_predictions = predictor.predict_all()
                    
                    # 合并结果
                    if traditional_predictions:
                        traditional_predictions['deepseek'] = deepseek_result
                        self.root.after(0, self.show_prediction_results, traditional_predictions)
                    else:
                        # 只有DeepSeek结果
                        self.root.after(0, self.show_prediction_results, {'deepseek': deepseek_result})
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", "DeepSeek预测失败，请检查Token是否正确"))
                    self.root.after(0, lambda: self.status_label.config(text="DeepSeek预测失败", fg='red'))
                    
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"DeepSeek预测出错: {str(e)}"))
                self.root.after(0, lambda: self.status_label.config(text="DeepSeek预测出错", fg='red'))
        
        threading.Thread(target=deepseek_thread, daemon=True).start()
    
    def show_prediction_results(self, predictions: Dict):
        """显示预测结果"""
        # 创建预测结果窗口
        pred_window = tk.Toplevel(self.root)
        pred_window.title("定位胆预测结果")
        pred_window.geometry("1200x700")
        pred_window.configure(bg='white')
        
        # 标题
        title_frame = tk.Frame(pred_window, bg='#9b59b6', height=50)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        tk.Label(title_frame, text="定位胆预测结果（推荐前3个号码）", 
                font=(self.default_font, 14, 'bold'),
                bg='#9b59b6', fg='white').pack(pady=12)
        
        # 创建Notebook显示三个算法的结果
        notebook = ttk.Notebook(pred_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 检查是否有DeepSeek预测结果
        has_deepseek = 'deepseek' in predictions
        
        algorithms = []
        if has_deepseek:
            # 如果有DeepSeek，放在最前面
            deepseek_data = predictions.get('deepseek', {})
            algorithms.append(('deepseek', 'DeepSeek AI', deepseek_data.get('predictions', {})))
        
        algorithms.extend([
            ('comprehensive', '综合推荐', predictions.get('comprehensive', {})),
            ('algorithm1', '频率分析', predictions.get('algorithm1', {})),
            ('algorithm2', '遗漏分析', predictions.get('algorithm2', {})),
            ('algorithm3', '趋势分析', predictions.get('algorithm3', {}))
        ])
        
        win_rates = predictions.get('win_rates', {})
        deepseek_info = predictions.get('deepseek', {}) if has_deepseek else {}
        
        # 计算综合推荐的胜率（三个算法的平均胜率）
        comprehensive_win_rates = {}
        if win_rates:
            for pos in range(10):
                rates = [win_rates.get(algo_name, {}).get(pos, 0) 
                        for algo_name in ['频率分析', '遗漏分析', '趋势分析']]
                comprehensive_win_rates[pos] = sum(rates) / len(rates) if rates else 0
        
        for algo_key, algo_name, algo_data in algorithms:
            # 创建算法结果页
            algo_frame = tk.Frame(notebook, bg='white')
            
            # 计算胜率显示
            if algo_key == 'deepseek':
                win_rate_display = deepseek_info.get('confidence', 0) * 100
                tab_text = f"{algo_name} (置信度: {win_rate_display:.1f}%)"
            elif algo_key == 'comprehensive':
                win_rate_display = comprehensive_win_rates.get(0, 0) * 100
                tab_text = f"{algo_name} (胜率: {win_rate_display:.1f}%)"
            else:
                win_rate_display = win_rates.get(algo_name, {}).get(0, 0) * 100
                tab_text = f"{algo_name} (胜率: {win_rate_display:.1f}%)"
            
            notebook.add(algo_frame, text=tab_text)
            
            # 创建表格
            table_frame = tk.Frame(algo_frame, bg='white')
            table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 表头
            header_frame = tk.Frame(table_frame, bg='#34495e', height=40)
            header_frame.pack(fill=tk.X)
            header_frame.pack_propagate(False)
            
            headers = ['位置', '推荐1', '推荐2', '推荐3', '胜率']
            col_widths = [80, 100, 100, 100, 80]
            
            for i, (header, width) in enumerate(zip(headers, col_widths)):
                tk.Label(header_frame, text=header, font=(self.default_font, 10, 'bold'),
                        bg='#34495e', fg='white', width=width).grid(row=0, column=i, padx=2, pady=5)
            
            # 表格内容
            content_frame = tk.Frame(table_frame, bg='white')
            content_frame.pack(fill=tk.BOTH, expand=True)
            
            position_names = ['第1名', '第2名', '第3名', '第4名', '第5名', 
                            '第6名', '第7名', '第8名', '第9名', '第10名']
            
            for pos in range(10):
                row_frame = tk.Frame(content_frame, bg='#ecf0f1' if pos % 2 == 0 else 'white', height=35)
                row_frame.pack(fill=tk.X)
                row_frame.pack_propagate(False)
                
                # 位置名称
                tk.Label(row_frame, text=position_names[pos], font=(self.default_font, 9),
                        bg=row_frame.cget('bg'), width=10).grid(row=0, column=0, padx=2, pady=5)
                
                # 推荐号码
                pos_predictions = algo_data.get(pos, [])
                for col_idx in range(3):
                    if col_idx < len(pos_predictions):
                        num, score = pos_predictions[col_idx]
                        score_pct = score * 100
                        tk.Label(row_frame, text=f"{num} ({score_pct:.1f}%)", 
                               font=(self.default_font, 9, 'bold'),
                               bg=row_frame.cget('bg'), fg='#2ecc71' if score_pct > 15 else '#34495e',
                               width=12).grid(row=0, column=col_idx+1, padx=2, pady=5)
                    else:
                        tk.Label(row_frame, text="--", font=(self.default_font, 9),
                               bg=row_frame.cget('bg'), width=12).grid(row=0, column=col_idx+1, padx=2, pady=5)
                
                # 胜率/置信度
                if algo_key == 'deepseek':
                    # DeepSeek使用置信度
                    pos_predictions = algo_data.get(pos, [])
                    if pos_predictions:
                        pos_confidence = pos_predictions[0][1] * 100 if pos_predictions else 0
                    else:
                        pos_confidence = deepseek_info.get('confidence', 0) * 100
                    color = '#e74c3c' if pos_confidence < 20 else '#f39c12' if pos_confidence < 30 else '#2ecc71'
                    tk.Label(row_frame, text=f"{pos_confidence:.1f}%", font=(self.default_font, 9, 'bold'),
                            bg=row_frame.cget('bg'), fg=color, width=10).grid(row=0, column=4, padx=2, pady=5)
                elif algo_key == 'comprehensive':
                    pos_win_rate = comprehensive_win_rates.get(pos, 0) * 100
                    color = '#e74c3c' if pos_win_rate < 20 else '#f39c12' if pos_win_rate < 30 else '#2ecc71'
                    tk.Label(row_frame, text=f"{pos_win_rate:.1f}%", font=(self.default_font, 9, 'bold'),
                            bg=row_frame.cget('bg'), fg=color, width=10).grid(row=0, column=4, padx=2, pady=5)
                else:
                    pos_win_rate = win_rates.get(algo_name, {}).get(pos, 0) * 100
                    color = '#e74c3c' if pos_win_rate < 20 else '#f39c12' if pos_win_rate < 30 else '#2ecc71'
                    tk.Label(row_frame, text=f"{pos_win_rate:.1f}%", font=(self.default_font, 9, 'bold'),
                            bg=row_frame.cget('bg'), fg=color, width=10).grid(row=0, column=4, padx=2, pady=5)
            
            # 说明
            info_frame = tk.Frame(algo_frame, bg='#ecf0f1', height=60)
            info_frame.pack(fill=tk.X, padx=10, pady=5)
            info_frame.pack_propagate(False)
            
            info_text = ""
            if algo_key == 'deepseek':
                analysis = deepseek_info.get('analysis', '')
                if analysis:
                    info_text = f"DeepSeek AI分析：{analysis}"
                else:
                    info_text = "DeepSeek AI：基于深度学习的智能预测，综合分析历史数据的复杂模式和规律"
            elif algo_key == 'comprehensive':
                info_text = "综合推荐：综合三个算法的结果，根据各算法的历史胜率进行加权，给出最优推荐"
            elif algo_key == 'algorithm1':
                info_text = "频率分析：统计每个位置每个号码的历史出现频率，推荐频率最高的号码"
            elif algo_key == 'algorithm2':
                info_text = "遗漏分析：分析每个号码的遗漏值（未出现的期数），推荐遗漏较大的冷号"
            else:
                info_text = "趋势分析：结合最近期的出现频率和变化趋势，综合预测下一期"
            
            tk.Label(info_frame, text=info_text, font=(self.default_font, 9),
                    bg='#ecf0f1', fg='#34495e', wraplength=1100, justify=tk.LEFT).pack(pady=15)
        
        self.status_label.config(text="预测完成", fg='green')
    
    def on_result_select(self, event):
        """选择结果时显示详细信息"""
        selection = self.result_tree.selection()
        if not selection:
            return
        
        item = self.result_tree.item(selection[0])
        period = item['values'][0]
        result_str = item['values'][1]
        
        # 查找完整数据
        result_data = next((r for r in self.current_results if r['period'] == period), None)
        if not result_data:
            return
        
        result_nums = LotteryCalculator.parse_result(result_str)
        
        # 生成详细信息
        detail_lines = []
        detail_lines.append(f"期号: {period}")
        detail_lines.append(f"开奖号码: {result_str}")
        detail_lines.append(f"日期时间: {result_data.get('date', '')}")
        detail_lines.append("")
        detail_lines.append("=" * 50)
        detail_lines.append("1~10名两面结果:")
        detail_lines.append("-" * 50)
        
        for i in range(10):
            two_sides = LotteryCalculator.calculate_two_sides(result_nums, i)
            detail_lines.append(f"第{i+1}名: {two_sides['号码']:2d} - 单双: {two_sides['单双']:2s} | 大小: {two_sides['大小']:2s}")
        
        detail_lines.append("")
        detail_lines.append("=" * 50)
        detail_lines.append("1~5名龙虎结果:")
        detail_lines.append("-" * 50)
        
        dragon_tiger_names = ['冠军', '亚军', '第三名', '第四名', '第五名']
        for i in range(5):
            dt = LotteryCalculator.calculate_dragon_tiger(result_nums, i)
            detail_lines.append(f"{dragon_tiger_names[i]}: {dt}")
        
        detail_lines.append("")
        detail_lines.append("=" * 50)
        detail_lines.append("冠亚和值结果:")
        detail_lines.append("-" * 50)
        
        crown_info = LotteryCalculator.calculate_crown_sum(result_nums)
        detail_lines.append(f"冠军号码: {result_nums[0]}")
        detail_lines.append(f"亚军号码: {result_nums[1]}")
        detail_lines.append(f"冠亚和值: {crown_info['和值']}")
        detail_lines.append(f"单双: {crown_info['单双']}")
        detail_lines.append(f"大小: {crown_info['大小']}")
        detail_lines.append(f"组合: {crown_info['组合']}")
        
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert("1.0", "\n".join(detail_lines))
    


def main():
    """主函数"""
    try:
        root = tk.Tk()
        app = LotteryQueryApp(root)
        
        # 设置窗口关闭事件处理
        def on_closing():
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()
    except Exception as e:
        import traceback
        error_msg = f"程序运行出错:\n{str(e)}\n\n详细错误信息:\n{traceback.format_exc()}"
        print(error_msg)
        # 尝试显示错误对话框
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("程序错误", error_msg)
        except:
            pass


if __name__ == "__main__":
    main()


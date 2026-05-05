
"""
数据匹配模块 - 负责任务与武器数据的匹配
"""
import json
import os
import logging
from typing import Dict, List, Optional, Tuple
from fuzzywuzzy import fuzz, process
from config import TASK_WEAPON_FILE, MONSTER_WEAKNESS_FILE, DEBUG

# 配置日志
logging.basicConfig(level=logging.INFO if DEBUG else logging.WARNING)
logger = logging.getLogger(__name__)


class DataMatcher:
    """数据匹配器 - 负责任务与武器数据的匹配"""

    def __init__(self):
        self.task_data = {}
        self.monster_data = {}
        self._load_data()

    def _load_data(self):
        """加载JSON数据"""
        try:
            # 加载任务武器数据
            if os.path.exists(TASK_WEAPON_FILE):
                with open(TASK_WEAPON_FILE, 'r', encoding='utf-8') as f:
                    self.task_data = json.load(f)
                logger.info(f"成功加载任务数据，共 {len(self.task_data)} 条记录")
            else:
                logger.warning(f"任务数据文件不存在: {TASK_WEAPON_FILE}")

            # 加载怪物弱点数据
            if os.path.exists(MONSTER_WEAKNESS_FILE):
                with open(MONSTER_WEAKNESS_FILE, 'r', encoding='utf-8') as f:
                    self.monster_data = json.load(f)
                logger.info(f"成功加载怪物数据，共 {len(self.monster_data)} 条记录")
            else:
                logger.warning(f"怪物数据文件不存在: {MONSTER_WEAKNESS_FILE}")
        except Exception as e:
            logger.error(f"加载数据文件失败: {str(e)}")

    def match_task(self, task_name: str) -> Optional[Dict]:
        """
        匹配任务名称
        使用模糊匹配算法提高匹配准确率

        Args:
            task_name: 任务名称

        Returns:
            匹配的任务数据，如果未找到则返回None
        """
        if not task_name or not self.task_data:
            return None

        # 首先尝试精确匹配
        if task_name in self.task_data:
            return self.task_data[task_name]

        # 使用模糊匹配
        task_names = list(self.task_data.keys())
        # 使用fuzzywuzzy进行模糊匹配，获取最相似的结果
        result = process.extractOne(task_name, task_names, scorer=fuzz.ratio)

        if result and result[1] >= 70:  # 相似度阈值设为70%
            matched_name = result[0]
            logger.info(f"模糊匹配: '{task_name}' -> '{matched_name}' (相似度: {result[1]}%)")
            return self.task_data[matched_name]

        return None

    def match_monster(self, monster_name: str) -> Optional[Dict]:
        """
        匹配怪物名称

        Args:
            monster_name: 怪物名称

        Returns:
            匹配的怪物数据，如果未找到则返回None
        """
        if not monster_name or not self.monster_data:
            return None

        # 首先尝试精确匹配
        if monster_name in self.monster_data:
            return self.monster_data[monster_name]

        # 使用模糊匹配
        monster_names = list(self.monster_data.keys())
        result = process.extractOne(monster_name, monster_names, scorer=fuzz.ratio)

        if result and result[1] >= 70:  # 相似度阈值设为70%
            matched_name = result[0]
            logger.info(f"模糊匹配: '{monster_name}' -> '{matched_name}' (相似度: {result[1]}%)")
            return self.monster_data[matched_name]

        return None

    def get_recommendation(self, task_name: str) -> Tuple[str, List[Dict]]:
        """
        获取武器推荐

        Args:
            task_name: 任务名称

        Returns:
            (怪物名称, 推荐武器列表)
        """
        # 首先尝试从任务数据中获取
        task_data = self.match_task(task_name)
        if task_data:
            targets = task_data.get("targets", [])
            weapons = task_data.get("weapons", [])

            if targets and weapons:
                return targets[0], weapons
            elif targets:
                # 如果任务数据中没有武器推荐，尝试从怪物数据中获取
                monster_name = targets[0]
                monster_data = self.match_monster(monster_name)
                if monster_data:
                    recommended_weapon = monster_data.get("recommended_weapon", {})
                    if recommended_weapon:
                        return monster_name, [recommended_weapon]

        return "", []

    def get_all_task_names(self) -> List[str]:
        """获取所有任务名称"""
        return list(self.task_data.keys())

    def get_all_monster_names(self) -> List[str]:
        """获取所有怪物名称"""
        return list(self.monster_data.keys())

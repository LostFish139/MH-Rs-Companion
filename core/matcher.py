
"""
数据匹配模块 - 负责任务与武器数据的匹配
支持多怪物任务、全武器推荐、狩猎技巧查询
"""
import json
import os
import logging
from typing import Dict, List, Optional, Tuple
from fuzzywuzzy import fuzz, process
from config import (
    TASK_WEAPON_FILE, MONSTER_WEAKNESS_FILE, HUNTING_TIPS_FILE,
    MONSTER_HUNT_INFO_FILE, WEAPON_CONFIG, TIPS_CONFIG, DEBUG
)

# 配置日志
logging.basicConfig(level=logging.INFO if DEBUG else logging.WARNING)
logger = logging.getLogger(__name__)

# 变体字符归一化映射（将各种变体字统一到标准形式）
# 用于匹配时处理"冰呪龙"与"冰咒龙"等同名异字问题
# 规则：将日文异体字统一为标准中文字
VARIANT_CHARS = {
    "呪": "咒",  # 冰呪龙 -> 冰咒龙（日文呪 -> 中文咒）
}


def _normalize_name(name: str) -> str:
    """将怪物名中的变体字符归一化为标准形式

    将所有变体字替换为标准字，便于匹配时比较。
    例如："冰呪龙" -> "冰咒龙"
    """
    result = name
    for char, replacement in VARIANT_CHARS.items():
        result = result.replace(char, replacement)
    return result


class DataMatcher:
    """数据匹配器 - 负责任务与武器数据的匹配，支持多怪物和狩猎技巧"""

    def __init__(self):
        self.task_data = {}
        self.monster_data = {}
        self.tips_data = {}
        self.hunt_info_data = {}  # 怪物狩猎信息（倒地机制、白给招、讨伐建议等）
        self.current_weapon = WEAPON_CONFIG.get("current_weapon", "盾斧")
        # 归一化名称映射表（变体字归一化名称 -> 原始名称）
        self._monster_name_norm_map = {}   # monster_data 的归一化映射
        self._hunt_info_name_norm_map = {}  # hunt_info_data 的归一化映射
        self._tips_name_norm_map = {}       # tips_data 中怪物专属技巧的归一化映射
        self._load_data()

    def _load_data(self):
        """加载JSON数据"""
        try:
            # 加载任务武器数据
            if os.path.exists(TASK_WEAPON_FILE):
                with open(TASK_WEAPON_FILE, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                # 过滤掉_meta元数据
                self.task_data = {k: v for k, v in raw_data.items() if not k.startswith('_')}
                logger.info(f"成功加载任务数据，共 {len(self.task_data)} 条记录")
            else:
                logger.warning(f"任务数据文件不存在: {TASK_WEAPON_FILE}")

            # 加载怪物弱点数据
            if os.path.exists(MONSTER_WEAKNESS_FILE):
                with open(MONSTER_WEAKNESS_FILE, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                # 过滤掉_meta元数据
                self.monster_data = {k: v for k, v in raw_data.items() if not k.startswith('_')}
                logger.info(f"成功加载怪物数据，共 {len(self.monster_data)} 条记录")
            else:
                logger.warning(f"怪物数据文件不存在: {MONSTER_WEAKNESS_FILE}")

            # 加载狩猎技巧数据
            if os.path.exists(HUNTING_TIPS_FILE):
                with open(HUNTING_TIPS_FILE, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                # 过滤掉_meta元数据
                self.tips_data = {k: v for k, v in raw_data.items() if not k.startswith('_')}
                logger.info(f"成功加载狩猎技巧数据")
            else:
                logger.warning(f"狩猎技巧数据文件不存在: {HUNTING_TIPS_FILE}")

            # 加载怪物狩猎信息（倒地机制、白给招、讨伐建议）
            if os.path.exists(MONSTER_HUNT_INFO_FILE):
                with open(MONSTER_HUNT_INFO_FILE, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                # 从monsterList数组转为字典（怪物名: 信息
                monster_list = raw_data.get("monsterList", [])
                self.hunt_info_data = {}
                for m in monster_list:
                    name = m.get("monsterName", "")
                    if name:
                        self.hunt_info_data[name] = m
                logger.info(f"成功加载怪物狩猎信息，共 {len(self.hunt_info_data)} 只怪物")
            else:
                logger.warning(f"怪物狩猎信息文件不存在: {MONSTER_HUNT_INFO_FILE}")

            # 构建归一化名称映射表（用于变体字匹配）
            self._build_normalized_name_maps()
        except Exception as e:
            logger.error(f"加载数据文件失败: {str(e)}")

    def _build_normalized_name_maps(self):
        """构建归一化名称映射表，用于变体字匹配

        将数据库中所有怪物名的变体字形式映射到原始名称，
        这样匹配时只需将输入归一化后查表即可。
        """
        # monster_data 的归一化映射
        for name in self.monster_data.keys():
            norm = _normalize_name(name)
            if norm != name and norm not in self._monster_name_norm_map:
                self._monster_name_norm_map[norm] = name

        # hunt_info_data 的归一化映射
        for name in self.hunt_info_data.keys():
            norm = _normalize_name(name)
            if norm != name and norm not in self._hunt_info_name_norm_map:
                self._hunt_info_name_norm_map[norm] = name

        # tips_data 中怪物专属技巧的归一化映射
        monster_tips = self.tips_data.get("怪物专属技巧", {})
        for name in monster_tips.keys():
            norm = _normalize_name(name)
            if norm != name and norm not in self._tips_name_norm_map:
                self._tips_name_norm_map[norm] = name

    def set_current_weapon(self, weapon_name: str):
        """设置当前使用的武器"""
        if weapon_name in WEAPON_CONFIG.get("all_weapons", []):
            self.current_weapon = weapon_name
            logger.info(f"当前武器已设置为: {weapon_name}")
        else:
            logger.warning(f"未知武器类型: {weapon_name}")

    def get_current_weapon(self) -> str:
        """获取当前使用的武器"""
        return self.current_weapon

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

        # 尝试变体字归一化匹配
        norm_name = _normalize_name(monster_name)
        # 先看归一化后的名字是否直接在数据库中（数据库可能用的是标准字）
        if norm_name in self.monster_data:
            logger.info(f"变体字匹配: '{monster_name}' -> '{norm_name}'")
            return self.monster_data[norm_name]
        # 通过归一化映射表查找原始名称（数据库可能用的是异体字）
        if norm_name in self._monster_name_norm_map:
            orig_name = self._monster_name_norm_map[norm_name]
            logger.info(f"变体字匹配: '{monster_name}' -> '{orig_name}'")
            return self.monster_data[orig_name]

        # 使用模糊匹配
        monster_names = list(self.monster_data.keys())
        result = process.extractOne(monster_name, monster_names, scorer=fuzz.ratio)

        if result and result[1] >= 70:  # 相似度阈值设为70%
            matched_name = result[0]
            logger.info(f"模糊匹配: '{monster_name}' -> '{matched_name}' (相似度: {result[1]}%)")
            return self.monster_data[matched_name]

        return None

    def get_all_target_monsters(self, task_name: str) -> List[str]:
        """
        获取任务的所有目标怪物名称（支持多怪物任务）
        
        匹配优先级：
        1. 任务名称精确/模糊匹配 task_weapon.json 中的任务
        2. 从任务名称中直接提取怪物名（匹配怪物数据库）

        Args:
            task_name: 任务名称

        Returns:
            目标怪物名称列表
        """
        # 方式1：任务名称匹配
        task_data = self.match_task(task_name)
        if task_data:
            targets = task_data.get("targets", [])
            # 过滤掉"探索"、"采集"等非怪物目标
            monster_targets = [t for t in targets if t not in ["探索", "采集", "其他"]]
            if monster_targets:
                return monster_targets

        # 方式2：从任务名称中直接提取怪物名
        extracted = self._extract_monsters_from_task_name(task_name)
        if extracted:
            logger.info(f"任务名提取怪物: '{task_name}' -> {extracted}")
            return extracted

        return []

    def _extract_monsters_from_task_name(self, task_name: str) -> List[str]:
        """
        从任务名称中提取怪物名称
        
        通过遍历怪物数据库，找出任务名中包含的怪物名
        处理"怪异探究：冰牙龙"、"霸主·青熊兽"等格式
        
        匹配规则：
        - 如果找到带前缀的（如霸主·X），优先返回更具体的那个
        - 不会同时返回"霸主·X"和"X"，只返回最匹配的一个

        Args:
            task_name: 任务名称

        Returns:
            提取到的怪物名称列表
        """
        monster_names = list(self.monster_data.keys())
        if not monster_names:
            return []

        # 按怪物名称长度排序，优先匹配更长的名字
        monster_names_sorted = sorted(monster_names, key=len, reverse=True)

        found_monsters = []
        task_name_clean = task_name

        # 移除常见任务前缀
        task_prefixes = ["怪异探究：", "怪异探究:", "探究任务：", "高级任务：",
                         "狩猎任务：", "自由任务：", "集会所：", "村任务："]
        for prefix in task_prefixes:
            if task_name_clean.startswith(prefix):
                task_name_clean = task_name_clean[len(prefix):]
                break

        # 在任务名中查找怪物名
        matched_base_names = set()  # 已匹配的基础名称（避免重复，如霸主·X和X只保留一个）
        
        for monster_name in monster_names_sorted:
            # 提取怪物的基础名称（去掉前缀）
            base_name = monster_name
            for prefix in ["霸主·", "怪异克服", "原初形态", "溟渊龙"]:
                if base_name.startswith(prefix):
                    base_name = base_name[len(prefix):]
                    break

            # 如果这个基础名称已经匹配过，跳过（避免同时返回霸主·X和X）
            if base_name in matched_base_names:
                continue

            # 检查怪物全名是否在任务名中（支持变体字匹配）
            name_matched = False
            if len(monster_name) >= 2 and monster_name in task_name_clean:
                name_matched = True
            else:
                # 尝试变体字匹配：把任务名中的变体字归一化后再比
                norm_task = _normalize_name(task_name_clean)
                norm_monster = _normalize_name(monster_name)
                if len(norm_monster) >= 2 and norm_monster in norm_task:
                    name_matched = True

            if name_matched:
                # 检查这个怪物名是否已经被更长的名字包含了
                already_covered = False
                for matched in found_monsters:
                    if monster_name in matched and matched != monster_name:
                        already_covered = True
                        break
                if already_covered:
                    matched_base_names.add(base_name)
                    continue
                    
                found_monsters.append(monster_name)
                matched_base_names.add(base_name)
                continue

            # 检查基础名称是否在任务名中
            # 但需要确保基础名不是另一个已匹配怪物名的一部分
            base_matched = False
            if len(base_name) >= 2 and base_name in task_name_clean:
                base_matched = True
            else:
                # 尝试变体字匹配
                norm_task = _normalize_name(task_name_clean)
                norm_base = _normalize_name(base_name)
                if len(norm_base) >= 2 and norm_base in norm_task:
                    base_matched = True

            if base_matched:
                # 检查是否已经有更长的名字包含了这个基础名
                already_covered = False
                for matched in found_monsters:
                    # 检查已匹配的怪物名是否包含当前基础名
                    # （如"激昂金狮子"包含"金狮子"）
                    if base_name in matched and matched != monster_name:
                        already_covered = True
                        break
                if already_covered:
                    matched_base_names.add(base_name)
                    continue
                    
                found_monsters.append(monster_name)
                matched_base_names.add(base_name)

        # 如果找到了多个，按在任务名中出现的顺序排列
        if len(found_monsters) > 1:
            def get_pos(m):
                pos = task_name_clean.find(m)
                if pos < 0:
                    # 尝试变体字匹配位置
                    norm_task = _normalize_name(task_name_clean)
                    norm_m = _normalize_name(m)
                    pos = norm_task.find(norm_m)
                if pos < 0:
                    # 尝试找基础名的位置
                    base = m
                    for prefix in ["霸主·", "怪异克服", "原初形态"]:
                        if base.startswith(prefix):
                            base = base[len(prefix):]
                            break
                    pos = task_name_clean.find(base)
                    if pos < 0:
                        # 基础名也尝试变体字
                        norm_base = _normalize_name(base)
                        norm_task = _normalize_name(task_name_clean)
                        pos = norm_task.find(norm_base)
                return pos if pos >= 0 else 999
            found_monsters.sort(key=get_pos)

        return found_monsters

    def get_recommendation(self, task_name: str) -> Tuple[str, List[Dict]]:
        """
        获取武器推荐（兼容旧接口，返回第一个怪物的推荐）

        Args:
            task_name: 任务名称

        Returns:
            (怪物名称, 推荐武器列表)
        """
        monsters = self.get_all_target_monsters(task_name)
        if not monsters:
            return "", []

        # 返回第一个怪物的推荐（兼容旧版本）
        first_monster = monsters[0]
        weapons = self.get_weapons_for_monster(first_monster)
        return first_monster, weapons

    def get_full_recommendation(self, task_name: str) -> Dict:
        """
        获取完整的推荐信息，支持多怪物任务

        Args:
            task_name: 任务名称

        Returns:
            完整推荐信息字典，包含所有怪物的推荐和狩猎技巧
        """
        monsters = self.get_all_target_monsters(task_name)
        if not monsters:
            return {}

        result = {
            "task_name": task_name,
            "monsters": [],
            "is_multi_monster": len(monsters) > 1
        }

        for monster_name in monsters:
            monster_info = self._get_monster_full_info(monster_name)
            result["monsters"].append(monster_info)

        return result

    def _get_monster_full_info(self, monster_name: str) -> Dict:
        """
        获取怪物的完整信息，包括弱点、武器推荐和狩猎技巧

        Args:
            monster_name: 怪物名称

        Returns:
            怪物完整信息字典
        """
        monster_data = self.match_monster(monster_name)
        if not monster_data:
            return {"name": monster_name, "found": False}

        info = {
            "name": monster_name,
            "found": True,
            "type": monster_data.get("type", "未知"),
            "weakness": monster_data.get("weakness", {}),
            "weakest_element": monster_data.get("weakest_element", "未知"),
            "weakest_parts": monster_data.get("weakest_parts", []),
            "status_weakness": monster_data.get("status_weakness", {}),
            "weapons": self._format_weapon_list(monster_data.get("recommended_weapons", {})),
            "tips": self.get_hunting_tips(monster_name),
            "hunt_info": self.get_monster_hunt_info(monster_name)
        }

        return info

    def get_monster_hunt_info(self, monster_name: str) -> Dict:
        """
        获取怪物狩猎信息（讨伐建议、白给招、倒地机制、特殊机制）

        Args:
            monster_name: 怪物名称

        Returns:
            狩猎信息字典
        """
        result = {
            "found": False,
            "grade": "",
            "hunt_suggestion": "",      # 讨伐建议
            "free_moves": "",            # 白给招式
            "stun_mechanism": "",        # 倒地机制
            "special_mechanism": ""      # 特殊机制
        }

        if not self.hunt_info_data:
            return result

        # 精确匹配
        if monster_name in self.hunt_info_data:
            info = self.hunt_info_data[monster_name]
            result["found"] = True
            result["grade"] = info.get("grade", "")
            result["hunt_suggestion"] = info.get("huntSuggestion", "")
            result["free_moves"] = info.get("mainFreeMove", "")
            result["stun_mechanism"] = info.get("stunMechanism", "")
            result["special_mechanism"] = info.get("specialMechanism", "")
            return result

        # 尝试变体字归一化匹配
        norm_name = _normalize_name(monster_name)
        matched_hunt_name = None
        if norm_name in self.hunt_info_data:
            matched_hunt_name = norm_name
        elif norm_name in self._hunt_info_name_norm_map:
            matched_hunt_name = self._hunt_info_name_norm_map[norm_name]
        if matched_hunt_name:
                info = self.hunt_info_data[matched_hunt_name]
                result["found"] = True
                result["grade"] = info.get("grade", "")
                result["hunt_suggestion"] = info.get("huntSuggestion", "")
                result["free_moves"] = info.get("mainFreeMove", "")
                result["stun_mechanism"] = info.get("stunMechanism", "")
                result["special_mechanism"] = info.get("specialMechanism", "")
                logger.info(f"狩猎信息变体字匹配: '{monster_name}' -> '{matched_hunt_name}'")
                return result

        # 模糊匹配
        hunt_info_names = list(self.hunt_info_data.keys())
        result_match = process.extractOne(monster_name, hunt_info_names, scorer=fuzz.ratio)
        if result_match and result_match[1] >= 70:
            matched_name = result_match[0]
            info = self.hunt_info_data[matched_name]
            result["found"] = True
            result["grade"] = info.get("grade", "")
            result["hunt_suggestion"] = info.get("huntSuggestion", "")
            result["free_moves"] = info.get("mainFreeMove", "")
            result["stun_mechanism"] = info.get("stunMechanism", "")
            result["special_mechanism"] = info.get("specialMechanism", "")
            logger.info(f"狩猎信息模糊匹配: '{monster_name}' -> '{matched_name}' (相似度: {result_match[1]}%)")
            return result

        return result

    def _format_weapon_list(self, weapons_dict: Dict) -> List[Dict]:
        """
        将武器推荐字典格式化为列表

        Args:
            weapons_dict: 武器推荐字典 {武器类型: {weapon, element}}

        Returns:
            格式化的武器列表
        """
        weapon_list = []
        for weapon_type, weapon_info in weapons_dict.items():
            weapon_list.append({
                "weapon_type": weapon_type,
                "weapon": weapon_info.get("weapon", "未知武器"),
                "element": weapon_info.get("element", "未知属性")
            })
        return weapon_list

    def get_weapons_for_monster(self, monster_name: str) -> List[Dict]:
        """
        获取指定怪物的推荐武器列表

        Args:
            monster_name: 怪物名称

        Returns:
            推荐武器列表
        """
        monster_data = self.match_monster(monster_name)
        if monster_data:
            recommended = monster_data.get("recommended_weapons", {})
            return self._format_weapon_list(recommended)
        return []

    def get_weapon_for_monster(self, monster_name: str, weapon_type: str = None) -> Optional[Dict]:
        """
        获取指定怪物的指定武器类型推荐

        Args:
            monster_name: 怪物名称
            weapon_type: 武器类型，默认为当前武器

        Returns:
            武器推荐信息
        """
        if weapon_type is None:
            weapon_type = self.current_weapon

        monster_data = self.match_monster(monster_name)
        if monster_data:
            recommended = monster_data.get("recommended_weapons", {})
            if weapon_type in recommended:
                info = recommended[weapon_type]
                return {
                    "weapon_type": weapon_type,
                    "weapon": info.get("weapon", "未知武器"),
                    "element": info.get("element", "未知属性")
                }
        return None

    def get_hunting_tips(self, monster_name: str) -> Dict:
        """
        获取狩猎技巧（通用技巧 + 武器专属技巧 + 怪物专属技巧）

        Args:
            monster_name: 怪物名称

        Returns:
            狩猎技巧字典
        """
        tips = {
            "general": [],
            "weapon_specific": [],
            "monster_specific": []
        }

        if not self.tips_data:
            return tips

        max_tips = TIPS_CONFIG.get("max_tips_per_category", 3)

        # 通用技巧
        if TIPS_CONFIG.get("show_general_tips", True):
            general_tips = self.tips_data.get("通用技巧", {})
            base_tips = general_tips.get("基础", [])[:max_tips]
            tips["general"].extend(base_tips)

        # 武器通用技巧
        if TIPS_CONFIG.get("show_weapon_tips", True):
            weapon_tips = self.tips_data.get("武器通用技巧", {})
            current_weapon_tips = weapon_tips.get(self.current_weapon, {})
            core_tips = current_weapon_tips.get("核心思路", [])[:max_tips]
            tips["weapon_specific"].extend(core_tips)

        # 怪物专属技巧
        if TIPS_CONFIG.get("show_monster_tips", True):
            monster_tips = self.tips_data.get("怪物专属技巧", {})
            matched_monster_tips = self._find_monster_tips(monster_name, monster_tips)
            if matched_monster_tips:
                # 怪物通用技巧
                monster_general = matched_monster_tips.get("通用", [])[:max_tips]
                tips["monster_specific"].extend(monster_general)
                # 武器专属技巧
                weapon_specific = matched_monster_tips.get(self.current_weapon, [])[:max_tips]
                tips["weapon_specific"].extend(weapon_specific)

        return tips

    def _find_monster_tips(self, monster_name: str, monster_tips_dict: Dict) -> Optional[Dict]:
        """
        模糊匹配怪物技巧

        Args:
            monster_name: 怪物名称
            monster_tips_dict: 怪物技巧字典

        Returns:
            匹配的怪物技巧
        """
        if monster_name in monster_tips_dict:
            return monster_tips_dict[monster_name]

        # 尝试变体字归一化匹配
        norm_name = _normalize_name(monster_name)
        if norm_name in monster_tips_dict:
            logger.info(f"狩猎技巧变体字匹配: '{monster_name}' -> '{norm_name}'")
            return monster_tips_dict[norm_name]
        if norm_name in self._tips_name_norm_map:
            orig_name = self._tips_name_norm_map[norm_name]
            logger.info(f"狩猎技巧变体字匹配: '{monster_name}' -> '{orig_name}'")
            return monster_tips_dict[orig_name]

        # 模糊匹配
        monster_names = list(monster_tips_dict.keys())
        result = process.extractOne(monster_name, monster_names, scorer=fuzz.ratio)

        if result and result[1] >= 70:
            matched_name = result[0]
            logger.info(f"狩猎技巧模糊匹配: '{monster_name}' -> '{matched_name}' (相似度: {result[1]}%)")
            return monster_tips_dict[matched_name]

        return None

    def get_all_task_names(self) -> List[str]:
        """获取所有任务名称"""
        return list(self.task_data.keys())

    def get_all_monster_names(self) -> List[str]:
        """获取所有怪物名称"""
        return list(self.monster_data.keys())

    def get_all_weapon_types(self) -> List[str]:
        """获取所有武器类型"""
        return WEAPON_CONFIG.get("all_weapons", [])

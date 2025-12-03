"""盲盒抽奖系统初始化数据脚本"""
import json
from pathlib import Path
from sqlmodel import Session, select
from app.core.db import engine
from app.models import PrizeTemplate, BlindBoxPrizeType


def load_json_data(filename: str):
    """加载JSON数据文件"""
    data_dir = Path(__file__).parent / "data"
    file_path = data_dir / filename
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def insert_prize_templates_data():
    """插入奖品模板数据"""
    print("开始插入奖品模板数据...")
    
    with Session(engine) as session:
        # 检查是否已有数据
        existing_prizes = session.exec(select(PrizeTemplate)).all()
        if existing_prizes:
            print(f"奖品模板数据已存在 ({len(existing_prizes)} 条)，跳过插入")
            return
        
        # 加载数据
        prizes_data = load_json_data("prize_templates_data.json")
        
        for prize_dict in prizes_data:
            # 转换枚举类型
            prize_dict['prize_type'] = BlindBoxPrizeType(prize_dict['prize_type'])
            
            prize = PrizeTemplate(**prize_dict)
            session.add(prize)
        
        session.commit()
        print(f"成功插入 {len(prizes_data)} 条奖品模板数据")


def init_blindbox_data():
    """初始化所有盲盒抽奖数据"""
    print("=" * 50)
    print("开始初始化盲盒抽奖系统数据")
    print("=" * 50)
    
    try:
        insert_prize_templates_data()
        
        print("=" * 50)
        print("盲盒抽奖系统数据初始化完成！")
        print("=" * 50)
    except Exception as e:
        print(f"初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    init_blindbox_data()


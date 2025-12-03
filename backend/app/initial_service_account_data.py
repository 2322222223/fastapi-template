"""
初始化服务号测试数据
"""
import json
import os
from sqlmodel import Session, select
from app.core.db import engine
from app.models import ServiceAccount, ServiceAccountCreate, ServiceAccountType


def load_service_account_data():
    """加载服务号测试数据"""
    data_file = os.path.join(os.path.dirname(__file__), "data", "service_account_test_data.json")
    
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return data.get("service_accounts", [])


def insert_service_accounts(session: Session, service_accounts_data: list[dict]):
    """插入服务号数据"""
    print(f"开始插入 {len(service_accounts_data)} 个服务号...")
    
    inserted_count = 0
    skipped_count = 0
    
    for account_data in service_accounts_data:
        # 检查是否已存在相同名称的服务号
        existing_account = session.exec(
            select(ServiceAccount).where(ServiceAccount.name == account_data["name"])
        ).first()
        
        if existing_account:
            print(f"服务号 '{account_data['name']}' 已存在，跳过")
            skipped_count += 1
            continue
        
        # 创建服务号
        try:
            service_account = ServiceAccountCreate(**account_data)
            db_account = ServiceAccount(**service_account.dict())
            session.add(db_account)
            inserted_count += 1
            print(f"添加服务号: {account_data['name']}")
        except Exception as e:
            print(f"创建服务号 '{account_data['name']}' 失败: {e}")
            continue
    
    session.commit()
    print(f"服务号数据插入完成: 新增 {inserted_count} 个，跳过 {skipped_count} 个")


def main():
    """主函数"""
    print("开始初始化服务号测试数据...")
    
    try:
        # 加载数据
        service_accounts_data = load_service_account_data()
        if not service_accounts_data:
            print("没有找到服务号测试数据")
            return
        
        # 连接数据库并插入数据
        with Session(engine) as session:
            insert_service_accounts(session, service_accounts_data)
        
        print("服务号测试数据初始化完成!")
        
    except Exception as e:
        print(f"初始化服务号数据时出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

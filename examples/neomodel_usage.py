"""
Neomodel ORM 使用示例
演示如何使用Neomodel与Neo4j数据库交互
"""

import asyncio
from datetime import datetime, date
from typing import List

# 导入配置和初始化
from app.core.neomodel_config import setup_neomodel, transaction
from app.core.config import settings

# 导入Pydantic模型
from app.models.graph.nodes.person import PersonNode
from app.models.graph.nodes.organization import OrganizationNode
from app.models.graph.nodes.location import LocationNode

# 导入Neomodel模型
from app.models.neomodel.nodes import Person, Organization, Location

# 导入仓储
from app.repositories.neomodel_repository import (
    PersonRepository,
    OrganizationRepository,
    LocationRepository
)

# 导入转换器
from app.models.converters.graph_converter import GraphModelConverter


def example_1_basic_crud():
    """
    示例1: 基本CRUD操作
    """
    print("\n=== 示例1: 基本CRUD操作 ===\n")
    
    # 初始化仓储
    person_repo = PersonRepository()
    
    # 1. 创建节点
    print("1. 创建人员节点")
    person = person_repo.create(
        uid="person_001",
        name="张三",
        email="zhangsan@example.com",
        age=30,
        gender="male",
        occupation="软件工程师",
        skills=["Python", "Neo4j", "FastAPI"]
    )
    print(f"   创建成功: {person.name} (UID: {person.uid})")
    
    # 2. 查询节点
    print("\n2. 查询节点")
    found_person = person_repo.find_by_uid("person_001")
    if found_person:
        print(f"   找到: {found_person.name}, 邮箱: {found_person.email}")
    
    # 3. 更新节点
    print("\n3. 更新节点")
    updated_person = person_repo.update(
        "person_001",
        occupation="高级软件工程师",
        skills=["Python", "Neo4j", "FastAPI", "Docker"]
    )
    if updated_person:
        print(f"   更新成功: 职位={updated_person.occupation}, 技能={updated_person.skills}")
    
    # 4. 搜索节点
    print("\n4. 搜索节点")
    search_results = person_repo.search("工程师", ["occupation", "bio"])
    print(f"   搜索结果: 找到 {len(search_results)} 个匹配的人员")
    
    # 5. 删除节点
    print("\n5. 删除节点")
    deleted = person_repo.delete("person_001")
    print(f"   删除{'成功' if deleted else '失败'}")


def example_2_pydantic_integration():
    """
    示例2: Pydantic模型集成
    """
    print("\n=== 示例2: Pydantic模型集成 ===\n")
    
    # 1. 创建Pydantic模型
    print("1. 创建Pydantic模型")
    pydantic_person = PersonNode(
        uid="person_002",
        name="李四",
        email="lisi@example.com",
        phone="+86-13800138000",
        age=28,
        gender="female",
        occupation="产品经理",
        interests=["设计", "用户体验", "数据分析"]
    )
    print(f"   Pydantic模型: {pydantic_person.name}")
    
    # 2. 转换为Neomodel并保存
    print("\n2. 转换为Neomodel并保存")
    neomodel_person = pydantic_person.to_neomodel()
    if neomodel_person:
        neomodel_person.save()
        print(f"   保存成功: {neomodel_person.name} (UID: {neomodel_person.uid})")
    
    # 3. 从数据库读取并转回Pydantic
    print("\n3. 从数据库读取并转回Pydantic")
    person_repo = PersonRepository()
    db_person = person_repo.find_by_uid("person_002")
    if db_person:
        pydantic_again = PersonNode.from_neomodel(db_person)
        print(f"   转换回Pydantic: {pydantic_again.name}, 邮箱: {pydantic_again.email}")
    
    # 清理
    person_repo.delete("person_002")


def example_3_relationships():
    """
    示例3: 关系管理
    """
    print("\n=== 示例3: 关系管理 ===\n")
    
    person_repo = PersonRepository()
    org_repo = OrganizationRepository()
    
    # 1. 创建节点
    print("1. 创建节点")
    
    # 创建人员
    person1 = person_repo.create(
        uid="person_003",
        name="王五",
        email="wangwu@example.com",
        occupation="CTO"
    )
    
    person2 = person_repo.create(
        uid="person_004",
        name="赵六",
        email="zhaoliu@example.com",
        occupation="开发工程师"
    )
    
    # 创建组织
    org = org_repo.create(
        uid="org_001",
        name="科技有限公司",
        org_type="company",
        industry="互联网",
        website="https://example.com"
    )
    
    print(f"   创建人员: {person1.name}, {person2.name}")
    print(f"   创建组织: {org.name}")
    
    # 2. 建立关系
    print("\n2. 建立关系")
    
    # 人员工作于组织
    if person1 and org:
        person1.works_at.connect(
            org,
            {
                'position': 'CTO',
                'department': '技术部',
                'start_date': datetime.now(),
                'is_current': True
            }
        )
        print(f"   {person1.name} 工作于 {org.name}")
    
    if person2 and org:
        person2.works_at.connect(
            org,
            {
                'position': '高级工程师',
                'department': '技术部',
                'start_date': datetime.now(),
                'is_current': True
            }
        )
        print(f"   {person2.name} 工作于 {org.name}")
    
    # 人员之间的关系
    if person1 and person2:
        person1.knows.connect(person2, {'context': '同事', 'since': datetime.now()})
        print(f"   {person1.name} 认识 {person2.name}")
    
    # 3. 查询关系
    print("\n3. 查询关系")
    
    # 获取组织的员工
    org_with_employees = org_repo.get_with_employees("org_001")
    if org_with_employees:
        print(f"   {org_with_employees['organization']['name']} 有 {org_with_employees['employee_count']} 名员工")
        for emp in org_with_employees['employees']:
            print(f"     - {emp['name']} ({emp['occupation']})")
    
    # 获取人员的关系
    person1_relationships = person_repo.get_relationships("person_003")
    print(f"\n   {person1.name} 的关系:")
    for rel in person1_relationships:
        print(f"     - {rel['type']}: {rel['node']['name']}")
    
    # 清理
    person_repo.delete("person_003")
    person_repo.delete("person_004")
    org_repo.delete("org_001")


def example_4_batch_operations():
    """
    示例4: 批量操作
    """
    print("\n=== 示例4: 批量操作 ===\n")
    
    person_repo = PersonRepository()
    
    # 1. 批量创建
    print("1. 批量创建人员")
    
    persons_data = [
        {
            "uid": f"batch_person_{i}",
            "name": f"测试用户{i}",
            "email": f"user{i}@example.com",
            "age": 20 + i,
            "skills": ["Python", "JavaScript"] if i % 2 == 0 else ["Java", "Go"]
        }
        for i in range(1, 6)
    ]
    
    created_persons = person_repo.bulk_create(persons_data)
    print(f"   批量创建 {len(created_persons)} 个人员")
    
    # 2. 分页查询
    print("\n2. 分页查询")
    page_result = person_repo.paginate(page=1, per_page=3)
    print(f"   第1页 (共{page_result['pages']}页，总计{page_result['total']}条):")
    for person in page_result['items']:
        print(f"     - {person.name} ({person.email})")
    
    # 3. 按技能查找
    print("\n3. 按技能查找")
    python_users = person_repo.find_by_skills(["Python"])
    print(f"   掌握Python的用户: {len(python_users)}个")
    for user in python_users:
        print(f"     - {user.name}: {user.skills}")
    
    # 4. 批量删除
    print("\n4. 批量删除")
    deleted_count = person_repo.delete_all(uid__startswith="batch_person_")
    print(f"   批量删除 {deleted_count} 个人员")


def example_5_transactions():
    """
    示例5: 事务处理
    """
    print("\n=== 示例5: 事务处理 ===\n")
    
    person_repo = PersonRepository()
    org_repo = OrganizationRepository()
    
    print("1. 使用事务创建关联数据")
    
    try:
        with transaction():
            # 在事务中创建多个相关节点
            company = org_repo.create(
                uid="trans_org_001",
                name="事务测试公司",
                org_type="company"
            )
            
            employee1 = person_repo.create(
                uid="trans_person_001",
                name="事务员工1",
                email="trans1@example.com"
            )
            
            employee2 = person_repo.create(
                uid="trans_person_002",
                name="事务员工2",
                email="trans2@example.com"
            )
            
            # 建立关系
            if company and employee1 and employee2:
                employee1.works_at.connect(company, {'position': '经理'})
                employee2.works_at.connect(company, {'position': '员工'})
                employee1.knows.connect(employee2, {'context': '同事'})
            
            print("   事务提交成功")
    
    except Exception as e:
        print(f"   事务回滚: {str(e)}")
    
    # 验证数据
    print("\n2. 验证事务结果")
    trans_org = org_repo.find_by_uid("trans_org_001")
    if trans_org:
        print(f"   找到组织: {trans_org.name}")
        employees = list(trans_org.employees.all())
        print(f"   员工数量: {len(employees)}")
    
    # 清理
    person_repo.delete("trans_person_001")
    person_repo.delete("trans_person_002")
    org_repo.delete("trans_org_001")


def example_6_location_features():
    """
    示例6: 地理位置功能
    """
    print("\n=== 示例6: 地理位置功能 ===\n")
    
    location_repo = LocationRepository()
    
    # 1. 创建地点
    print("1. 创建地点")
    
    locations_data = [
        {
            "uid": "loc_beijing",
            "name": "北京",
            "location_type": "city",
            "latitude": 39.9042,
            "longitude": 116.4074,
            "population": 21540000
        },
        {
            "uid": "loc_shanghai",
            "name": "上海",
            "location_type": "city",
            "latitude": 31.2304,
            "longitude": 121.4737,
            "population": 24280000
        },
        {
            "uid": "loc_tianjin",
            "name": "天津",
            "location_type": "city",
            "latitude": 39.1255,
            "longitude": 117.1901,
            "population": 13866000
        }
    ]
    
    for loc_data in locations_data:
        loc = location_repo.create(**loc_data)
        print(f"   创建地点: {loc.name} ({loc.latitude}, {loc.longitude})")
    
    # 2. 查找附近的地点
    print("\n2. 查找北京附近的城市 (300km内)")
    
    # 注意: find_nearby需要Neo4j空间索引支持
    # nearby_cities = location_repo.find_nearby(39.9042, 116.4074, radius_km=300)
    # print(f"   找到 {len(nearby_cities)} 个附近的城市")
    
    # 3. 建立地点层级关系
    print("\n3. 建立地点层级关系")
    
    china = location_repo.create(
        uid="loc_china",
        name="中国",
        location_type="country",
        population=1411000000
    )
    
    beijing = location_repo.find_by_uid("loc_beijing")
    if china and beijing:
        china.contains.connect(beijing)
        print(f"   {china.name} 包含 {beijing.name}")
    
    # 清理
    for uid in ["loc_beijing", "loc_shanghai", "loc_tianjin", "loc_china"]:
        location_repo.delete(uid)


def main():
    """
    主函数：运行所有示例
    """
    print("=" * 60)
    print("Neomodel ORM 使用示例")
    print("=" * 60)
    
    # 初始化Neomodel连接
    print("\n初始化Neomodel连接...")
    setup_neomodel()
    print("连接成功！")
    
    # 运行示例
    try:
        # 基本CRUD操作
        example_1_basic_crud()
        
        # Pydantic模型集成
        example_2_pydantic_integration()
        
        # 关系管理
        example_3_relationships()
        
        # 批量操作
        example_4_batch_operations()
        
        # 事务处理
        example_5_transactions()
        
        # 地理位置功能
        example_6_location_features()
        
    except Exception as e:
        print(f"\n错误: {str(e)}")
    
    print("\n" + "=" * 60)
    print("示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    # 确保Neo4j数据库已启动
    print("请确保Neo4j数据库已启动 (docker-compose up -d neo4j)")
    print("Neo4j浏览器: http://localhost:7474")
    print("默认凭据: neo4j/password123")
    print()
    
    # 运行示例
    main()
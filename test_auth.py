"""
登录功能测试脚本
用于测试用户注册、登录、密码验证等功能
"""

from services.auth_service import auth_service


def test_auth():
    """测试认证功能"""
    print("=" * 50)
    print("🔐 用户认证功能测试")
    print("=" * 50)
    
    # 1. 测试注册
    print("\n📝 测试 1：用户注册")
    print("-" * 50)
    
    result = auth_service.register_user(
        username="test_teacher",
        password="123456",
        email="test@example.com",
        role="teacher"
    )
    print(f"注册结果：{result}")
    
    if result['success']:
        print(f"✅ 用户 ID: {result['user_id']}")
    else:
        print(f"⚠️ {result['message']}")
    
    # 2. 测试重复注册
    print("\n📝 测试 2：重复注册")
    print("-" * 50)
    
    result = auth_service.register_user(
        username="test_teacher",
        password="123456",
        email="test2@example.com",
        role="teacher"
    )
    print(f"重复注册结果：{result}")
    
    # 3. 测试登录
    print("\n📝 测试 3：用户登录")
    print("-" * 50)
    
    result = auth_service.login_user("test_teacher", "123456")
    print(f"登录结果：{result}")
    
    if result['success']:
        print(f"✅ 登录成功，用户信息：{result['user']}")
    else:
        print(f"❌ {result['message']}")
    
    # 4. 测试错误密码
    print("\n📝 测试 4：错误密码登录")
    print("-" * 50)
    
    result = auth_service.login_user("test_teacher", "wrong_password")
    print(f"错误密码登录结果：{result}")
    
    # 5. 测试不存在的用户
    print("\n📝 测试 5：不存在的用户")
    print("-" * 50)
    
    result = auth_service.login_user("nonexistent_user", "123456")
    print(f"不存在的用户登录结果：{result}")
    
    # 6. 测试获取用户信息
    print("\n📝 测试 6：获取用户信息")
    print("-" * 50)
    
    if result.get('user'):
        user_id = result['user']['id']
    else:
        # 使用已知的用户ID
        user_id = 1
    
    user = auth_service.get_user_by_id(user_id)
    print(f"用户信息：{user}")
    
    # 7. 测试修改密码
    print("\n📝 测试 7：修改密码")
    print("-" * 50)
    
    result = auth_service.update_password(user_id, "123456", "new_password")
    print(f"修改密码结果：{result}")
    
    if result['success']:
        # 测试新密码登录
        result = auth_service.login_user("test_teacher", "new_password")
        print(f"新密码登录结果：{result}")
        
        # 恢复旧密码
        auth_service.update_password(user_id, "new_password", "123456")
        print("✅ 密码已恢复为 123456")
    
    # 8. 测试获取所有用户
    print("\n📝 测试 8：获取所有用户")
    print("-" * 50)
    
    users = auth_service.get_all_users()
    print(f"用户总数：{len(users)}")
    for user in users:
        print(f"  - ID: {user['id']}, 用户名: {user['username']}, 角色: {user['role']}")
    
    # 9. 密码加密测试
    print("\n📝 测试 9：密码加密机制")
    print("-" * 50)
    
    password1 = auth_service.hash_password("test123")
    password2 = auth_service.hash_password("test123")
    
    print(f"密码 1: {password1[:30]}...")
    print(f"密码 2: {password2[:30]}...")
    print(f"两次加密结果相同：{password1 == password2}")
    print(f"（应该不同，因为使用了随机 salt）")
    
    # 验证密码
    is_valid = auth_service.verify_password("test123", password1)
    print(f"密码验证结果：{is_valid}")
    
    print("\n" + "=" * 50)
    print("✅ 测试完成！")
    print("=" * 50)


if __name__ == "__main__":
    test_auth()

"""
数据库升级脚本 - 为用户表添加密码字段
用于在现有数据库上添加登录功能
"""

import mysql.connector
from data.config import get_db_config


def upgrade_database():
    """升级数据库，添加用户认证相关字段"""
    
    # 获取配置
    DB_CONFIG = get_db_config()
    
    # 连接 MySQL
    conn = mysql.connector.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        charset='utf8mb4'
    )
    
    cursor = conn.cursor()
    
    try:
        print(" 开始升级数据库...")
        
        # 1. 检查 password 字段是否存在
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'password'
        """, (DB_CONFIG['database'],))
        
        password_exists = cursor.fetchone()
        
        if not password_exists:
            print(" ️ 添加 password 字段...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN password VARCHAR(255) NOT NULL DEFAULT '' 
                COMMENT '加密后的密码（salt$hash）'
                AFTER username
            """)
            print("✅ password 字段添加成功！")
        else:
            print("⚠️ password 字段已存在，跳过")
        
        # 2. 添加 username 索引
        cursor.execute("""
            SELECT INDEX_NAME 
            FROM INFORMATION_SCHEMA.STATISTICS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'users' 
            AND INDEX_NAME = 'idx_username'
        """, (DB_CONFIG['database'],))
        
        index_exists = cursor.fetchone()
        
        if not index_exists:
            print(" ️ 添加 username 索引...")
            cursor.execute("""
                ALTER TABLE users 
                ADD INDEX idx_username (username)
            """)
            print("✅ username 索引添加成功！")
        else:
            print("⚠️ username 索引已存在，跳过")
        
        # 3. 修改 role 字段，添加 admin 选项
        cursor.execute("""
            SELECT COLUMN_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'role'
        """, (DB_CONFIG['database'],))
        
        role_type = cursor.fetchone()
        if role_type and 'admin' not in role_type[0]:
            print(" ️ 更新 role 字段类型...")
            cursor.execute("""
                ALTER TABLE users 
                MODIFY COLUMN role ENUM('teacher', 'student', 'admin') DEFAULT 'teacher'
            """)
            print("✅ role 字段更新成功！")
        else:
            print("⚠️ role 字段已包含 admin，跳过")
        
        conn.commit()
        print("\n🎉 数据库升级完成！")
        print("\n 提示：")
        print("   - 现有用户的密码字段为空，需要重置密码")
        print("   - 可以使用以下 SQL 为现有用户设置密码：")
        print("     UPDATE users SET password = 'your_hashed_password' WHERE username = 'xxx';")
        
    except Exception as e:
        print(f"❌ 升级失败：{str(e)}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    upgrade_database()

import psycopg2
import pandas as pd


def explore_database_structure() -> str:
    """探索天文数据库的表结构和数据分布
    
    返回所有相关表的详细结构信息，包括：
    - 表名和列信息
    - 数据类型和空值情况  
    - 值分布统计
    - 样本数据预览
    
    这有助于了解数据库内容，为后续查询提供参考。
    """
    connection_string = "postgresql://wxuser:wxpass@localhost:5432/wxdb"
    
    try:
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        tables = [
            'gcn_notice_xdb', 'gcn_circular_xdb', 'gcn_event_xdb',
            'atelmetadata_xdb', 'atelextraction_xdb', 'tns_xdb'
        ]
        
        output = "🔍 天文数据库结构探索报告\n"
        output += "=" * 60 + "\n\n"
        
        for table in tables:
            output += f"📊 表: {table}\n"
            output += "-" * 40 + "\n"
            
            try:
                # 获取表结构
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """)
                
                columns = cursor.fetchall()
                if not columns:
                    output += "  (表不存在或无法访问)\n\n"
                    continue
                
                # 表结构信息
                output += "📋 表结构:\n"
                for col_name, data_type, nullable in columns:
                    null_info = '可空' if nullable == 'YES' else '非空'
                    output += f"  • {col_name:25} {data_type:20} {null_info}\n"
                
                # 表统计信息
                cursor.execute(f"SELECT COUNT(*) as total FROM {table}")
                total_records = cursor.fetchone()[0]
                output += f"\n📈 表统计: 总记录数 {total_records}\n"
                
                # 关键列的值分布
                output += "\n🎯 关键列值分布:\n"
                for col_name, data_type, _ in columns:
                    if col_name in ['mission', 'notice_type', 'event_type', 'circular_type', 'type']:
                        explore_column_distribution(conn, table, col_name, output)
                    elif col_name in ['content', 'title', 'subject']:
                        explore_text_column_summary(conn, table, col_name, output)
                
                # 样本数据预览
                output += "\n👀 样本数据预览:\n"
                show_sample_preview(conn, table, 2, output)
                
                output += "\n" + "="*60 + "\n\n"
                
            except Exception as e:
                output += f"  ❌ 查询失败: {e}\n\n"
        
        cursor.close()
        conn.close()
        
        # 添加使用建议
        output += "💡 使用建议:\n"
        output += "• 使用 search_astronomy_alerts 搜索具体事件\n"
        output += "• 关注 mission, notice_type, event_type 等关键字段\n"
        output += "• 使用 get_database_stats 获取整体统计\n"
        
        return output
        
    except Exception as e:
        return f"❌ 数据库连接失败: {str(e)}"

def explore_column_distribution(conn, table, column, output):
    """探索分类列的分布"""
    try:
        query = f"""
        SELECT {column}, COUNT(*) as count
        FROM {table}
        WHERE {column} IS NOT NULL AND {column} != ''
        GROUP BY {column}
        ORDER BY count DESC
        LIMIT 10
        """
        df = pd.read_sql(query, conn)
        
        if len(df) > 0:
            output += f"  {column}:\n"
            for _, row in df.iterrows():
                value = str(row[column]) if len(str(row[column])) < 30 else str(row[column])[:30] + "..."
                percentage = (row['count'] / df['count'].sum()) * 100
                output += f"    • {value:25} {row['count']:4} 条 ({percentage:.1f}%)\n"
    except:
        pass

def explore_text_column_summary(conn, table, column, output):
    """探索文本列的统计摘要"""
    try:
        query = f"""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT {column}) as unique_count,
            AVG(LENGTH({column})) as avg_length,
            SUM(CASE WHEN {column} IS NULL OR {column} = '' THEN 1 ELSE 0 END) as empty_count
        FROM {table}
        """
        df = pd.read_sql(query, conn)
        
        total = df.iloc[0]['total']
        unique = df.iloc[0]['unique_count']
        avg_len = df.iloc[0]['avg_length']
        empty = df.iloc[0]['empty_count']
        
        output += f"  {column}:\n"
        output += f"    • 总记录: {total}, 唯一值: {unique}, 空值: {empty}\n"
        output += f"    • 平均长度: {avg_len:.1f} 字符\n"
    except:
        pass

def show_sample_preview(conn, table, limit, output):
    """显示样本数据预览"""
    try:
        query = f"SELECT * FROM {table} LIMIT {limit}"
        df = pd.read_sql(query, conn)
        
        for i, row in df.iterrows():
            output += f"  第 {i+1} 行:\n"
            # 只显示关键字段
            key_fields = ['id', 'mission', 'notice_type', 'event_type', 'title', 'grb_date']
            for col in key_fields:
                if col in df.columns and pd.notna(row[col]):
                    value = str(row[col])
                    if len(value) > 50:
                        value = value[:50] + "..."
                    output += f"    • {col}: {value}\n"
            output += "\n"
    except:
        output += "    (无法获取样本数据)\n"


def get_table_info(table_name: str) -> str:
    """获取特定表的详细信息
    
    Args:
        table_name: 表名，如 'gcn_notice_xdb', 'gcn_circular_xdb' 等
        
    Returns:
        表的详细结构信息和样本数据
    """
    connection_string = "postgresql://wxuser:wxpass@localhost:5432/wxdb"
    
    try:
        conn = psycopg2.connect(connection_string)
        
        output = f"📊 表 {table_name} 详细信息\n"
        output += "=" * 50 + "\n\n"
        
        # 检查表是否存在
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = '{table_name}'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            return f"❌ 表 '{table_name}' 不存在"
        
        # 表结构
        cursor.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        output += "📋 表结构:\n"
        for col_name, data_type, nullable in columns:
            null_info = '可空' if nullable == 'YES' else '非空'
            output += f"  • {col_name:25} {data_type:20} {null_info}\n"
        
        # 记录数
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total = cursor.fetchone()[0]
        output += f"\n📈 总记录数: {total}\n"
        
        # 关键字段示例
        output += "\n🎯 关键字段示例:\n"
        for col_name, data_type, _ in columns:
            if col_name in ['mission', 'notice_type', 'event_type', 'circular_type']:
                cursor.execute(f"""
                    SELECT DISTINCT {col_name}
                    FROM {table_name}
                    WHERE {col_name} IS NOT NULL
                    LIMIT 5
                """)
                values = [row[0] for row in cursor.fetchall()]
                if values:
                    output += f"  • {col_name}: {', '.join(map(str, values))}\n"
        
        cursor.close()
        conn.close()
        
        return output
        
    except Exception as e:
        return f"❌ 查询失败: {str(e)}"
    
def get_database_schema() -> str:
    """获取数据库表结构和字段说明"""
    return """
📊 天文数据库结构：

gcn_notice_xdb (GCN通知表):
  • id: 主键
  • mission: 任务 (SWIFT, FERMI, INTEGRAL等)
  • notice_type: 事件类型 (GRB, SGR, TRANSIENT等) 
  • trigger_num: 触发编号
  • grb_ra, grb_dec: 坐标
  • grb_date, notice_datetime: 时间
  • content: 内容详情

gcn_circular_xdb (GCN通告表):
  • id, event_name, title, circular_type
  • ra, dec, err: 坐标和误差
  • send_datetime: 发送时间
  • content: 详细内容

atelmetadata_xdb (ATel表):
  • atel_id, title, author, subject
  • datetime: 发布时间
  • content: 内容

tns_xdb (TNS表):
  • objid, event_name, type
  • ra, dec, redshift
  • discoverydate: 发现时间
  • reporters: 报告者
"""


"""
填充缺失的银行账户数据
运行方式: python fill_bank_accounts.py
"""
import sys
sys.path.insert(0, '.')

from models import get_session, BankAccount
from logic.constants import BankInfoKey
from sqlalchemy import Integer

# 虚拟银行账户数据（符合中国对公账户规范）
BANK_ACCOUNTS = [
    # 客户 - 711-华东 (customer_id=5)
    {
        "owner_type": "customer",
        "owner_id": 5,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "上海统一方便店有限公司",
            BankInfoKey.BANK_NAME: "招商银行上海浦东陆家嘴支行",
            BankInfoKey.ACCOUNT_NO: "6214850210000001",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": "customer",
        "owner_id": 5,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "上海统一方便店有限公司",
            BankInfoKey.BANK_NAME: "中国工商银行上海张江高科技园区支行",
            BankInfoKey.ACCOUNT_NO: "1001234567890123",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 客户 - 海南TODAY (customer_id=6)
    {
        "owner_type": "customer",
        "owner_id": 6,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "海南today便利店有限公司",
            BankInfoKey.BANK_NAME: "中国银行海口龙华支行",
            BankInfoKey.ACCOUNT_NO: "2650010000000000012",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": "customer",
        "owner_id": 6,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "海南today便利店有限公司",
            BankInfoKey.BANK_NAME: "中国建设银行海南分行营业部",
            BankInfoKey.ACCOUNT_NO: "43001503908059000012",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 客户 - 零食有鸣 (customer_id=7)
    {
        "owner_type": "customer",
        "owner_id": 7,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "四川零食有鸣品牌管理有限公司",
            BankInfoKey.BANK_NAME: "中国农业银行成都武侯支行",
            BankInfoKey.ACCOUNT_NO: "22800101040000019",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": "customer",
        "owner_id": 7,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "四川零食有鸣品牌管理有限公司",
            BankInfoKey.BANK_NAME: "交通银行成都锦江支行",
            BankInfoKey.ACCOUNT_NO: "3110010000000000156",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 客户 - 雄安便利店 (customer_id=8)
    {
        "owner_type": "customer",
        "owner_id": 8,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "雄安新区便民便利店有限公司",
            BankInfoKey.BANK_NAME: "中国工商银行河北雄安分行",
            BankInfoKey.ACCOUNT_NO: "1008990000000000145",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": "customer",
        "owner_id": 8,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "雄安新区便民便利店有限公司",
            BankInfoKey.BANK_NAME: "中国建设银行雄安新区支行",
            BankInfoKey.ACCOUNT_NO: "1305010000000000123",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 客户 - 西安每一天 (customer_id=9)
    {
        "owner_type": "customer",
        "owner_id": 9,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "西安每一天便利店有限公司",
            BankInfoKey.BANK_NAME: "招商银行西安高新区支行",
            BankInfoKey.ACCOUNT_NO: "6228090000000000118",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": "customer",
        "owner_id": 9,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "西安每一天便利店有限公司",
            BankInfoKey.BANK_NAME: "中国银行西安南郊支行",
            BankInfoKey.ACCOUNT_NO: "2920010000000000134",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 客户 - 福建邻几 (customer_id=10)
    {
        "owner_type": "customer",
        "owner_id": 10,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "福建邻几便利店有限公司",
            BankInfoKey.BANK_NAME: "中国工商银行福州鼓楼支行",
            BankInfoKey.ACCOUNT_NO: "1408010000000000127",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": "customer",
        "owner_id": 10,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "福建邻几便利店有限公司",
            BankInfoKey.BANK_NAME: "中国建设银行福州台江支行",
            BankInfoKey.ACCOUNT_NO: "3505010000000000136",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 客户 - 福美多 (customer_id=11)
    {
        "owner_type": "customer",
        "owner_id": 11,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "福美多便利店连锁有限公司",
            BankInfoKey.BANK_NAME: "中国农业银行福州分行",
            BankInfoKey.ACCOUNT_NO: "1358010104000000138",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": "customer",
        "owner_id": 11,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "福美多便利店连锁有限公司",
            BankInfoKey.BANK_NAME: "交通银行福州分行营业部",
            BankInfoKey.ACCOUNT_NO: "3010010000000000149",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 客户 - 十分 (customer_id=12)
    {
        "owner_type": "customer",
        "owner_id": 12,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "十分便利店股份有限公司",
            BankInfoKey.BANK_NAME: "中国银行深圳福田支行",
            BankInfoKey.ACCOUNT_NO: "7755010000000000151",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": "customer",
        "owner_id": 12,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "十分便利店股份有限公司",
            BankInfoKey.BANK_NAME: "招商银行深圳南山支行",
            BankInfoKey.ACCOUNT_NO: "6229090000000000162",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 客户 - 中百罗森 (customer_id=13)
    {
        "owner_type": "customer",
        "owner_id": 13,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "武汉中百罗森便利店有限公司",
            BankInfoKey.BANK_NAME: "中国工商银行武汉江汉支行",
            BankInfoKey.ACCOUNT_NO: "3202010000000000173",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": "customer",
        "owner_id": 13,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "武汉中百罗森便利店有限公司",
            BankInfoKey.BANK_NAME: "中国建设银行武汉中南支行",
            BankInfoKey.ACCOUNT_NO: "4205010000000000184",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 客户 - 天福 (customer_id=14)
    {
        "owner_type": "customer",
        "owner_id": 14,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "广东天福便利店连锁有限公司",
            BankInfoKey.BANK_NAME: "中国银行东莞分行",
            BankInfoKey.ACCOUNT_NO: "5755010000000000195",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": "customer",
        "owner_id": 14,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "广东天福便利店连锁有限公司",
            BankInfoKey.BANK_NAME: "中国农业银行东莞城区支行",
            BankInfoKey.ACCOUNT_NO: "4490010104000000167",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 客户 - 壹度便利店 (customer_id=15)
    {
        "owner_type": "customer",
        "owner_id": 15,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "壹度便利店有限公司",
            BankInfoKey.BANK_NAME: "招商银行合肥包河支行",
            BankInfoKey.ACCOUNT_NO: "6228090000000000178",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": "customer",
        "owner_id": 15,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "壹度便利店有限公司",
            BankInfoKey.BANK_NAME: "中国银行合肥庐阳支行",
            BankInfoKey.ACCOUNT_NO: "1850010000000000189",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 客户 - 十足 (customer_id=16)
    {
        "owner_type": "customer",
        "owner_id": 16,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "十足集团有限公司",
            BankInfoKey.BANK_NAME: "中国工商银行杭州西湖支行",
            BankInfoKey.ACCOUNT_NO: "1202010000000000191",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": "customer",
        "owner_id": 16,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "十足集团有限公司",
            BankInfoKey.BANK_NAME: "中国建设银行杭州滨江支行",
            BankInfoKey.ACCOUNT_NO: "3305010000000000153",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 客户 - 全家 (customer_id=17)
    {
        "owner_type": "customer",
        "owner_id": 17,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "全家便利店有限公司",
            BankInfoKey.BANK_NAME: "中国银行上海静安支行",
            BankInfoKey.ACCOUNT_NO: "3100010000000000164",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": "customer",
        "owner_id": 17,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "全家便利店有限公司",
            BankInfoKey.BANK_NAME: "招商银行上海黄浦支行",
            BankInfoKey.ACCOUNT_NO: "6228090000000000175",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 供应商 - 浙江斯贝乐 (supplier_id=11)
    {
        "owner_type": "supplier",
        "owner_id": 11,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "浙江斯贝乐厨房设备有限公司",
            BankInfoKey.BANK_NAME: "中国工商银行杭州余杭支行",
            BankInfoKey.ACCOUNT_NO: "1202010000000000186",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": "supplier",
        "owner_id": 11,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "浙江斯贝乐厨房设备有限公司",
            BankInfoKey.BANK_NAME: "中国建设银行杭州临平支行",
            BankInfoKey.ACCOUNT_NO: "3305010000000000197",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },
]


def main():
    session = get_session()
    try:
        # 检查已存在的账户
        existing = session.query(BankAccount).all()
        existing_keys = set()
        for ba in existing:
            key = (ba.owner_type, ba.owner_id, ba.account_info.get(BankInfoKey.ACCOUNT_NO, '') if ba.account_info else '')
            existing_keys.add(key)

        print(f'Existing accounts: {len(existing)}')

        # 插入新账户
        added_count = 0
        for data in BANK_ACCOUNTS:
            key = (data["owner_type"], data["owner_id"], data["account_info"].get(BankInfoKey.ACCOUNT_NO, ''))
            if key not in existing_keys:
                ba = BankAccount(**data)
                session.add(ba)
                added_count += 1
                print(f'  Added: {data["owner_type"]}/{data["owner_id"]} - {data["account_info"][BankInfoKey.ACCOUNT_NO]}')
            else:
                print(f'  Skipped (exists): {data["owner_type"]}/{data["owner_id"]} - {data["account_info"][BankInfoKey.ACCOUNT_NO]}')

        session.commit()
        print(f'\nNew accounts added: {added_count}')

        # 验证结果
        total = session.query(BankAccount).count()
        print(f'Total accounts: {total}')

        # 按实体类型统计
        from sqlalchemy import func
        stats = session.query(
            BankAccount.owner_type,
            BankAccount.owner_id,
            func.count(BankAccount.id).label('count'),
            func.sum(func.cast(BankAccount.is_default, Integer)).label('has_default')
        ).group_by(BankAccount.owner_type, BankAccount.owner_id).all()

        print('\nEntity account stats:')
        for s in stats:
            print(f'  {s[0]}/{s[1]}: {s[2]} accounts, default={s[3]}')

    finally:
        session.close()


if __name__ == "__main__":
    main()

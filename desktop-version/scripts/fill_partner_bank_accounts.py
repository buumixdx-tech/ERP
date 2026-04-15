"""
填充外部合作方的银行账户数据
运行方式: python fill_partner_bank_accounts.py
"""
import sys
sys.path.insert(0, '.')

from models import get_session, BankAccount
from logic.constants import BankInfoKey, AccountOwnerType
from sqlalchemy import Integer

# 虚拟银行账户数据
BANK_ACCOUNTS = [
    # 耀程科技 (partner_id=1)
    {
        "owner_type": AccountOwnerType.PARTNER,
        "owner_id": 1,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "耀程科技",
            BankInfoKey.BANK_NAME: "招商银行北京万通中心支行",
            BankInfoKey.ACCOUNT_NO: "110945287710668",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": AccountOwnerType.PARTNER,
        "owner_id": 1,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "耀程科技",
            BankInfoKey.BANK_NAME: "中国银行北京长安支行",
            BankInfoKey.ACCOUNT_NO: "6217856000123456789",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 天猫 (partner_id=2)
    {
        "owner_type": AccountOwnerType.PARTNER,
        "owner_id": 2,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "天猫",
            BankInfoKey.BANK_NAME: "中国建设银行杭州西湖支行",
            BankInfoKey.ACCOUNT_NO: "6200589012300567891",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": AccountOwnerType.PARTNER,
        "owner_id": 2,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "天猫",
            BankInfoKey.BANK_NAME: "中国农业银行杭州滨江支行",
            BankInfoKey.ACCOUNT_NO: "6228480012345678901",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 雄安闻众信 (partner_id=3)
    {
        "owner_type": AccountOwnerType.PARTNER,
        "owner_id": 3,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "雄安闻众信",
            BankInfoKey.BANK_NAME: "中国工商银行雄安新区支行",
            BankInfoKey.ACCOUNT_NO: "2102014509200789012",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": AccountOwnerType.PARTNER,
        "owner_id": 3,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "雄安闻众信",
            BankInfoKey.BANK_NAME: "交通银行雄安容城支行",
            BankInfoKey.ACCOUNT_NO: "3015010109200034567",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 和美记 (partner_id=4)
    {
        "owner_type": AccountOwnerType.PARTNER,
        "owner_id": 4,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "和美记",
            BankInfoKey.BANK_NAME: "招商银行上海陆家嘴支行",
            BankInfoKey.ACCOUNT_NO: "110945287710901",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": AccountOwnerType.PARTNER,
        "owner_id": 4,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "和美记",
            BankInfoKey.BANK_NAME: "中国农业银行上海浦东支行",
            BankInfoKey.ACCOUNT_NO: "6228480018901234567",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 琼浆 (partner_id=5)
    {
        "owner_type": AccountOwnerType.PARTNER,
        "owner_id": 5,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "琼浆",
            BankInfoKey.BANK_NAME: "中国建设银行成都春熙路支行",
            BankInfoKey.ACCOUNT_NO: "6200589012300789012",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": AccountOwnerType.PARTNER,
        "owner_id": 5,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "琼浆",
            BankInfoKey.BANK_NAME: "中国工商银行成都盐市口支行",
            BankInfoKey.ACCOUNT_NO: "1608014509200456789",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 廊坊羽旨 (partner_id=6)
    {
        "owner_type": AccountOwnerType.PARTNER,
        "owner_id": 6,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "廊坊羽旨",
            BankInfoKey.BANK_NAME: "中国银行廊坊分行",
            BankInfoKey.ACCOUNT_NO: "6217856000134567890",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": AccountOwnerType.PARTNER,
        "owner_id": 6,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "廊坊羽旨",
            BankInfoKey.BANK_NAME: "招商银行廊坊支行",
            BankInfoKey.ACCOUNT_NO: "110945287710345",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },

    # 百望达 (partner_id=7)
    {
        "owner_type": AccountOwnerType.PARTNER,
        "owner_id": 7,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "百望达",
            BankInfoKey.BANK_NAME: "中国农业银行北京海淀支行",
            BankInfoKey.ACCOUNT_NO: "6228480010678901234",
            BankInfoKey.ACCOUNT_TYPE: "基本户"
        },
        "is_default": True
    },
    {
        "owner_type": AccountOwnerType.PARTNER,
        "owner_id": 7,
        "account_info": {
            BankInfoKey.HOLDER_NAME: "百望达",
            BankInfoKey.BANK_NAME: "中国建设银行北京上地支行",
            BankInfoKey.ACCOUNT_NO: "6200589012300456789",
            BankInfoKey.ACCOUNT_TYPE: "一般户"
        },
        "is_default": False
    },
]


def main():
    session = get_session()
    try:
        existing = session.query(BankAccount).all()
        existing_keys = set()
        for ba in existing:
            key = (ba.owner_type, ba.owner_id, ba.account_info.get(BankInfoKey.ACCOUNT_NO, '') if ba.account_info else '')
            existing_keys.add(key)

        print(f'Existing accounts: {len(existing)}')

        added_count = 0
        for data in BANK_ACCOUNTS:
            key = (data["owner_type"], data["owner_id"], data["account_info"].get(BankInfoKey.ACCOUNT_NO, ''))
            if key not in existing_keys:
                ba = BankAccount(**data)
                session.add(ba)
                added_count += 1
                print(f'  Added: partner/{data["owner_id"]} - {data["account_info"][BankInfoKey.ACCOUNT_NO]}')
            else:
                print(f'  Skipped: partner/{data["owner_id"]} - {data["account_info"][BankInfoKey.ACCOUNT_NO]}')

        session.commit()
        print(f'\nNew accounts added: {added_count}')

        total = session.query(BankAccount).count()
        print(f'Total accounts: {total}')

        # Verify partner accounts
        from sqlalchemy import func
        stats = session.query(
            BankAccount.owner_type,
            BankAccount.owner_id,
            func.count(BankAccount.id).label('count'),
            func.sum(func.cast(BankAccount.is_default, Integer)).label('has_default')
        ).filter(
            BankAccount.owner_type == AccountOwnerType.PARTNER
        ).group_by(BankAccount.owner_type, BankAccount.owner_id).all()

        print('\nPartner account stats:')
        for s in stats:
            print(f'  partner/{s[1]}: {s[2]} accounts, default={s[3]}')

    finally:
        session.close()


if __name__ == "__main__":
    main()

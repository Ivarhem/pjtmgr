"""Accounting contract_type_config service - re-exports from common for backward compatibility."""
from app.modules.common.services.contract_type_config import (  # noqa: F401
    list_contract_types,
    get_valid_codes,
    create_contract_type,
    update_contract_type,
    delete_contract_type,
    seed_defaults,
    to_read,
)

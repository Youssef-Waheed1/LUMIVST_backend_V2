# # app/schemas/__init__.py

# from .profile import CompanyProfileCreate, CompanyProfileResponse
# from .quote import StockQuoteCreate, StockQuoteResponse
# from .stock import StockResponse, StockListResponse
# # from .financials import FinancialsResponse

# __all__ = [
#     "CompanyProfileCreate",
#     "CompanyProfileResponse", 
#     "StockQuoteCreate",
#     "StockQuoteResponse",
#     "StockResponse",
#     "StockListResponse",
#     "FinancialsResponse",
# ]

























# # from .financials import (
# #     IncomeStatement, BalanceSheet, CashFlow,
# #     IncomeStatementResponse, BalanceSheetResponse, CashFlowResponse
# # )



# # # app/schemas/__init__.py
# # from .stock import StockResponse, StockListResponse
# # from .profile import CompanyProfileCreate, CompanyProfileResponse
# # from .quote import StockQuoteCreate, StockQuoteResponse

# # __all__ = [
# #     "StockResponse", 
# #     "StockListResponse",
# #     "CompanyProfileCreate", 
# #     "CompanyProfileResponse",
# #     "StockQuoteCreate", 
# #     "StockQuoteResponse"
# # ]

# # # app/schemas/__init__.py

# # from .profile import CompanyProfileCreate, CompanyProfileResponse
# # from .quote import StockQuoteResponse  # ⭐ أزل StockQuoteCreate إذا لم تعد موجودة
# # from .stock import StockResponse, StockListResponse
# # from .financials import FinancialsResponse

# # # إذا كنت تحتاج StockQuoteCreate، أضفها هنا:
# # # from .quote import StockQuoteCreate, StockQuoteResponse

# # __all__ = [
# #     "CompanyProfileCreate",
# #     "CompanyProfileResponse", 
# #     "StockQuoteResponse",  # ⭐ تأكد أن هذا موجود
# #     "StockResponse",
# #     "StockListResponse",
# #     "FinancialsResponse",
# # ]